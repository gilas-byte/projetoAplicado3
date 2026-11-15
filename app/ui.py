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
from html import escape

import plotly.graph_objects as go
import streamlit as st
from streamlit.components.v1 import html as _iframe

# Papel de cada cor, igual nas quatro telas.
COR_PROPRIO = "#4c8dff"  # seu nivel / sua faixa / sua UF
COR_VIZINHO = "#e0a63a"  # nivel acima / contraste / regiao
COR_BRASIL = "#8b95a5"  # referencia nacional
COR_NOTA = "#ef5a5a"  # a nota digitada

_CSS = """
<style>
:root{--r-bg:#0d1016;--r-surf:#131820;--r-line:#252c38;--r-line2:#323b4a;--r-tx:#e6e9ee;--r-mu:#8b95a5;
 --r-azul:#4c8dff;--r-mono:'IBM Plex Mono',ui-monospace,monospace}
header[data-testid="stHeader"]{background:transparent}
.stMainBlockContainer{padding-top:2.2rem;padding-bottom:4rem;max-width:640px}
h1,h2,h3{font-family:var(--r-mono)!important;letter-spacing:-.01em}
h1{font-size:1.6rem!important;font-weight:600!important}
h2{font-size:1.15rem!important;font-weight:600!important}
h3{font-size:1rem!important;font-weight:600!important}
[data-testid="stNumberInputStepUp"],[data-testid="stNumberInputStepDown"]{display:none}
[data-testid="stColumn"] [data-testid="stWidgetLabel"]{min-height:2.5em;align-items:flex-end}
[data-testid="stWidgetLabel"] p{font-family:var(--r-mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--r-mu)}
[data-testid="stForm"]{border:1px solid var(--r-line);background:var(--r-surf);border-radius:10px;padding:1.1rem}
[data-testid="stBaseButton-primaryFormSubmit"],[data-testid="stBaseButton-primary"]{width:100%;font-family:var(--r-mono);font-weight:600;text-transform:uppercase;letter-spacing:.05em;border:0;background:var(--r-azul);color:#fff;padding:.7rem 1rem;transition:background .15s}
[data-testid="stBaseButton-primaryFormSubmit"]:hover,[data-testid="stBaseButton-primary"]:hover{background:#6aa0ff;color:#fff}
[data-testid="stElementContainer"]:has([data-testid="stFormSubmitButton"]),div:has(>[data-testid="stFormSubmitButton"]),[data-testid="stFormSubmitButton"],[data-testid="stFormSubmitButton"]>button{width:100%!important}
[data-testid="stForm"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;gap:.8rem}
[data-testid="stForm"] [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important;width:auto!important}
[data-testid="stMetric"]{background:var(--r-surf);border:1px solid var(--r-line);border-radius:10px;padding:.8rem 1rem;transition:border-color .15s}
[data-testid="stMetric"]:hover{border-color:var(--r-line2)}
[data-testid="stMetricLabel"] p{font-family:var(--r-mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--r-mu)}
[data-testid="stMetricValue"]{font-family:var(--r-mono);font-weight:600;font-variant-numeric:tabular-nums}
[data-testid="stExpander"]{border:1px solid var(--r-line);border-radius:10px;background:transparent}
[data-testid="stExpander"] summary:hover{color:var(--r-azul)}
[data-testid="stAlert"]{border-radius:10px}
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}
[data-baseweb="tab-highlight"]{background:var(--r-azul)!important;height:2px!important}
[data-baseweb="tab"]{font-family:var(--r-mono)}

.r-lead{color:var(--r-mu);max-width:52ch;margin:0 0 1.4rem}
.r-sec{border-top:1px solid var(--r-line);padding:1.1rem 0 .4rem}
.r-tit{font:600 .72rem var(--r-mono);text-transform:uppercase;letter-spacing:.08em;color:var(--r-mu);margin:0 0 .5rem}
.r-lin{display:grid;grid-template-columns:10px 1fr auto;gap:.2rem .7rem;align-items:center;padding:.7rem 0;border-bottom:1px solid var(--r-line)}
.r-lin:last-child{border-bottom:0}
.r-sq{width:10px;height:10px;background:var(--c)}
.r-nome{font-size:.92rem;line-height:1.25}.r-nome small{display:block;color:var(--r-mu);font-size:.78rem}
.r-val{font:600 1rem var(--r-mono);text-align:right}
.r-bar{grid-column:2/4;height:3px;background:var(--r-line);position:relative}
.r-bar i{position:absolute;left:0;top:0;bottom:0;width:var(--w);background:var(--c);animation:r-bar .9s cubic-bezier(.2,.7,.2,1) both}
@keyframes r-bar{from{width:0}}

.st-key-resultado>div>[data-testid="stElementContainer"],.st-key-resultado>div>[data-testid="stVerticalBlock"]{animation:r-in .35s ease-out both}
.st-key-resultado>div>:nth-child(2){animation-delay:.06s}.st-key-resultado>div>:nth-child(3){animation-delay:.12s}
.st-key-resultado>div>:nth-child(4){animation-delay:.18s}.st-key-resultado>div>:nth-child(5){animation-delay:.24s}
.st-key-resultado>div>:nth-child(n+6){animation-delay:.3s}
@keyframes r-in{from{opacity:0;transform:translateY(6px)}}
.st-key-resultado .js-plotly-plot .scatterlayer .js-line{stroke-dasharray:4000;stroke-dashoffset:4000;animation:r-draw 1.2s .15s ease-out forwards}
@keyframes r-draw{to{stroke-dashoffset:0}}
.st-key-resultado .js-plotly-plot .barlayer .point path{transform-box:fill-box;transform-origin:50% 100%;animation:r-grow .8s cubic-bezier(.2,.7,.2,1) both}
@keyframes r-grow{from{transform:scaleY(0)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
"""


