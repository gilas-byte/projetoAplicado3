"""Radar ENEM: tema e pecas visuais compartilhadas pelas paginas do app.

So apresentacao: nada aqui calcula percentil nem le dados. As paginas passam o
texto que a logica ja devolveu (`texto_percentil`) e este modulo desenha.

Privacidade (docs/privacidade.md, R6): nada e gravado, nada vai para a URL e
nenhum recurso externo e carregado (as fontes ficam em app/static/fonts).
A barra de posicao so aparece quando o percentil NAO esta em limite de
exibicao (DL-04, item 8); perto das pontas o app mostra so o texto.
"""

from __future__ import annotations

from html import escape

import streamlit as st

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
