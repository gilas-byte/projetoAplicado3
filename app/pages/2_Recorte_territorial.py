"""Radar ENEM: módulo Recorte territorial (autor: Vinícius Joacir dos Anjos).

Página do app Streamlit. Lê apenas data/analytics/dist_territorial.parquet
(CDF agregada por edição, área e grupo territorial), gerado por
scripts/territorial.py. Regras em docs/decisoes (DL-04).

Privacidade (docs/privacidade.md, R6): notas e UF digitadas ficam só no
estado da sessão; nada é gravado, nada vai para a URL e nada vai para log.
O gráfico usa faixas de pelo menos PISO_GRUPO participantes.

Uso:
  ./.venv/bin/streamlit run app/app.py   (página "Recorte territorial")
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
from equidade import densidade_protegida  # noqa: E402
from territorial import (  # noqa: E402
    AREAS,
    BRASIL,
    NOMES_UF,
    REGIOES,
    UFS,
    EntradaInvalida,
    alcance_do_limite,
    carregar,
    comparar,
    formatar_inteiro,
    formatar_nota,
    formatar_percentil,
    formatar_z,
    grupo_regiao,
    grupo_uf,
    medianas_ufs,
    validar_entrada,
)

DIST_TERRITORIAL = Path(os.environ.get("RADAR_DIST_TERRITORIAL",
                                       RAIZ / "data" / "analytics" / "dist_territorial.parquet"))
COR_UF, COR_REGIAO, COR_BRASIL, COR_NOTA = "#2563eb", "#16a34a", "#6b7280", "#dc2626"


@st.cache_data
def _cdfs():
    return carregar(DIST_TERRITORIAL)


def grafico_distribuicoes(cdfs, e) -> go.Figure:
    fig = go.Figure()
    for grupo, nome, cor in ((grupo_uf(e.uf), NOMES_UF[e.uf], COR_UF),
                             (grupo_regiao(e.regiao), f"Região {REGIOES[e.regiao][0]}", COR_REGIAO),
                             (BRASIL, "Brasil", COR_BRASIL)):
        cdf = cdfs.get((e.ano, e.area, grupo))
        if not cdf:
            continue
        blocos = densidade_protegida(cdf)
        fig.add_trace(go.Scatter(
            x=[x for a, b, _ in blocos for x in (a, b)], y=[d for *_, d in blocos for _ in (0, 1)],
            mode="lines", name=nome, line=dict(color=cor, width=2),
            hovertemplate=nome + ": %{y:.2f}% do grupo a cada 10 pontos<extra></extra>",
        ))
    fig.add_vline(x=e.nota, line_width=2, line_dash="dash", line_color=COR_NOTA,
                  annotation_text="sua nota", annotation_position="top")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="Nota",
                      yaxis_title="% do grupo a cada 10 pontos", legend=dict(orientation="h", y=-0.25))
    return fig


def grafico_medianas(cdfs, e) -> go.Figure:
    ranking = medianas_ufs(cdfs, e.ano, e.area)[::-1]  # maior mediana no topo
    cores = [COR_UF if uf == e.uf else ("#93c5fd" if uf in REGIOES[e.regiao][1] else "#d1d5db")
             for uf, *_ in ranking]
    fig = go.Figure(go.Bar(
        x=[m for _, m, _ in ranking], y=[uf for uf, *_ in ranking], orientation="h", marker_color=cores,
        customdata=[[NOMES_UF[uf], formatar_inteiro(n)] for uf, _, n in ranking],
        hovertemplate="%{customdata[0]}: mediana %{x:.1f} (%{customdata[1]} participantes)<extra></extra>",
    ))
    fig.add_vline(x=e.nota, line_width=2, line_dash="dash", line_color=COR_NOTA)
    minimo = min((m for _, m, _ in ranking), default=0)
    fig.update_layout(height=max(300, 18 * len(ranking) + 60), margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(title="Mediana da UF", range=[max(0, min(minimo, e.nota) - 40), None]),
                      yaxis=dict(tickfont=dict(size=11)))
    return fig


def mostrar(cdfs, r) -> None:
    e = r.entrada
    st.subheader(f"{AREAS[e.area]}: nota {formatar_nota(e.nota)}")
    cenarios = (r.uf, r.regiao, r.brasil)
    for coluna, cenario in zip(st.columns(3), cenarios):
        with coluna:
            if cenario.disponivel:
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
            else:
                st.metric(cenario.rotulo, "—")
                st.info(f"{cenario.rotulo}: {cenario.motivo}.")
    if r.diferenca_pp is not None:
        sentido = "acima" if r.diferenca_pp >= 0 else "abaixo"
        pp = f"{abs(r.diferenca_pp):.1f}".replace(".", ",")
        st.markdown(f"Sua posição em {r.uf.rotulo} fica **{pp} pontos percentuais {sentido}** da sua "
                    f"posição no Brasil.")
    if r.prob_superioridade is not None:
        st.markdown(
            f"Sorteando um participante de {r.uf.rotulo} e um do restante do país, o de {r.uf.rotulo} "
            f"tem nota maior em **{formatar_percentil(r.prob_superioridade * 100)}** dos pares "
            f"(empates contam metade)."
        )
    if r.superioridade_regiao is not None:
        st.markdown(
            f"Na mesma comparação, a {r.regiao.rotulo} contra o restante do país: "
            f"**{formatar_percentil(r.superioridade_regiao * 100)}** dos pares."
        )
    if r.posicao_mediana is not None:
        empate = (f", empatada com {r.mediana_empatada_com} outra(s) UF(s)" if r.mediana_empatada_com else "")
        st.markdown(f"{r.uf.rotulo} tem a **{r.posicao_mediana}ª maior mediana entre as "
                    f"{r.ufs_comparadas} UFs**{empate} nesta edição e área.")
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
        st.plotly_chart(grafico_distribuicoes(cdfs, e), config={"displayModeBar": False})
    if r.ufs_comparadas:
        with st.expander("Mediana de cada UF"):
            st.plotly_chart(grafico_medianas(cdfs, e), config={"displayModeBar": False})


def main() -> None:
    st.set_page_config(page_title="Radar ENEM · Recorte territorial", layout="centered")
    st.title("Recorte territorial")
    st.write(
        "A mesma nota pode ocupar posições diferentes no seu estado, na sua região e no Brasil. "
        "Informe a UF onde fez a prova e suas notas para ver as três posições lado a lado."
    )
    if not DIST_TERRITORIAL.exists():
        st.error("Artefato do módulo ausente. Rode `scripts/etl.py` e depois `scripts/territorial.py`.")
        st.stop()
    cdfs = _cdfs()
    anos = sorted({ano for ano, _, _ in cdfs}, reverse=True)
    if not anos:
        st.error("Artefato do módulo sem nenhum grupo publicado.")
        st.stop()

    ano = st.selectbox("Edição de comparação", anos)
    with st.form("territorial"):
        uf = st.selectbox(
            "Em qual UF você fez a prova?", list(UFS), index=None,
            format_func=lambda s: f"{s} · {NOMES_UF[s]}", placeholder="Selecione a UF",
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
    if uf is None:
        st.warning("Informe a UF onde você fez a prova.")
        return
    informadas = {a: n for a, n in notas.items() if n is not None}
    if not informadas:
        st.warning("Informe ao menos uma nota.")
        return

    for area, nota in informadas.items():
        try:
            entrada = validar_entrada(ano, area, nota, uf, anos)
        except EntradaInvalida as erro:
            st.error(str(erro))
            continue
        mostrar(cdfs, comparar(cdfs, entrada))

    with st.expander("Como a comparação é feita"):
        st.markdown(
            f"""
