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
sys.path.insert(0, str(RAIZ / "app"))

from colunas import PISO_GRUPO  # noqa: E402
from estatistica import densidade_protegida, formatar_percentil  # noqa: E402
from ui import (  # noqa: E402
    COR_BRASIL,
    COR_NOTA,
    COR_PROPRIO,
    COR_VIZINHO,
    abertura,
    anel,
    aplicar_tema,
    estilo_grafico,
    rodape,
    ABAS_RESULTADO,
    visao_simples,
)
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
    formatar_z,
    opcoes_q006,
    validar_entrada,
)

DIST_EQUIDADE = Path(os.environ.get("RADAR_DIST_EQUIDADE", RAIZ / "data" / "analytics" / "dist_equidade.parquet"))
COR_FAIXA, COR_CONTRASTE = COR_PROPRIO, COR_VIZINHO


@st.cache_data
def _cdfs():
    return carregar(DIST_EQUIDADE)


@st.cache_data
def _opcoes(ano: int):
    return opcoes_q006(ano)


def grafico(cdfs, ano: int, area: str, faixa: str, nota: float) -> go.Figure:
    fig = go.Figure()
    for grupo, nome, cor in ((faixa, "Sua faixa de renda", COR_FAIXA),
                             (CONTRASTE, "Escola privada, > 10 SM", COR_CONTRASTE)):
        cdf = cdfs.get((ano, area, grupo))
        if not cdf:
            continue
        blocos = densidade_protegida(cdf)
        fig.add_trace(go.Bar(
            x=[(a + b) / 2 for a, b, _ in blocos], y=[d for *_, d in blocos],
            width=[b - a for a, b, _ in blocos], name=nome, marker_color=cor, opacity=0.5,
            marker_line_width=0, hovertemplate=nome + ": %{y:.2f}% do grupo a cada 10 pontos<extra></extra>",
        ))
    fig.add_vline(x=nota, line_width=2, line_dash="dash", line_color=COR_NOTA,
                  annotation_text="sua nota", annotation_position="top")
    fig.update_layout(barmode="overlay", bargap=0.05, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis_title="Nota", yaxis_title="% do grupo a cada 10 pontos",
                      legend=dict(orientation="h", y=-0.25))
    return estilo_grafico(fig)


def mostrar(cdfs, resultado) -> None:
    e, real, simulado = resultado.entrada, resultado.real, resultado.simulado
    destaque = real if real.disponivel else (simulado if simulado.disponivel else None)
    if destaque is not None:
        anel(destaque.texto, f"{AREAS[e.area]} | nota {formatar_nota(e.nota)}",
             f"{destaque.rotulo}: {destaque.n:,} participantes.".replace(",", "."),
             cor=COR_FAIXA if destaque is real else COR_CONTRASTE)
    else:
        st.subheader(f"{AREAS[e.area]}: nota {formatar_nota(e.nota)}")
    col1, col2 = st.columns(2)
    for coluna, cenario, titulo in ((col1, real, "1. Entre a sua faixa de renda"),
                                    (col2, simulado, "2. Entre escola privada de alta renda")):
        with coluna:
            if cenario.disponivel:
                st.metric(titulo, cenario.texto)
                # Só o número leva ponto de milhar: um replace na frase inteira
                # trocaria também a vírgula do texto ("sua, contando").
                participantes = f"{cenario.n:,}".replace(",", ".")
                if cenario.em_limite:
                    st.caption(f"Posição na ponta da distribuição dos {participantes} participantes do grupo "
                               f"({cenario.rotulo.lower()}); o valor exato não é exibido.")
                else:
                    st.caption(f"Percentil: parcela dos {participantes} participantes do grupo "
                               f"({cenario.rotulo.lower()}) com nota menor que a sua, contando metade "
                               f"de quem tirou a mesma nota.")
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
    if not disponiveis:
        return
    simples, tecnica = st.tabs(ABAS_RESULTADO)
    with simples:
        visao_simples([("Entre a sua faixa de renda" if c is real else "Entre escola privada de alta renda",
                        c.texto, COR_FAIXA if c is real else COR_CONTRASTE) for c in disponiveis])
    with tecnica:
        st.dataframe(
            {
                "Grupo": ["Sua faixa" if c.grupo != CONTRASTE else "Contraste" for c in disponiveis],
                "Participantes": [f"{c.n:,}".replace(",", ".") for c in disponiveis],
                "Média": [formatar_nota(c.media) for c in disponiveis],
                "Mediana": [formatar_nota(c.mediana) for c in disponiveis],
                "Desvio-padrão": [formatar_nota(c.desvio) for c in disponiveis],
                "Z da sua nota": [formatar_z(c.z) for c in disponiveis],
            },
            hide_index=True,
        )
        st.plotly_chart(grafico(cdfs, e.ano, e.area, e.faixa, e.nota), config={"displayModeBar": False})


def main() -> None:
    st.set_page_config(page_title="Radar ENEM · Equidade socioeconômica", layout="centered")
    aplicar_tema("equidade")
    st.title("Equidade socioeconômica")
    abertura(
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
    with st.container(key="resultado"):
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
- **Posição (percentil):** porcentagem do grupo com nota abaixo da sua; notas iguais contam
  pela metade. Na Redação as notas andam de 20 em 20 e muitas pessoas empatam, então o
  percentil pode passar da parcela com nota estritamente menor: quem tirou 0, por exemplo,
  não tem ninguém abaixo, mas recebe metade dos empatados. As redações com nota 0 (anuladas
  ou em branco) entram na comparação, como no resultado oficial.
- **Privacidade:** grupos com menos de {PISO_GRUPO} participantes não são mostrados, o gráfico
  usa faixas de pelo menos {PISO_GRUPO} pessoas e o que você digita não é gravado. Nas pontas
  da distribuição (as {PISO_GRUPO} pessoas mais extremas de cada lado, no mínimo) a posição
  aparece como "acima de" ou "abaixo de", sem o valor exato.
- **Leitura:** o módulo descreve diferenças observadas entre grupos. Não indica que a renda
  causa a nota nem prevê aprovação.
- **Fonte:** Microdados do ENEM, INEP.
"""
        )


main()
# Fora de main(): aparece mesmo quando a pagina retorna antes do resultado.
rodape()
