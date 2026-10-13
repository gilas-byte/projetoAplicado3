"""Radar ENEM: MVP do fluxo nota -> percentil -> visualizacao.

Le apenas artefatos ANALYTICS: histograma protegido (dist_notas.parquet)
e CDF exata de frequencias agregadas (dist_exata.parquet). Nenhuma linha
individual dos microdados e carregada.

Privacidade das notas digitadas (docs/privacidade.md, R6): ficam so no
estado da sessao do Streamlit, que some quando a aba fecha. O app nao grava
nada, nao usa query string (st.query_params) e nao registra as notas em log.

Uso:
  ./.venv/bin/streamlit run app/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from colunas import PISO_GRUPO  # noqa: E402
from estatistica import histograma, percentil_exato_acumulado  # noqa: E402

DIST_NOTAS = Path(os.environ.get("RADAR_DIST_NOTAS", RAIZ / "data" / "analytics" / "dist_notas.parquet"))
DIST_EXATA = Path(os.environ.get("RADAR_DIST_EXATA", RAIZ / "data" / "analytics" / "dist_exata.parquet"))

AREAS = {
    "cn": "Ciências da Natureza",
    "ch": "Ciências Humanas",
    "lc": "Linguagens e Códigos",
    "mt": "Matemática",
    "redacao": "Redação",
}


@st.cache_data
def carregar() -> dict[tuple[int, str], list[tuple[float, float, int]]]:
    """Faixas por (edicao, area). Carregado uma vez e compartilhado entre sessoes."""
    linhas = duckdb.sql(
        f"SELECT ano, area, nota_min, nota_max, n FROM read_parquet('{DIST_NOTAS}') "
        "ORDER BY ano, area, nota_min"
    ).fetchall()
    faixas: dict[tuple[int, str], list[tuple[float, float, int]]] = {}
    for ano, area, nota_min, nota_max, n in linhas:
        faixas.setdefault((ano, area), []).append((nota_min, nota_max, n))
    return faixas


@st.cache_data
def carregar_exatas() -> dict[tuple[int, str], list[tuple[float, int, int]]]:
    """CDF de notas exatas, exclusivamente em memoria do backend.

    Não expor a tabela ou suas contagens por endpoint público: algumas
    notas específicas possuem menos de PISO_GRUPO participantes.
    """
    linhas = duckdb.sql(
        f"SELECT ano, area, nota, n, abaixo FROM read_parquet('{DIST_EXATA}') "
        "ORDER BY ano, area, nota"
    ).fetchall()
    saida = {}
    for ano, area, nota, n, abaixo in linhas:
        saida.setdefault((ano, area), []).append((float(nota), int(n), int(abaixo)))
    return saida


def grafico(faixas_area, nota: float, titulo: str) -> go.Figure:
    classes = histograma(faixas_area)
    fig = go.Figure(
        go.Bar(
            x=[inicio + 10 for inicio, _ in classes],
            y=[pct for _, pct in classes],
            width=20,
            marker_color=["#2563eb" if inicio <= nota else "#93c5fd" for inicio, _ in classes],
            hovertemplate="%{x:.0f} ± 10 pontos: %{y:.1f}% dos participantes<extra></extra>",
        )
    )
    fig.add_vline(x=nota, line_width=2, line_dash="dash", line_color="#dc2626",
                  annotation_text="sua nota", annotation_position="top")
    fig.update_layout(
        title=titulo, bargap=0.05, height=320, margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Nota", yaxis_title="% dos participantes", showlegend=False,
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="Radar ENEM", layout="centered")
    st.title("Radar ENEM")
    st.write(
        "Informe suas notas e veja em que posição você ficaria entre os "
        "participantes de uma edição do ENEM."
    )

    if not DIST_NOTAS.exists() or not DIST_EXATA.exists():
        st.error("Artefatos estatísticos incompletos. Rode `scripts/etl.py` para gerar faixas e distribuição exata.")
        st.stop()
    faixas = carregar()
    exatas = carregar_exatas()
    anos = sorted({ano for ano, _ in faixas}, reverse=True)

    with st.form("notas"):
        ano = st.selectbox("Edição de comparação", anos)
        colunas = st.columns(2)
        notas = {}
        for i, (area, nome) in enumerate(AREAS.items()):
            notas[area] = colunas[i % 2].number_input(
                nome, min_value=0.0, max_value=1000.0, value=None,
                step=20.0 if area == "redacao" else 0.1, format="%.1f",
                placeholder="não informada",
            )
        enviado = st.form_submit_button("Ver minha posição", type="primary")

    informadas = {a: n for a, n in notas.items() if n is not None}
    if not enviado:
        return
    if not informadas:
        st.warning("Informe ao menos uma nota.")
        return

    st.subheader(f"Sua posição no ENEM {ano}")
    for area, nota in informadas.items():
        faixas_area = faixas.get((ano, area))
        if not faixas_area or not exatas.get((ano, area)):
            st.info(f"{AREAS[area]}: grupo insuficiente para comparação.")
            continue
        p = percentil_exato_acumulado(exatas[(ano, area)], nota)
        total = sum(n for *_, n in faixas_area)
        st.metric(AREAS[area], f"{nota:.1f}", f"acima de {p:.1f}% dos participantes", delta_color="off")
        st.plotly_chart(grafico(faixas_area, nota, f"{AREAS[area]}: distribuição das notas"),
                        config={"displayModeBar": False})
        st.caption(f"Comparação com {total:,} participantes elegíveis de {ano}.".replace(",", "."))

    with st.expander("Como a posição é calculada"):
        st.markdown(
            f"""
- **Quem entra na comparação:** participantes presentes nos dois dias de prova
  (quatro áreas) e que não fizeram o exame como treineiros. Quem faltou, foi
  eliminado ou era treineiro não disputa vaga e distorceria a distribuição.
- **Percentil:** porcentagem dos participantes com nota abaixo da sua; notas
  iguais contam pela metade.
- **Privacidade:** o app não carrega registros individuais. O gráfico utiliza
  faixas de pelo menos {PISO_GRUPO} pessoas, enquanto o cálculo exato usa uma
  distribuição acumulada agregada restrita ao backend. As notas digitadas
  não são persistidas pelo aplicativo.
- **Leitura:** o resultado descreve a posição da nota na edição escolhida; não
  prevê aprovação, que depende do curso, da instituição e das regras de cada
  processo seletivo.
- **Fonte:** Microdados do ENEM, INEP.
"""
        )


main()
