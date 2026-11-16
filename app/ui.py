"""Radar ENEM: tema e pecas visuais compartilhadas pelas paginas do app.

So apresentacao: nada aqui calcula percentil nem le dados. As paginas passam o
texto que a logica ja devolveu (`texto_percentil`) e este modulo desenha.

Privacidade (docs/privacidade.md, R6): nada e gravado, nada vai para a URL e
nenhum recurso externo e carregado (as fontes ficam em app/static/fonts).
A barra de posicao so aparece quando o percentil NAO esta em limite de
exibicao (DL-04, item 8); perto das pontas o app mostra so o texto.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from streamlit import iframe as _iframe  # substitui st.components.v1.html (removido apos 06/2026)

# Papel de cada cor, igual nas quatro telas e nos dois temas. Cada uma tem
# contraste de pelo menos 3:1 (WCAG 2.1, criterio 1.4.11, elementos graficos) com o
# fundo e com os cartoes do tema claro e do escuro: luminancia relativa perto de 0,2,
# o meio-termo entre os dois fundos. Conferido em tests/test_ui.py (TestContraste).
# As versoes anteriores (#3b8cff, #e0a63a, #8b95a5, #ef5a5a) foram pensadas para o
# tema escuro e ficavam entre 2,0:1 e 3,1:1 no claro, que virou o padrao em 15/11/2026.
COR_PROPRIO = "#1375ff"  # seu nivel / sua faixa / sua UF
COR_VIZINHO = "#a3731a"  # nivel acima / contraste / regiao
COR_BRASIL = "#707d90"  # referencia nacional
COR_NOTA = "#eb3030"  # a nota digitada

# Cores de superficie por tema. As cores de papel (COR_*) servem nos dois temas.
_PALETAS = {
    "dark": dict(bg="#0d1016", surf="#131820", line="#252c38", line2="#323b4a", tx="#e6e9ee", mu="#8b95a5",
                 azul="#1f6fe5", glow="rgba(59,140,255,.55)", glow2="rgba(59,140,255,.28)", btn_hover="#1859c4",
                 borda_hover="#3d4a5e", side="#0a0d13", ciano="#22d3ee", fraco1="#586882", fraco2="#5e6573",
                 sombra_nota="rgba(239,90,90,.8)"),
    "light": dict(bg="#f4f6fa", surf="#ffffff", line="#dbe1ea", line2="#c5cdd9", tx="#141a24", mu="#5b6677",
                  azul="#1f6fe5", glow="rgba(31,111,229,.38)", glow2="rgba(31,111,229,.16)", btn_hover="#1859c4",
                  borda_hover="#aab5c6", side="#eceff5", ciano="#0a6f8c", fraco1="#7489ab", fraco2="#7c8492",
                  sombra_nota="rgba(217,60,60,.5)"),
}


# fraco1/fraco2: o resto da distribuicao e os grupos de contexto. Tambem passam de 3:1
# com o fundo do proprio tema; a diferenca para COR_PROPRIO vem do tom (cinza contra
# azul saturado) e, nos graficos, tambem da linha tracejada da nota ou do simbolo.
# ciano: texto pequeno (posicao da metrica), entao passa de 4,5:1 (criterio 1.4.3).
# azul e btn_hover: fundo do botao com texto branco, tambem 4,5:1 (antes 3,3:1 no escuro).


def tema_atual() -> str:
    """\"dark\" ou \"light\", conforme o tema ativo no navegador (padrao: light)."""
    try:
        tipo = st.context.theme.type
    except Exception:  # fora de uma sessao (teste isolado) ou versao sem o recurso
        tipo = None
    return "dark" if tipo == "dark" else "light"


def paleta() -> dict:
    return _PALETAS[tema_atual()]


