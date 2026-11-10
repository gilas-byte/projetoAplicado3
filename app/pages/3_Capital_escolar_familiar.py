"""Radar ENEM: módulo Capital escolar familiar (autor: Guilherme da Silva Anselmo).

Página do app Streamlit. Lê apenas data/analytics/dist_capital.parquet
(CDF agregada por edição, área e nível de escolaridade dos responsáveis),
gerado por scripts/capital_escolar.py. Regras em docs/decisoes (DL-05).

Privacidade (docs/privacidade.md, R6): notas e respostas digitadas ficam só
no estado da sessão; nada é gravado, nada vai para a URL e nada vai para log.
O gráfico usa faixas de pelo menos PISO_GRUPO participantes.

Uso:
  ./.venv/bin/streamlit run app/app.py   (página "Capital escolar familiar")
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
from capital_escolar import (  # noqa: E402
    AREAS,
    ROTULOS,
    EntradaInvalida,
    carregar,
    comparar,
    formatar_inteiro,
    formatar_nota,
    formatar_z,
    opcoes_escolaridade,
    validar_entrada,
)
from estatistica import alcance_do_limite, densidade_protegida, formatar_percentil  # noqa: E402

DIST_CAPITAL = Path(os.environ.get("RADAR_DIST_CAPITAL", RAIZ / "data" / "analytics" / "dist_capital.parquet"))
COR_PROPRIO, COR_VIZINHO, COR_BRASIL, COR_NOTA = "#2563eb", "#f59e0b", "#6b7280", "#dc2626"


@st.cache_data
def _cdfs():
    return carregar(DIST_CAPITAL)


@st.cache_data
def _opcoes(ano: int, variavel: str):
    return opcoes_escolaridade(ano, variavel)


def grafico(cdfs, r) -> go.Figure:
    e = r.entrada
    fig = go.Figure()
    for cenario, cor in ((r.proprio, COR_PROPRIO), (r.vizinho, COR_VIZINHO), (r.brasil, COR_BRASIL)):
        if cenario is None or not cenario.disponivel:
            continue
        blocos = densidade_protegida(cdfs[(e.ano, e.area, cenario.grupo)])
        fig.add_trace(go.Scatter(
            x=[x for a, b, _ in blocos for x in (a, b)], y=[d for *_, d in blocos for _ in (0, 1)],
            mode="lines", name=cenario.rotulo, line=dict(color=cor, width=2),
            hovertemplate=cenario.rotulo + ": %{y:.2f}% do grupo a cada 10 pontos<extra></extra>",
        ))
    fig.add_vline(x=e.nota, line_width=2, line_dash="dash", line_color=COR_NOTA,
                  annotation_text="sua nota", annotation_position="top")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="Nota",
                      yaxis_title="% do grupo a cada 10 pontos", legend=dict(orientation="h", y=-0.25))
    return fig


def mostrar_metrica(cenario) -> None:
    if not cenario.disponivel:
        st.metric(cenario.rotulo, "—")
        st.info(f"{cenario.rotulo}: {cenario.motivo}.")
        return
    st.metric(cenario.rotulo, cenario.texto_percentil)
    if cenario.em_limite:
        lado = "acima" if cenario.texto_percentil.startswith("acima") else "abaixo"
        pessoas = round(alcance_do_limite(cenario.n, lado))
        extremo = "do topo" if lado == "acima" else "da base"
        st.caption(f"sua posição está entre as cerca de {formatar_inteiro(pessoas)} pessoas mais "
                   f"perto {extremo}, num grupo de {formatar_inteiro(cenario.n)} participantes; o "
                   f"valor exato não é mostrado para proteger quem está nas pontas")
    else:
        st.caption(f"acima dessa porcentagem dos {formatar_inteiro(cenario.n)} participantes")


def mostrar(cdfs, r) -> None:
    e = r.entrada
    st.subheader(f"{AREAS[e.area]}: nota {formatar_nota(e.nota)}")
    cenarios = [c for c in (r.proprio, r.vizinho, r.brasil) if c is not None]
    for coluna, cenario in zip(st.columns(len(cenarios)), cenarios):
        with coluna:
            mostrar_metrica(cenario)
    if r.diferenca_pp is not None:
        sentido = "acima" if r.diferenca_pp >= 0 else "abaixo"
        pp = f"{abs(r.diferenca_pp):.1f}".replace(".", ",")
        st.markdown(f"A mesma nota fica **{pp} pontos percentuais {sentido}** na sua posição entre "
                    f"participantes do seu nível, comparada à posição entre participantes do nível "
                    f"{r.sentido_vizinho}.")
    if r.prob_superioridade is not None:
        st.markdown(
            f"Sorteando uma pessoa do seu nível e uma do nível {r.sentido_vizinho}, a do seu nível "
            f"tem nota maior em **{formatar_percentil(r.prob_superioridade * 100)}** dos pares "
            f"(empates contam metade)."
        )
    for aviso in r.avisos:
        st.caption(aviso)
    disponiveis = [c for c in cenarios if c.disponivel]
    if disponiveis:
        st.dataframe(
            {
                "Grupo": [c.rotulo for c in disponiveis],
                "Participantes": [formatar_inteiro(c.n) for c in disponiveis],
                "Média": [formatar_nota(c.media) for c in disponiveis],
                "Mediana": [formatar_nota(c.mediana) for c in disponiveis],
                "Desvio-padrão": [formatar_nota(c.desvio) for c in disponiveis],
                "Z da sua nota": [formatar_z(c.z) for c in disponiveis],
            },
            hide_index=True,
        )
        st.plotly_chart(grafico(cdfs, r), config={"displayModeBar": False})


def main() -> None:
    st.set_page_config(page_title="Radar ENEM · Capital escolar familiar", layout="centered")
    st.title("Capital escolar familiar")
    st.write(
        "A mesma nota pode ocupar posições diferentes conforme o grupo de comparação. "
        "Informe até que série seus responsáveis estudaram e suas notas para ver a sua posição entre "
        "participantes do mesmo nível de escolaridade familiar e na referência nacional."
    )
    if not DIST_CAPITAL.exists():
        st.error("Artefato do módulo ausente. Rode `scripts/etl.py` e depois `scripts/capital_escolar.py`.")
        st.stop()
    cdfs = _cdfs()
    anos = sorted({ano for ano, _, _ in cdfs}, reverse=True)
    if not anos:
        st.error("Artefato do módulo sem nenhum grupo publicado.")
        st.stop()

    ano = st.selectbox("Edição de comparação", anos)
    try:
        opcoes_pai, opcoes_mae = _opcoes(ano, "Q001"), _opcoes(ano, "Q002")
    except EntradaInvalida as erro:
        st.error(str(erro))
        st.stop()
    texto_pai, texto_mae = dict(opcoes_pai), dict(opcoes_mae)

    with st.form("capital"):
        pai = st.selectbox(
            f"Até que série seu pai, ou o homem responsável por você, estudou? (ENEM {ano})",
            [codigo for codigo, _ in opcoes_pai], index=None,
            format_func=lambda c: f"{c}) {texto_pai[c]}", placeholder="Selecione a sua resposta",
        )
        mae = st.selectbox(
            f"Até que série sua mãe, ou a mulher responsável por você, estudou? (ENEM {ano})",
            [codigo for codigo, _ in opcoes_mae], index=None,
            format_func=lambda c: f"{c}) {texto_mae[c]}", placeholder="Selecione a sua resposta",
        )
        colunas = st.columns(2)
        notas = {}
        for i, (area, nome) in enumerate(AREAS.items()):
            notas[area] = colunas[i % 2].number_input(
                nome, min_value=0.0, max_value=1000.0, value=None,
                step=20.0 if area == "redacao" else 0.1, format="%.1f", placeholder="não informada",
            )
        outro_nivel = st.checkbox(
            "Comparar também com participantes de outro nível de escolaridade (opcional)", value=False,
            help="Mostra a mesma nota entre participantes do nível imediatamente acima do seu "
                 "(ou abaixo, se o seu for o mais alto).",
        )
        enviado = st.form_submit_button("Comparar", type="primary")

    if not enviado:
        return
    if pai is None or mae is None:
        st.warning("Informe a escolaridade dos dois responsáveis (pode responder \"Não sei\").")
        return
    informadas = {a: n for a, n in notas.items() if n is not None}
    if not informadas:
        st.warning("Informe ao menos uma nota.")
        return

    for area, nota in informadas.items():
        try:
            entrada = validar_entrada(ano, area, nota, pai, mae, anos)
        except EntradaInvalida as erro:
            st.error(str(erro))
            continue
        if entrada.nivel is not None and area == next(iter(informadas)):
            st.caption(f"Seu grupo: {ROTULOS[entrada.nivel].lower()} (o maior nível entre pai e mãe).")
        mostrar(cdfs, comparar(cdfs, entrada, outro_nivel))

    with st.expander("Como a comparação é feita"):
        st.markdown(
            f"""
