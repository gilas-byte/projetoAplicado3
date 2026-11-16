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
from estatistica import caixa_protegida, histograma, percentil_exato_acumulado  # noqa: E402
from ui import COR_NOTA, COR_PROPRIO, abertura, aplicar_tema, estilo_grafico, paleta  # noqa: E402

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
    # Caminho como parâmetro da consulta, não interpolado no texto da SQL (Business
    # Intelligence, aula de KPIs e performance: a f-string do exemplo é insegura).
    # Aqui o valor vem do servidor, nunca do usuário, mas a regra vale para todo o app.
    linhas = duckdb.execute(
        "SELECT ano, area, nota_min, nota_max, n FROM read_parquet(?) ORDER BY ano, area, nota_min",
        [str(DIST_NOTAS)],
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
    linhas = duckdb.execute(
        "SELECT ano, area, nota, n, abaixo FROM read_parquet(?) ORDER BY ano, area, nota",
        [str(DIST_EXATA)],
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
            marker_color=[COR_PROPRIO if inicio <= nota else paleta()["fraco1"] for inicio, _ in classes],
            marker_line_width=0,
            hovertemplate="%{x:.0f} ± 10 pontos: %{y:.1f}% dos participantes<extra></extra>",
        )
    )
    fig.add_vline(x=nota, line_width=2, line_dash="dash", line_color=COR_NOTA,
                  annotation_text="sua nota", annotation_position="top")
    fig.update_layout(
        title=titulo, bargap=0.05, margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title="Nota", yaxis_title="% dos participantes", showlegend=False,
    )
    return estilo_grafico(fig)


def grafico_caixas(caixas: list[tuple[str, dict, float]]) -> go.Figure:
    """Caixa protegida de cada área informada, com a nota do usuário marcada.

    Bigodes nos percentis 5 e 95 e nenhum ponto discrepante: o mínimo, o máximo e
    os outliers do boxplot clássico seriam notas de pessoas isoladas (privacidade, R3).
    """
    fig = go.Figure()
    nomes = [nome for nome, _, _ in caixas]
    fig.add_trace(go.Box(
        y=nomes, orientation="h", name="Participantes",
        q1=[c["q1"] for _, c, _ in caixas], median=[c["mediana"] for _, c, _ in caixas],
        q3=[c["q3"] for _, c, _ in caixas], lowerfence=[c["bigode_inferior"] for _, c, _ in caixas],
        upperfence=[c["bigode_superior"] for _, c, _ in caixas],
        boxpoints=False, fillcolor=paleta()["fraco1"], line=dict(color=COR_PROPRIO, width=1.5),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=[nota for *_, nota in caixas], y=nomes, mode="markers", name="Sua nota",
        marker=dict(color=COR_NOTA, size=12, symbol="diamond", line=dict(width=1, color="#ffffff")),
        hovertemplate="sua nota: %{x:.1f}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(title="Nota", range=[0, 1000]),
        legend=dict(orientation="h", y=-0.3), boxmode="overlay",
    )
    return estilo_grafico(fig, altura=110 + 55 * len(caixas))


def texto_quartis(caixa: dict) -> str:
    def f(x: float) -> str:
        return f"{x:.1f}".replace(".", ",")
    return (f"Metade dos participantes ficou entre {f(caixa['q1'])} e {f(caixa['q3'])} "
            f"(1º e 3º quartis); a mediana foi {f(caixa['mediana'])}. 90% ficaram entre "
            f"{f(caixa['bigode_inferior'])} e {f(caixa['bigode_superior'])}.")


def main() -> None:
    st.set_page_config(page_title="Radar ENEM", layout="centered")
    aplicar_tema("inicio")
    st.title("Radar ENEM")
    abertura(
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

    with st.container(key="resultado"):
        st.subheader(f"Sua posição no ENEM {ano}")
        caixas = []
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
            caixa = caixa_protegida(exatas[(ano, area)])
            if caixa is not None:
                st.caption(texto_quartis(caixa))
                caixas.append((AREAS[area], caixa, nota))
        if caixas:
            st.markdown("**Sua nota diante dos quartis de cada área**")
            st.plotly_chart(grafico_caixas(caixas), config={"displayModeBar": False})
            st.caption("A caixa vai do 1º ao 3º quartil, a linha interna é a mediana e os bigodes "
                       "vão dos percentis 5 a 95. O mínimo, o máximo e os pontos isolados não são "
                       "desenhados, porque cada um seria a nota de uma única pessoa.")

    with st.expander("Como a posição é calculada"):
        st.markdown(
            f"""
- **Quem entra na comparação:** participantes presentes nos dois dias de prova
  (quatro áreas) e que não fizeram o exame como treineiros. Quem faltou, foi
  eliminado ou era treineiro não disputa vaga e distorceria a distribuição.
- **Percentil:** porcentagem dos participantes com nota abaixo da sua; notas
  iguais contam pela metade.
- **Quartis:** o 1º quartil é a menor nota que deixa ao menos 25% dos
  participantes nela ou abaixo; a mediana e o 3º quartil seguem a mesma regra
  com 50% e 75% (DL-01). Os bigodes do gráfico de caixa usam 5% e 95%.
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