_CSS = """
<style>
:root{--r-raio:16px;__ROOT__;--r-mono:'IBM Plex Mono',ui-monospace,monospace}
header[data-testid="stHeader"]{background:transparent}
.stMainBlockContainer{padding-top:2.2rem;padding-bottom:4rem;max-width:640px}
h1,h2,h3{font-family:var(--r-mono)!important;letter-spacing:-.01em}
h1{font-size:1.6rem!important;font-weight:600!important}
h2{font-size:1.15rem!important;font-weight:600!important}
h3{font-size:1rem!important;font-weight:600!important}
[data-testid="stNumberInputStepUp"],[data-testid="stNumberInputStepDown"]{display:none}
[data-testid="stColumn"] [data-testid="stWidgetLabel"]{min-height:2.5em;align-items:flex-end}
[data-testid="stWidgetLabel"] p{font-family:var(--r-mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--r-mu)}
[data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p{font-family:inherit;text-transform:none;letter-spacing:0;font-size:.9rem;color:var(--r-tx)}
[data-testid="stForm"]{border:1px solid var(--r-line);background:var(--r-surf);border-radius:var(--r-raio);padding:1.1rem}
[data-testid="stBaseButton-primaryFormSubmit"],[data-testid="stBaseButton-primary"]{width:100%;font-family:var(--r-mono);font-weight:600;text-transform:uppercase;letter-spacing:.05em;border:0;background:var(--r-azul);color:#fff;padding:.7rem 1rem;box-shadow:0 0 14px var(--r-glow);transition:background .15s,box-shadow .2s,transform .15s}
[data-testid="stBaseButton-primaryFormSubmit"]:hover,[data-testid="stBaseButton-primary"]:hover{background:var(--r-btn-hover);color:#fff;box-shadow:0 0 24px var(--r-glow),0 0 48px var(--r-glow2);transform:translateY(-2px)}
[data-testid="stBaseButton-primaryFormSubmit"]:active,[data-testid="stBaseButton-primary"]:active{transform:scale(.98)}
[data-testid="stElementContainer"]:has([data-testid="stFormSubmitButton"]),div:has(>[data-testid="stFormSubmitButton"]),[data-testid="stFormSubmitButton"],[data-testid="stFormSubmitButton"]>button{width:100%!important}
[data-testid="stForm"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;gap:.8rem}
[data-testid="stForm"] [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important;width:auto!important}
[data-testid="stMetric"]{background:var(--r-surf);border:1px solid var(--r-line);border-radius:var(--r-raio);padding:.8rem 1rem;transition:border-color .15s}
[data-testid="stMetric"]:hover{border-color:var(--r-borda-hover);transform:translateY(-3px)}
[data-testid="stMetric"]{transition:border-color .2s,transform .2s}
[data-testid="stForm"]{transition:border-color .2s}[data-testid="stForm"]:focus-within{border-color:var(--r-borda-hover)}
[data-testid="stExpander"]{transition:border-color .2s}[data-testid="stExpander"]:hover{border-color:var(--r-borda-hover)}
[data-testid="stMetricLabel"] p{white-space:normal!important;font-family:var(--r-mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--r-mu)}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{font-family:var(--r-mono)!important;font-weight:600;font-variant-numeric:tabular-nums}
[data-testid="stMetricValue"]{font-size:1.4rem}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] div,[data-testid="stMetricValue"] p{white-space:normal!important;overflow:visible!important;text-overflow:clip!important;overflow-wrap:anywhere;line-height:1.2;min-width:0}
[data-testid="stMetricDelta"],[data-testid="stMetricDelta"] *{color:var(--r-ciano)!important;font-family:var(--r-mono)}
[data-testid="stExpander"]{border:1px solid var(--r-line);border-radius:var(--r-raio);background:transparent}
[data-testid="stExpander"] summary:hover{color:var(--r-azul)}
[data-testid="stAlert"]{border-radius:var(--r-raio)}
[data-testid="stDataFrame"]{border-radius:var(--r-raio);overflow:hidden}
[data-baseweb="tab-highlight"]{background:var(--r-azul)!important;height:2px!important}
[data-baseweb="tab"]{font-family:var(--r-mono)}

[data-testid="stSidebar"]{background:var(--r-side);border-right:1px solid var(--r-line)}
[data-testid="stSidebarContent"]{padding:1.2rem .9rem}
[data-testid="stSidebarHeader"]{display:none}
.r-logo{display:flex;align-items:center;gap:.7rem;font:600 1.05rem var(--r-mono);letter-spacing:-.01em;padding:.2rem .4rem 1.3rem;border-bottom:1px solid var(--r-line);margin-bottom:1rem}
.r-logo b{color:var(--r-azul)}
.r-logo svg{flex:none;filter:drop-shadow(0 0 5px var(--r-glow))}
.r-menu{font:600 .68rem var(--r-mono);text-transform:uppercase;letter-spacing:.12em;color:var(--r-mu);padding:0 .5rem .5rem}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{position:relative;border-radius:12px;padding:.62rem .8rem;gap:.75rem;color:var(--r-mu);border:1px solid transparent;transition:background .2s,color .2s,transform .2s,border-color .2s}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p{font-size:.92rem}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{background:var(--r-surf);color:var(--r-tx);transform:translateX(4px);border-color:var(--r-line)}
@keyframes r-barra{from{transform:scaleY(0);opacity:0}}
[data-testid="stSidebarCollapseButton"] button,[data-testid="stExpandSidebarButton"]{color:var(--r-mu);transition:color .2s}
[data-testid="stSidebarCollapseButton"] button:hover,[data-testid="stExpandSidebarButton"]:hover{color:var(--r-azul)}

[data-testid="stSidebar"] [data-testid="stIFrame"],[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stIFrame"]){display:none}
[data-testid="stSidebar"] [data-testid="stCheckbox"]{padding:.5rem .8rem;margin-top:.8rem;border-top:1px solid var(--r-line)}
[data-testid="stSidebar"] [data-testid="stCheckbox"] [data-testid="stWidgetLabel"] p{font:600 .72rem var(--r-mono);text-transform:uppercase;letter-spacing:.08em;color:var(--r-mu)}
.r-lead{color:var(--r-mu);max-width:52ch;margin:0 0 1.4rem}
.r-rodape{color:var(--r-mu);font-size:.78rem;border-top:1px solid var(--r-line);padding-top:.8rem;margin-top:2rem}
.r-sec{border-top:1px solid var(--r-line);padding:1.1rem 0 .4rem}
.r-tit{font:600 .72rem var(--r-mono);text-transform:uppercase;letter-spacing:.08em;color:var(--r-mu);margin:0 0 .5rem}
.r-lin{display:grid;grid-template-columns:10px 1fr auto;gap:.2rem .7rem;align-items:center;padding:.7rem 0;border-bottom:1px solid var(--r-line)}
.r-lin:last-child{border-bottom:0}
.r-sq{width:10px;height:10px;background:var(--c)}
.r-nome{font-size:.92rem;line-height:1.25}.r-nome small{display:block;color:var(--r-mu);font-size:.78rem}
.r-val{font:600 1rem var(--r-mono);text-align:right}
.r-bar{grid-column:2/4;height:3px;background:var(--r-line);position:relative}
.r-bar i{position:absolute;left:0;top:0;bottom:0;width:var(--w);background:var(--c);animation:r-bar 1.3s .2s cubic-bezier(.2,.7,.2,1) backwards}
@keyframes r-bar{from{width:0}}

.st-key-resultado>div>[data-testid="stElementContainer"],.st-key-resultado>div>[data-testid="stVerticalBlock"]{animation:r-in .55s cubic-bezier(.2,.7,.2,1) backwards}
.st-key-resultado>div>:nth-child(2){animation-delay:.1s}.st-key-resultado>div>:nth-child(3){animation-delay:.2s}
.st-key-resultado>div>:nth-child(4){animation-delay:.3s}.st-key-resultado>div>:nth-child(5){animation-delay:.4s}
.st-key-resultado>div>:nth-child(6){animation-delay:.5s}.st-key-resultado>div>:nth-child(n+7){animation-delay:.6s}
@keyframes r-in{from{opacity:0;transform:translateY(16px)}}
.st-key-resultado [data-testid="stMetricValue"]{animation:r-val .7s .35s cubic-bezier(.2,.7,.2,1) backwards}
@keyframes r-val{from{opacity:0;transform:translateX(-12px)}}
.st-key-resultado .js-plotly-plot .scatterlayer .js-line{animation:r-draw 1.8s .25s cubic-bezier(.3,.6,.2,1) backwards}
@keyframes r-draw{from{stroke-dasharray:4000;stroke-dashoffset:4000}to{stroke-dasharray:4000;stroke-dashoffset:0}}
.st-key-resultado .js-plotly-plot .barlayer .point path{transform-box:fill-box;transform-origin:50% 100%;animation:r-grow .9s cubic-bezier(.2,.7,.2,1) backwards}
@keyframes r-grow{from{transform:scaleY(0)}}
.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(1) path{animation-delay:16ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(2) path{animation-delay:32ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(3) path{animation-delay:48ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(4) path{animation-delay:64ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(5) path{animation-delay:80ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(6) path{animation-delay:96ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(7) path{animation-delay:112ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(8) path{animation-delay:128ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(9) path{animation-delay:144ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(10) path{animation-delay:160ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(11) path{animation-delay:176ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(12) path{animation-delay:192ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(13) path{animation-delay:208ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(14) path{animation-delay:224ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(15) path{animation-delay:240ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(16) path{animation-delay:256ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(17) path{animation-delay:272ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(18) path{animation-delay:288ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(19) path{animation-delay:304ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(20) path{animation-delay:320ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(21) path{animation-delay:336ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(22) path{animation-delay:352ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(23) path{animation-delay:368ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(24) path{animation-delay:384ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(25) path{animation-delay:400ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(26) path{animation-delay:416ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(27) path{animation-delay:432ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(28) path{animation-delay:448ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(29) path{animation-delay:464ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(30) path{animation-delay:480ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(31) path{animation-delay:496ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(32) path{animation-delay:512ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(33) path{animation-delay:528ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(34) path{animation-delay:544ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(35) path{animation-delay:560ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(36) path{animation-delay:576ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(37) path{animation-delay:592ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(38) path{animation-delay:608ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(39) path{animation-delay:624ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(40) path{animation-delay:640ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(41) path{animation-delay:656ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(42) path{animation-delay:672ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(43) path{animation-delay:688ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(44) path{animation-delay:704ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(45) path{animation-delay:720ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(46) path{animation-delay:736ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(47) path{animation-delay:752ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(48) path{animation-delay:768ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(49) path{animation-delay:784ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(50) path{animation-delay:800ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(51) path{animation-delay:816ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(52) path{animation-delay:832ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(53) path{animation-delay:848ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(54) path{animation-delay:864ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(55) path{animation-delay:880ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(56) path{animation-delay:896ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(57) path{animation-delay:912ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(58) path{animation-delay:928ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(59) path{animation-delay:944ms}.st-key-resultado .js-plotly-plot .barlayer .point:nth-child(60) path{animation-delay:960ms}
.js-plotly-plot .shapelayer path{filter:drop-shadow(0 0 4px var(--r-sombra-nota))}
.js-plotly-plot .infolayer .annotation text{filter:drop-shadow(0 0 4px var(--r-sombra-nota))}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
"""