- **Seu nível:** o maior nível de escolaridade informado entre pai e mãe, em seis níveis:
  nunca estudou; Fundamental incompleto; Fundamental completo; Médio completo; Superior
  completo; Pós-graduação completa. Se um dos dois respondeu \"Não sei\" ou deixou
  em branco, vale o outro. **Limitação:** com pai \"Não sei\" e mãe \"Nunca estudou\", você entra no
  nível mais baixo, embora o pai possa ter estudado mais. O \"Não sei\" aparece com mais frequência
  na pergunta do pai do que na da mãe.
- **Sem informação nos dois:** você continua na posição nacional, mas não há nível de escolaridade
  para comparar.
- **Outro nível (opcional):** a comparação com um segundo nível fica desligada por padrão. Quando
  ligada, compara com o nível imediatamente acima do seu (ou abaixo, no nível mais alto). A
  linguagem do módulo descreve diferenças entre grupos e não classifica pessoas.
- **Quem entra:** participantes presentes nos dois dias e que não eram treineiros, com nota
  na área. Resposta fora das alternativas do questionário tira o participante dos níveis, e ele
  continua na posição nacional.
- **Posição (percentil):** porcentagem do grupo com nota abaixo da sua; notas iguais contam
  pela metade.
- **Privacidade:** grupos com menos de {PISO_GRUPO} participantes não são mostrados, o gráfico
  usa faixas de pelo menos {PISO_GRUPO} pessoas e o que você digita não é gravado. Quando a sua
  posição fica perto de uma das pontas do grupo, aparece só \"acima de\" ou \"abaixo de\" um limite,
  e a diferença entre níveis não é mostrada. O limite cobre no mínimo as cerca de {PISO_GRUPO} pessoas
  mais extremas (contando pela metade quem tem nota igual à sua).
- **Leitura:** o módulo descreve diferenças observadas entre grupos. Não indica que a escolaridade
  dos responsáveis causa a nota nem prevê resultado individual.
- **Fonte:** Microdados do ENEM, INEP.
"""
        )


main()