- **Território:** a UF é a do **local de prova**, informada para todos os participantes. A UF
  da escola falta para a maioria (quem já tinha concluído o ensino médio não informa).
- **Regiões:** as cinco regiões do IBGE. O Brasil reúne as 27 UFs.
- **Quem entra:** participantes presentes nos dois dias e que não eram treineiros, com nota
  na área.
- **Posição:** porcentagem do grupo com nota abaixo da sua; notas iguais contam pela metade.
- **Comparação com o país:** a probabilidade de superioridade compara a UF com o restante do
  Brasil (sem a própria UF), para a UF não ser comparada com ela mesma.
- **Privacidade:** grupos com menos de {PISO_GRUPO} participantes não são mostrados, o gráfico
  usa faixas de pelo menos {PISO_GRUPO} pessoas, não há recorte por município e o que você
  digita não é gravado. Na UF e na região, quando a sua posição fica perto de uma das pontas
  do grupo, aparece só "acima de" ou "abaixo de" um limite, e a diferença para o Brasil não
  é mostrada. O limite cobre no mínimo as cerca de {PISO_GRUPO} pessoas mais extremas
  (contando pela metade quem tem nota igual à sua). Como ele é arredondado para uma casa
  decimal, nos grupos grandes cobre o 0,1% mais extremo; quando a sua posição estiver em
  limite, a legenda mostra quantas pessoas isso representa no grupo e na edição escolhidos.
  O limite depende da posição, não de quantas pessoas têm nota maior: com muitas notas
  iguais à sua, a posição pode sair exata mesmo com poucas pessoas acima.
- **Leitura:** o módulo descreve diferenças observadas entre territórios. Não indica que o
  lugar causa a nota: as UFs diferem em renda, rede de ensino e perfil de quem faz a prova.
- **Fonte:** Microdados do ENEM, INEP.
"""
        )


main()