# (chave, arquivo, rotulo, icone, href que o Streamlit gera para a pagina)
_PAGINAS = (
    ("inicio", "app.py", "Início", ":material/home:", ""),
    ("equidade", "pages/1_Equidade_socioeconomica.py", "Equidade socioeconômica", ":material/balance:", "Equidade_socioeconomica"),
    ("territorial", "pages/2_Recorte_territorial.py", "Recorte territorial", ":material/map:", "Recorte_territorial"),
    ("capital", "pages/3_Capital_escolar_familiar.py", "Capital escolar familiar", ":material/school:", "Capital_escolar_familiar"),
)

# O Streamlit nao marca o link da pagina atual de forma estavel (as classes mudam a
# cada versao), entao a pagina diz quem esta ativa e o CSS do item sai daqui.
_CSS_ATIVO = (
    '<style>[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][href="{h}"]{{background:var(--r-surf);'
    'color:var(--r-tx);border-color:var(--r-line)}}'
    '[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][href="{h}"]::before{{content:"";position:absolute;'
    'left:-.9rem;top:18%;bottom:18%;width:4px;border-radius:0 4px 4px 0;background:var(--r-azul);'
    'box-shadow:0 0 10px var(--r-azul),0 0 22px var(--r-glow);animation:r-barra .45s cubic-bezier(.2,.7,.2,1) both}}'
    '[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][href="{h}"] [data-testid="stIconMaterial"]{{'
    'color:var(--r-azul);filter:drop-shadow(0 0 5px var(--r-glow))}}</style>'
)