def aplicar_tema() -> None:
    """Injeta o CSS do app. Chamar uma vez por pagina, logo apos set_page_config."""
    st.html(_CSS)


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
body{background:transparent;color:#e6e9ee;font:400 15px/1.5 'IBM Plex Sans',system-ui,sans-serif;display:flex;gap:18px;align-items:center;padding:6px 2px}
.ring{position:relative;width:128px;height:128px;flex:none}
.ring svg{display:block;transform:rotate(-90deg)}
.n{position:absolute;inset:0;display:grid;place-content:center;text-align:center;font:600 26px 'IBM Plex Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums}
.n small{display:block;font:600 10px 'IBM Plex Mono',ui-monospace,monospace;color:#8b95a5;text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px}
h2{font:600 11px 'IBM Plex Mono',ui-monospace,monospace;text-transform:uppercase;letter-spacing:.08em;color:#8b95a5;margin-bottom:6px}
p{font-size:14px;color:#e6e9ee}
</style></head><body>
<div class="ring"><svg width="128" height="128" viewBox="0 0 128 128"><circle cx="64" cy="64" r="56" fill="none" stroke="#252c38" stroke-width="6"/>
<circle id="arc" cx="64" cy="64" r="56" fill="none" stroke="__COR__" stroke-width="6" stroke-dasharray="351.86" stroke-dashoffset="351.86"/></svg>
<div class="n" style="font-size:__TAM__px"><span><small>__ROTULO__</small><span id="v">__FINAL__</span></span></div></div>
<div><h2>__TITULO__</h2><p>__DESCRICAO__</p></div>
<script>
const ALVO=__ALVO__,FINAL=__FINAL_JS__,ANIMA=__ANIMA__;
const arc=document.getElementById('arc'),v=document.getElementById('v'),C=351.86;
const quieto=matchMedia('(prefers-reduced-motion: reduce)').matches||!ANIMA;
function pos(x){arc.style.strokeDashoffset=C*(1-x/100)}
if(quieto){pos(ALVO);v.textContent=FINAL}
else{v.textContent='0,0%';arc.style.transition='stroke-dashoffset 1.1s cubic-bezier(.2,.7,.2,1)';
 requestAnimationFrame(()=>requestAnimationFrame(()=>pos(ALVO)));
 const t0=performance.now();(function tick(t){const k=Math.min(1,(t-t0)/1100),e=1-Math.pow(1-k,3);
  v.textContent=k<1?(ALVO*e).toFixed(1).replace('.',',')+'%':FINAL;if(k<1)requestAnimationFrame(tick)})(t0)}
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
    rotulo = (m.group(1) or "acima de ").strip() if m else ""
    final = f"{m.group(2)},{m.group(3)}%" if m else texto  # o prefixo vai no rotulo pequeno
    corpo = (
        _ANEL.replace("__COR__", escape(cor))
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


# --------------------------------------------------------------- GRAFICOS


def estilo_grafico(fig: go.Figure, altura: int = 320) -> go.Figure:
    """Aplica o visual do app (fundo transparente, linhas finas, fonte Plex) a um grafico Plotly."""
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color="#8b95a5", size=12),
        title=dict(font=dict(family="IBM Plex Mono, monospace", size=13, color="#e6e9ee"), x=0, xanchor="left"),
        hoverlabel=dict(bgcolor="#131820", bordercolor="#323b4a", font=dict(family="IBM Plex Mono, monospace", color="#e6e9ee")),
        legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
    )
    eixo = dict(gridcolor="#252c38", zerolinecolor="#323b4a", linecolor="#323b4a", tickfont=dict(family="IBM Plex Mono, monospace", size=11))
    fig.update_xaxes(**eixo)
    fig.update_yaxes(**eixo)
    return fig
