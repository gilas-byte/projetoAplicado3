"""Radar ENEM: módulo Equidade socioeconômica (autor: Samuel Silva de Rezende).

Página do app Streamlit. Lê apenas data/analytics/dist_equidade.parquet
(CDF agregada por edição, área e grupo de renda), gerado por
scripts/equidade.py. Regras em docs/decisoes (DL-03).

Privacidade (docs/privacidade.md, R6): notas e renda digitadas ficam só no
estado da sessão; nada é gravado, nada vai para a URL e nada vai para log.
O gráfico usa faixas de pelo menos PISO_GRUPO participantes.

Uso:
  ./.venv/bin/streamlit run app/app.py   (página "Equidade socioeconomica")
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

from colunas import PISO_GRUPO  # noqa: E402
from equidade import (  # noqa: E402
    AREAS,
    CONTRASTE,
    CONTRASTE_ROTULO,
    FAIXA_POR_CODIGO,
    EntradaInvalida,
    carregar,
    faixa_de_q006,
    comparar,
    formatar_nota,
    formatar_percentil,
    formatar_z,
    opcoes_q006,
    validar_entrada,
)
from estatistica import faixas, histograma  # noqa: E402

DIST_EQUIDADE = Path(os.environ.get("RADAR_DIST_EQUIDADE", RAIZ / "data" / "analytics" / "dist_equidade.parquet"))
COR_FAIXA, COR_CONTRASTE, COR_NOTA = "#2563eb", "#f59e0b", "#dc2626"


@st.cache_data
def _cdfs():
    return carregar(DIST_EQUIDADE)


@st.cache_data
def _opcoes(ano: int):
    return opcoes_q006(ano)


def _classes(cdf):
    """Histograma protegido do grupo: só faixas com >= PISO_GRUPO pessoas."""
    return histograma(faixas([(nota, n) for nota, n, _ in cdf]))


def grafico(cdfs, ano: int, area: str, faixa: str, nota: float) -> go.Figure:
    fig = go.Figure()
    for grupo, nome, cor in ((faixa, "Sua faixa de renda", COR_FAIXA),
                             (CONTRASTE, "Escola privada, > 10 SM", COR_CONTRASTE)):
        cdf = cdfs.get((ano, area, grupo))
        if not cdf:
            continue
        classes = _classes(cdf)
        fig.add_trace(go.Bar(
            x=[inicio + 10 for inicio, _ in classes], y=[pct for _, pct in classes], width=20,
            name=nome, marker_color=cor, opacity=0.55,
            hovertemplate=nome + ": %{y:.1f}% do grupo entre %{x:.0f} ± 10<extra></extra>",
        ))
    fig.add_vline(x=nota, line_width=2, line_dash="dash", line_color=COR_NOTA,
                  annotation_text="sua nota", annotation_position="top")
    fig.update_layout(barmode="overlay", bargap=0.05, height=320, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis_title="Nota", yaxis_title="% do grupo",
                      legend=dict(orientation="h", y=-0.25))
    return fig


def mostrar(cdfs, resultado) -> None:
    e, real, simulado = resultado.entrada, resultado.real, resultado.simulado
    st.subheader(f"{AREAS[e.area]}: nota {formatar_nota(e.nota)}")
    col1, col2 = st.columns(2)
    for coluna, cenario, titulo in ((col1, real, "1. Entre a sua faixa de renda"),
                                    (col2, simulado, "2. Entre escola privada de alta renda")):
        with coluna:
            if cenario.disponivel:
                st.metric(titulo, formatar_percentil(cenario.percentil),
                          f"acima de {formatar_percentil(cenario.percentil)} do grupo", delta_color="off")
                st.caption(f"{cenario.rotulo} · {cenario.n:,} participantes".replace(",", "."))
            else:
                st.metric(titulo, "—")
                st.info(f"{cenario.rotulo}: {cenario.motivo}.")
    if resultado.diferenca_pp is not None:
        sentido = "abaixo" if resultado.diferenca_pp >= 0 else "acima"
        pp = f"{abs(resultado.diferenca_pp):.1f}".replace(".", ",")
        st.markdown(
            f"A mesma nota fica **{pp} pontos percentuais {sentido}** quando comparada ao grupo de "
            f"escola privada com renda acima de 10 salários mínimos."
        )
        st.markdown(
            f"Sorteando uma pessoa da sua faixa e uma do grupo de contraste, a da sua faixa tem nota "
            f"maior em **{formatar_percentil(resultado.prob_superioridade * 100)}** dos pares "
            f"(empates contam metade)."
        )
    for aviso in resultado.avisos:
        st.caption(aviso)
    disponiveis = [c for c in (real, simulado) if c.disponivel]
    if disponiveis:
        st.dataframe(
            {
                "Grupo": [c.rotulo for c in disponiveis],
                "Participantes": [f"{c.n:,}".replace(",", ".") for c in disponiveis],
                "Média": [formatar_nota(c.media) for c in disponiveis],
                "Mediana": [formatar_nota(c.mediana) for c in disponiveis],
                "Desvio-padrão": [formatar_nota(c.desvio) for c in disponiveis],
                "Z-Score da sua nota": [formatar_z(c.z) for c in disponiveis],
            },
            hide_index=True,
        )
        st.plotly_chart(grafico(cdfs, e.ano, e.area, e.faixa, e.nota), config={"displayModeBar": False})


def main() -> None:
    st.set_page_config(page_title="Radar ENEM · Equidade socioeconômica", layout="centered")
    st.title("Equidade socioeconômica")
    st.write(
        "A mesma nota pode significar posições diferentes conforme o grupo de comparação. "
        "Informe sua nota e a renda da sua família e veja sua posição em dois cenários: "
        "entre participantes da sua faixa de renda e entre participantes de escola privada "
        "com renda familiar acima de 10 salários mínimos."
    )
    if not DIST_EQUIDADE.exists():
        st.error("Artefato do módulo ausente. Rode `scripts/etl.py` e depois `scripts/equidade.py`.")
        st.stop()
    cdfs = _cdfs()
    anos = sorted({ano for ano, _, _ in cdfs}, reverse=True)
    if not anos:
        st.error("Artefato do módulo sem nenhum grupo publicado.")
        st.stop()

    ano = st.selectbox("Edição de comparação", anos)
    try:
        opcoes = _opcoes(ano)
    except EntradaInvalida as erro:
        st.error(str(erro))
        st.stop()
    textos = dict(opcoes)

    with st.form("equidade"):
        alternativa = st.selectbox(
            "Qual é a renda mensal da sua família? (questionário do ENEM " + str(ano) + ")",
            [codigo for codigo, _ in opcoes], index=None,
            format_func=lambda c: f"{c}) {textos[c]}", placeholder="Selecione a sua resposta",
        )
        colunas = st.columns(2)
        notas = {}
        for i, (area, nome) in enumerate(AREAS.items()):
            notas[area] = colunas[i % 2].number_input(
                nome, min_value=0.0, max_value=1000.0, value=None,
                step=20.0 if area == "redacao" else 0.1, format="%.1f", placeholder="não informada",
            )
        enviado = st.form_submit_button("Comparar", type="primary")

    if not enviado:
        return
    if alternativa is None:
        st.warning("Informe a renda familiar para comparar por faixa de renda.")
        return
    informadas = {a: n for a, n in notas.items() if n is not None}
    if not informadas:
        st.warning("Informe ao menos uma nota.")
        return

    st.caption(f"Sua faixa: {FAIXA_POR_CODIGO[faixa_de_q006(alternativa)].rotulo}.")
    for area, nota in informadas.items():
        try:
            entrada = validar_entrada(ano, area, nota, alternativa, anos)
        except EntradaInvalida as erro:
            st.error(str(erro))
            continue
        mostrar(cdfs, comparar(cdfs, entrada))

    with st.expander("Como a comparação é feita"):
        st.markdown(
            f"""
- **Faixas de renda:** as 17 respostas da pergunta de renda (Q006) são agrupadas em seis
  faixas em salários mínimos da edição: até 1, de 1 a 2, de 2 a 3, de 3 a 5, de 5 a 10 e
  acima de 10.
- **Grupo de contraste:** {CONTRASTE_ROTULO.lower()}. Só entra quem declarou o tipo de escola;
  a maioria dos inscritos (quem já tinha concluído o ensino médio) não declara.
- **Quem entra:** participantes presentes nos dois dias e que não eram treineiros, com nota
  na área. Quem não respondeu à pergunta de renda fica fora deste módulo.
- **Posição:** porcentagem do grupo com nota abaixo da sua; notas iguais contam pela metade.
- **Privacidade:** grupos com menos de {PISO_GRUPO} participantes não são mostrados, o gráfico
  usa faixas de pelo menos {PISO_GRUPO} pessoas e o que você digita não é gravado.
- **Leitura:** o módulo descreve diferenças observadas entre grupos. Não indica que a renda
  causa a nota nem prevê aprovação.
- **Fonte:** Microdados do ENEM, INEP.
"""
        )


main()