def _logo() -> str:
    c = paleta()
    return (
        '<div class="r-logo"><svg width="26" height="26" viewBox="0 0 26 26" fill="none">'
        f'<circle cx="13" cy="13" r="10.5" stroke="{c["line"]}" stroke-width="2.4"/>'
        f'<path d="M13 2.5a10.5 10.5 0 0 1 10.5 10.5" stroke="{c["azul"]}" stroke-width="2.4" stroke-linecap="round"/>'
        f'<circle cx="13" cy="13" r="2.6" fill="{c["azul"]}"/></svg>'
        '<span>radar<b>.</b>enem</span></div><p class="r-menu">Módulos</p>'
    )


def _sidebar(ativa: str) -> None:
    """Navegacao propria (a nativa chama a pagina principal de "app")."""
    with st.sidebar:
        st.html(_logo())
        href = next((h for chave, _, _, _, h in _PAGINAS if chave == ativa), None)
        if href is not None:
            st.html(_CSS_ATIVO.format(h=href))
        for _, arquivo, rotulo, icone, _ in _PAGINAS:
            try:
                st.page_link(arquivo, label=rotulo, icon=icone)
            except Exception:  # pagina fora do contexto multipagina (ex.: teste isolado)
                pass


_ALTERNAR = """<!doctype html><html><body><script>
// O Streamlit guarda o tema escolhido em localStorage, uma chave por pagina.
const forcar = __FORCAR__;
const caminhos = ["/", "/Equidade_socioeconomica", "/Recorte_territorial", "/Capital_escolar_familiar"];
const guardar = (tema) => caminhos.forEach((c) => parent.localStorage.setItem("stActiveTheme-" + c + "-v2", JSON.stringify(tema)));
if (forcar) {            // o usuario mexeu no interruptor
  guardar(forcar);
  parent.location.reload();
} else {                 // primeira visita: o app abre no claro, mesmo com o sistema escuro
  const k = "stActiveTheme-" + parent.location.pathname + "-v2";
  const v = parent.localStorage.getItem(k);
  if (v === null || v === '"System"') {
    guardar("Light");
    if (parent.matchMedia("(prefers-color-scheme: dark)").matches) parent.location.reload();
  }
}
</script></body></html>"""


def _pedir_troca() -> None:
    """Callback do interruptor: marca que foi o usuario quem mexeu (o valor novo vem no proximo run)."""
    st.session_state["_r_troca"] = True


def _alternador() -> None:
    """Interruptor "Modo escuro" da sidebar (o claro e o padrao). So troca de tema quando o usuario mexe nele: o estado do
    widget nao e fonte de verdade, porque o tema ativo so chega ao servidor depois do primeiro run."""
    atual = tema_atual()
    with st.sidebar:
        escuro = st.toggle("Modo escuro", value=atual == "dark", on_change=_pedir_troca)
    forcar = "null"
    if st.session_state.pop("_r_troca", False):
        forcar = '"Dark"' if escuro else '"Light"'
    _iframe(_ALTERNAR.replace("__FORCAR__", forcar), height=1)


def aplicar_tema(pagina: str) -> None:
    """Injeta o CSS e a sidebar do app. Chamar uma vez por pagina, logo apos set_page_config.

    `pagina` e a chave da pagina atual: "inicio", "equidade", "territorial" ou "capital".
    """
    c = paleta()
    root = ";".join(f"--r-{k.replace('_', '-')}:{v}" for k, v in c.items())
    st.html(_CSS.replace("__ROOT__", root))
    _sidebar(pagina)
    _alternador()


def abertura(texto: str) -> None:
    """Paragrafo de abertura da pagina, em cinza e com largura de leitura."""
    st.html(f'<p class="r-lead">{escape(texto)}</p>')


def grupos(titulo: str, itens: list[dict]) -> None:
    """Lista de grupos com quadrado de cor, valor e barra fina de posicao.

    Cada item: rotulo, detalhe, valor (texto ja pronto, ex.: "acima de 58,3%"),
    cor e pct (0 a 100, ou None para nao desenhar a barra).
    """
    linhas = []
    for it in itens:
        barra = ""
        if it.get("pct") is not None:
            pct = max(0.0, min(100.0, float(it["pct"])))
            barra = f'<div class="r-bar"><i style="--w:{pct:.1f}%"></i></div>'
        detalhe = f"<small>{escape(it['detalhe'])}</small>" if it.get("detalhe") else ""
        linhas.append(
            f'<div class="r-lin" style="--c:{escape(it["cor"])}"><span class="r-sq"></span>'
            f'<div class="r-nome">{escape(it["rotulo"])}{detalhe}</div>'
            f'<div class="r-val">{escape(it["valor"])}</div>{barra}</div>'
        )
    st.html(f'<div class="r-sec"><p class="r-tit">{escape(titulo)}</p>{"".join(linhas)}</div>')


# ------------------------------------------------------------------ ANEL

_ANEL = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:'IBM Plex Mono';font-weight:600;src:url('/app/static/fonts/ibm-plex-mono-600.woff2') format('woff2')}
@font-face{font-family:'IBM Plex Sans';font-weight:400;src:url('/app/static/fonts/ibm-plex-sans-400.woff2') format('woff2')}
@font-face{font-family:'IBM Plex Sans';font-weight:600;src:url('/app/static/fonts/ibm-plex-sans-600.woff2') format('woff2')}
*{box-sizing:border-box;margin:0;padding:0}
body{background:transparent;color:__TX__;font:400 15px/1.5 'IBM Plex Sans',system-ui,sans-serif;display:flex;gap:18px;align-items:center;padding:6px 2px}
.ring{position:relative;width:128px;height:128px;flex:none}
.ring svg{display:block;transform:rotate(-90deg)}
.n{position:absolute;inset:0;display:grid;place-content:center;text-align:center;font:600 26px 'IBM Plex Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums}
.n>span>span{text-shadow:__SOMBRA__}
@keyframes pulso{50%{filter:drop-shadow(0 0 14px __COR__) drop-shadow(0 0 4px __COR__)}}
#arc.fim{animation:pulso .9s ease-in-out 1}
.n small{display:block;font:600 10px 'IBM Plex Mono',ui-monospace,monospace;color:__MU__;text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px}
h2{font:600 11px 'IBM Plex Mono',ui-monospace,monospace;text-transform:uppercase;letter-spacing:.08em;color:__MU__;margin-bottom:6px}
p{font-size:14px;color:__TX__}
</style></head><body>
<div class="ring"><svg width="128" height="128" viewBox="0 0 128 128"><circle cx="64" cy="64" r="56" fill="none" stroke="__LINHA__" stroke-width="6"/>
<circle id="arc" cx="64" cy="64" r="56" fill="none" stroke="__COR__" stroke-width="6" stroke-linecap="round" stroke-dasharray="351.86" stroke-dashoffset="351.86" style="filter:drop-shadow(0 0 5px __COR__)"/></svg>
<div class="n" style="font-size:__TAM__px"><span><small>__ROTULO__</small><span id="v">__FINAL__</span></span></div></div>
<div><h2>__TITULO__</h2><p>__DESCRICAO__</p></div>
<script>
const ALVO=__ALVO__,FINAL=__FINAL_JS__,ANIMA=__ANIMA__;
const arc=document.getElementById('arc'),v=document.getElementById('v'),C=351.86;
const quieto=matchMedia('(prefers-reduced-motion: reduce)').matches||!ANIMA;
function pos(x){arc.style.strokeDashoffset=C*(1-x/100)}
if(quieto){pos(ALVO);v.textContent=FINAL}
else{v.textContent='0,0%';arc.style.transition='stroke-dashoffset 1.7s cubic-bezier(.2,.7,.2,1)';
 requestAnimationFrame(()=>requestAnimationFrame(()=>pos(ALVO)));
 const t0=performance.now();(function tick(t){const k=Math.min(1,(t-t0)/1700),e=1-Math.pow(1-k,3);
  v.textContent=k<1?(ALVO*e).toFixed(1).replace('.',',')+'%':FINAL;if(k<1)requestAnimationFrame(tick);else arc.classList.add('fim')})(t0)}
</script></body></html>"""

_TEXTO_PERCENTIL = re.compile(r"(acima de |abaixo de )?(\d{1,3}),(\d)%")


def anel(texto: str, titulo: str, descricao: str, cor: str = COR_PROPRIO, altura: int = 150) -> None:
    """Anel de posicao com contador de 0 ate o valor.

    `texto` e o texto que a logica ja devolveu (`texto_percentil`, ex.: "58,3%"
    ou "acima de 99,9%"). O anel anima so esse valor: nunca recebe o percentil
    exato, entao nao revela nada alem do que o texto ja mostra (DL-04, item 8).
    Texto fora do formato aparece parado, sem animar.
    """
    m = _TEXTO_PERCENTIL.fullmatch(texto.strip())
    alvo = float(f"{m.group(2)}.{m.group(3)}") if m else 0.0
    rotulo = (m.group(1) or "percentil ").strip() if m else ""  # prefixo so quando vem do texto
    final = f"{m.group(2)},{m.group(3)}%" if m else texto  # o prefixo vai no rotulo pequeno
    c = paleta()
    corpo = (
        _ANEL.replace("__TX__", c["tx"]).replace("__MU__", c["mu"]).replace("__LINHA__", c["line"])
        .replace("__COR__", escape(cor))
        .replace("__SOMBRA__", f"0 0 14px {escape(cor)}" if tema_atual() == "dark" else "none")
        .replace("__ROTULO__", escape(rotulo))
        .replace("__FINAL__", escape(final))
        .replace("__FINAL_JS__", json.dumps(final))
        .replace("__ALVO__", repr(alvo))
        .replace("__TAM__", "26" if m else "15")
        .replace("__ANIMA__", "true" if m else "false")
        .replace("__TITULO__", escape(titulo))
        .replace("__DESCRICAO__", escape(descricao))
    )
    _iframe(corpo, height=altura)


# --------------------------------------------------------------- RODAPE

_MANIFESTO_PUBLICACAO = Path(__file__).resolve().parent.parent / "data" / "analytics" / "_manifesto_publicacao.json"


@lru_cache(maxsize=1)
def _versao_dos_dados(caminho: Path = _MANIFESTO_PUBLICACAO) -> tuple[str, str] | None:
    """(data da auditoria, commit curto) do manifesto gravado por scripts/auditar_artefatos.py.

    O manifesto so tem hashes, tamanhos e datas dos artefatos agregados; nenhuma contagem
    vai para a tela. Sem o arquivo (por exemplo, rodando so com os testes), o rodape
    mostra apenas a fonte.
    """
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        quando = datetime.fromisoformat(dados["auditado_em_utc"]).strftime("%d/%m/%Y")
        return quando, str(dados.get("versao_codigo_git") or "")[:7]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def rodape() -> None:
    """Fonte e versao dos dados no fim de cada pagina (BI: todo painel mostra fonte e atualizacao)."""
    texto = "Fonte: Microdados do ENEM 2019 a 2022, INEP, processados pela equipe Radar ENEM."
    versao = _versao_dos_dados()
    if versao is not None:
        quando, commit = versao
        texto += f" Dados agregados conferidos em {quando}"
        texto += f" (código {commit})." if commit else "."
    st.html(f'<p class="r-rodape">{escape(texto)}</p>')


# --------------------------------------------------------------- GRAFICOS


def estilo_grafico(fig: go.Figure, altura: int = 320) -> go.Figure:
    """Aplica o visual do app (fundo transparente, linhas finas, fonte Plex) a um grafico Plotly."""
    c = paleta()
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color=c["mu"], size=12),
        title=dict(font=dict(family="IBM Plex Mono, monospace", size=13, color=c["tx"]), x=0, xanchor="left"),
        hoverlabel=dict(bgcolor=c["surf"], bordercolor=c["line2"], font=dict(family="IBM Plex Mono, monospace", color=c["tx"])),
        legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)", y=-0.38, yanchor="top"),
    )
    eixo = dict(gridcolor=c["line"], zerolinecolor=c["line2"], linecolor=c["line2"],
                tickfont=dict(family="IBM Plex Mono, monospace", size=11))
    fig.update_xaxes(**eixo)
    fig.update_yaxes(**eixo)
    return fig
