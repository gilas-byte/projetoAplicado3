"""Monta o relatório final da AV6 em Word (.docx) no modelo UniSENAI da AV4.

Lê as fontes em Markdown desta pasta (00_*.md a 99_*.md, em ordem) e gera
docs/av6/AV6_Relatorio_Final_RadarENEM_EquipeA.docx, reaproveitando do .docx da AV4
o cabeçalho, o rodapé, os estilos, as fontes incorporadas e a capa.

Uso (na raiz do repositório):
    python docs/av6/relatorio/montar_docx.py              # gera o .docx
    python docs/av6/relatorio/montar_docx.py --paginas p.json
        # usa os números de página medidos numa renderização (sumário)

Marcação aceita nas fontes:
    #C Título | subtítulo         capítulo numerado (faixa "CAPÍTULO N – TÍTULO")
    #U Título | subtítulo         faixa sem número (Referências, Apêndices)
    ## Título                     seção numerada (N.M) dentro do capítulo
    ##U Título                    seção sem número (elementos pré-textuais)
    ### Título                    subtítulo numerado (N.M.K)
    ####  Título                  subtítulo sem número
    - texto                       item de lista com travessão
    Quadro: título                legenda de quadro (a tabela Markdown vem logo abaixo)
    Larguras: 20,30,50            larguras das colunas do próximo quadro, em %
    Fonte: texto                  linha de fonte de quadro ou figura
    Figura: arquivo | cm | título figura em linha própria da caixa da seção
    ```  ...  ```                 bloco de terminal ou código
    !! texto                      caixa de destaque (link público)
    \\quebra                       quebra de página
    Inline: **negrito**, `código`, *itálico*, <https://...>, {{PREENCHER: ...}}
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from lxml import etree

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
MODELO = RAIZ / "docs/av4/AV4_Relatorio_Consolidado_RadarENEM_EquipeA.docx"
SAIDA = RAIZ / "docs/av6/AV6_Relatorio_Final_RadarENEM_EquipeA.docx"
FIGURAS = AQUI / "figuras"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {
    "w": W_NS,
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}
W = "{%s}" % W_NS
DECL = " ".join(f'xmlns:{k}="{v}"' for k, v in NS.items())

LARGURA_CAIXA = 9071      # dxa, largura das caixas (16 cm)
LARGURA_INTERNA = 8771    # dxa, tabelas aninhadas
CM_EMU = 360000
QUEBRA = '<w:p><w:pPr><w:pageBreakBefore/><w:spacing w:after="0" w:line="120" w:lineRule="exact"/></w:pPr></w:p>'
ARQ_ADIAMENTOS = AQUI / "adiamentos.json"
ADIAMENTOS: dict[str, int] = {}
ALTURA_MAX_CM = 12.5


# ----------------------------------------------------------------------------- texto
def t(texto: str) -> str:
    return f'<w:t xml:space="preserve">{escape(texto)}</w:t>'


def run(texto: str, *, b=False, i=False, sz=None, mono=False, cor=None, realce=False,
        estilo=None, u=False) -> str:
    props = []
    if estilo:
        props.append(f'<w:rStyle w:val="{estilo}"/>')
    if mono:
        props.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
    if b:
        props.append("<w:b/>")
    if i:
        props.append("<w:i/>")
    if cor:
        props.append(f'<w:color w:val="{cor}"/>')
    if sz:
        props.append(f'<w:sz w:val="{sz}"/>')
    if realce:
        props.append('<w:highlight w:val="yellow"/>')
    if u:
        props.append('<w:u w:val="single"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f"<w:r>{rpr}{t(texto)}</w:r>"


class Doc:
    def __init__(self):
        self.links: dict[str, str] = {}
        self.imagens: list[tuple[str, Path]] = []
        self.bm = 100
        self.draw_id = 100
        self.toc = []        # (nivel, texto, bookmark)
        self.figuras = []    # (texto, bookmark)
        self.quadros = []
        self.cap = 0
        self.sec = 0
        self.sub = 0
        self.numerado = False
        self.n_fig = 0
        self.n_qua = 0
        self.arquivos_fig: list[str] = []

    # --- inline
    def inline(self, texto: str, *, sz=None, b=False, mono_sz=None) -> str:
        """Converte a marcação inline em runs."""
        partes = []
        padrao = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\{\{.+?\}\}|<https?://[^>]+>|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))")
        pos = 0
        for m in padrao.finditer(texto):
            if m.start() > pos:
                partes.append(run(texto[pos:m.start()], sz=sz, b=b))
            tok = m.group(0)
            if tok.startswith("**"):
                partes.append(self.inline(tok[2:-2], sz=sz, b=True, mono_sz=mono_sz))
            elif tok.startswith("`"):
                partes.append(run(tok[1:-1], mono=True, sz=mono_sz or (sz - 2 if sz else 19), b=b))
            elif tok.startswith("{{"):
                partes.append(run(tok[2:-2], sz=sz, b=True, realce=True))
            elif tok.startswith("<http"):
                partes.append(self.hyperlink(tok[1:-1], sz=sz, b=b))
            else:
                partes.append(run(tok[1:-1], sz=sz, b=b, i=True))
            pos = m.end()
        if pos < len(texto):
            partes.append(run(texto[pos:], sz=sz, b=b))
        return "".join(partes)

    def hyperlink(self, url: str, *, sz=None, b=False) -> str:
        rid = self.links.setdefault(url, f"rIdL{len(self.links) + 1}")
        return f'<w:hyperlink r:id="{rid}" w:history="1">{run(url, sz=sz, b=b, estilo="Hyperlink")}</w:hyperlink>'

    def bookmark(self, nome=None):
        self.bm += 1
        nome = nome or f"_Toc{900000000 + self.bm}"
        return nome, f'<w:bookmarkStart w:id="{self.bm}" w:name="{nome}"/>', f'<w:bookmarkEnd w:id="{self.bm}"/>'

    # --- blocos dentro das caixas
    def par(self, texto: str, esquerda=False) -> str:
        jc = "left" if esquerda else "both"
        return ('<w:p><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/>'
                f'<w:jc w:val="{jc}"/></w:pPr>{self.inline(texto)}</w:p>')

    def item(self, texto: str) -> str:
        return ('<w:p><w:pPr><w:spacing w:after="60" w:line="276" w:lineRule="auto"/>'
                '<w:ind w:left="510" w:hanging="283"/><w:jc w:val="both"/></w:pPr>'
                f'{run("–" + chr(160))}{self.inline(texto)}</w:p>')

    def subtitulo(self, texto: str, numerar=True) -> str:
        if numerar and self.numerado:
            self.sub += 1
            texto = f"{self.cap}.{self.sec}.{self.sub} {texto}"
        return ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="120" w:line="276" '
                f'w:lineRule="auto"/></w:pPr>{run(texto, b=True)}</w:p>')

    def legenda(self, tipo: str, titulo: str) -> str:
        if tipo == "Figura":
            self.n_fig += 1
            n = self.n_fig
        else:
            self.n_qua += 1
            n = self.n_qua
        nome, ini, fim = self.bookmark()
        (self.figuras if tipo == "Figura" else self.quadros).append((f"{tipo} {n} – {titulo}", nome))
        seq = (f'<w:r><w:rPr><w:b/><w:sz w:val="19"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
               f'<w:r><w:rPr><w:b/><w:sz w:val="19"/></w:rPr><w:instrText xml:space="preserve"> SEQ {tipo} \\* ARABIC </w:instrText></w:r>'
               f'<w:r><w:rPr><w:b/><w:sz w:val="19"/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>'
               f'{run(str(n), b=True, sz=19)}'
               f'<w:r><w:rPr><w:b/><w:sz w:val="19"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>')
        return ('<w:p><w:pPr><w:keepNext/><w:spacing w:before="80" w:after="40" w:line="276" w:lineRule="auto"/></w:pPr>'
                f'{ini}{run(tipo + " ", b=True, sz=19)}{seq}{self.inline(" – " + titulo, sz=19)}{fim}</w:p>')

    def fonte(self, texto: str) -> str:
        return ('<w:p><w:pPr><w:spacing w:before="40" w:after="160" w:line="276" w:lineRule="auto"/></w:pPr>'
                f'{self.inline("Fonte: " + texto, sz=17, mono_sz=15)}</w:p>')

    def tabela(self, linhas: list[list[str]], larguras: list[float] | None) -> str:
        ncol = len(linhas[0])
        if not larguras:
            pesos = []
            for c in range(ncol):
                maior = max(len(re.sub(r"[`*]", "", l[c])) if c < len(l) else 0 for l in linhas)
                pesos.append(min(max(maior, 6), 60))
            larguras = pesos
        total = sum(larguras)
        ws = [int(LARGURA_INTERNA * w / total) for w in larguras]
        ws[-1] += LARGURA_INTERNA - sum(ws)
        borda = "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
                        for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
        out = [f'<w:tbl><w:tblPr><w:tblW w:w="{LARGURA_INTERNA}" w:type="dxa"/><w:tblBorders>{borda}</w:tblBorders>'
               '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar>'
               '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>',
               "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in ws) + "</w:tblGrid>"]
        for k, linha in enumerate(linhas):
            cab = k == 0
            trpr = "<w:trPr><w:tblHeader/></w:trPr>" if cab else "<w:trPr><w:cantSplit/></w:trPr>"
            cels = []
            for c in range(ncol):
                txt = linha[c] if c < len(linha) else ""
                shd = '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>' if cab else ""
                cels.append(f'<w:tc><w:tcPr><w:tcW w:w="{ws[c]}" w:type="dxa"/>{shd}</w:tcPr>'
                            f'<w:p><w:pPr><w:spacing w:after="20"/></w:pPr>{self.inline(txt, sz=18, b=cab, mono_sz=16)}</w:p></w:tc>')
            out.append(f"<w:tr>{trpr}{''.join(cels)}</w:tr>")
        out.append("</w:tbl>")
        return "".join(out)

    def codigo(self, linhas: list[str]) -> str:
        borda = "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
                        for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
        pars = "".join(
            f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>{run(l or " ", mono=True, sz=16)}</w:p>'
            for l in linhas)
        return (f'<w:tbl><w:tblPr><w:tblW w:w="{LARGURA_INTERNA}" w:type="dxa"/><w:tblBorders>{borda}</w:tblBorders>'
                '<w:tblLayout w:type="fixed"/></w:tblPr>'
                f'<w:tblGrid><w:gridCol w:w="{LARGURA_INTERNA}"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:w="{LARGURA_INTERNA}" w:type="dxa"/>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="F7F7F7"/></w:tcPr>{pars}</w:tc></w:tr></w:tbl>'
                '<w:p><w:pPr><w:spacing w:after="80"/></w:pPr></w:p>')

    def destaque(self, texto: str) -> str:
        borda = "".join(f'<w:{b} w:val="single" w:sz="12" w:space="0" w:color="1D4ED8"/>'
                        for b in ("top", "left", "bottom", "right"))
        linhas = texto.split(" || ")
        pars = "".join(
            '<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:jc w:val="center"/></w:pPr>'
            f'{self.inline(l, sz=22 if k else 20, b=True)}</w:p>' for k, l in enumerate(linhas))
        return (f'<w:tbl><w:tblPr><w:tblW w:w="{LARGURA_INTERNA}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{borda}</w:tblBorders>'
                '<w:tblLayout w:type="fixed"/></w:tblPr>'
                f'<w:tblGrid><w:gridCol w:w="{LARGURA_INTERNA}"/></w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr><w:tc><w:tcPr><w:tcW w:w="{LARGURA_INTERNA}" w:type="dxa"/>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="EAF2FF"/></w:tcPr>{pars}</w:tc></w:tr></w:tbl>'
                '<w:p><w:pPr><w:spacing w:after="80"/></w:pPr></w:p>')

    def imagem(self, arquivo: str, largura_cm: float) -> str:
        caminho = FIGURAS / arquivo
        with open(caminho, "rb") as f:
            cab = f.read(24)
        larg, alt = struct.unpack(">II", cab[16:24])
        cx = int(largura_cm * CM_EMU)
        cy = int(cx * alt / larg)
        if cy > ALTURA_MAX_CM * CM_EMU:
            cy = int(ALTURA_MAX_CM * CM_EMU)
            cx = int(cy * larg / alt)
        return ('<w:p><w:pPr><w:keepNext/><w:spacing w:after="60"/><w:jc w:val="center"/></w:pPr>'
                + self.desenho(arquivo, cx, cy) + '</w:p>')

    def desenho(self, arquivo: str, cx: int, cy: int) -> str:
        """Run com a imagem inline, no tamanho dado em EMU."""
        caminho = FIGURAS / arquivo
        self.imagens.append((f"rIdImg{len(self.imagens) + 1}", caminho))
        rid = self.imagens[-1][0]
        self.draw_id += 1
        d = self.draw_id
        return ('<w:r><w:rPr><w:noProof/></w:rPr><w:drawing>'
                f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
                f'<wp:docPr id="{d}" name="Figura {d}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
                f'<pic:nvPicPr><pic:cNvPr id="{d}" name="{escape(arquivo)}"/><pic:cNvPicPr/></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
                '<a:ln w="6350"><a:solidFill><a:srgbClr val="BFBFBF"/></a:solidFill></a:ln></pic:spPr>'
                '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')

    # --- caixas
    def caixa(self, titulo: str, linhas_conteudo: list[tuple[str, str]], nivel_toc=2, toc=True) -> str:
        borda = "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
                        for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
        nome, ini, fim = self.bookmark()
        if toc:
            self.toc.append((nivel_toc, titulo, nome))
        estilo = '<w:pStyle w:val="Ttulo2"/>' if toc else ""
        out = [f'<w:tbl><w:tblPr><w:tblW w:w="{LARGURA_CAIXA}" w:type="dxa"/><w:tblBorders>{borda}</w:tblBorders>'
               '<w:tblLayout w:type="fixed"/><w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
               f'<w:tblGrid><w:gridCol w:w="{LARGURA_CAIXA}"/></w:tblGrid>'
               f'<w:tr><w:trPr><w:tblHeader/></w:trPr><w:tc><w:tcPr><w:tcW w:w="{LARGURA_CAIXA}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/></w:tcPr>'
               f'<w:p><w:pPr>{estilo}<w:keepNext/><w:spacing w:before="40" w:after="40"/></w:pPr>{ini}{run(titulo.upper(), b=True, sz=20)}{fim}</w:p></w:tc></w:tr>']
        n = len(linhas_conteudo)
        for k, (tipo, xml) in enumerate(linhas_conteudo):
            bordas = []
            if k > 0:
                bordas.append('<w:top w:val="nil"/>')
            if k < n - 1:
                bordas.append('<w:bottom w:val="nil"/>')
            tcb = f"<w:tcBorders>{''.join(bordas)}</w:tcBorders>" if bordas else ""
            trpr = "<w:trPr><w:cantSplit/></w:trPr>" if tipo == "figura" else ""
            if not xml.rstrip().endswith("</w:p>"):
                xml += '<w:p><w:pPr><w:spacing w:after="0" w:line="80" w:lineRule="exact"/></w:pPr></w:p>'
            out.append(f'<w:tr>{trpr}<w:tc><w:tcPr><w:tcW w:w="{LARGURA_CAIXA}" w:type="dxa"/>{tcb}'
                       '<w:tcMar><w:left w:w="140" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar></w:tcPr>'
                       f'{xml}</w:tc></w:tr>')
        out.append("</w:tbl><w:p/>")
        return "".join(out)

    def faixa(self, titulo: str, subtitulo: str) -> str:
        borda = "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
                        for b in ("top", "left", "bottom", "right"))
        nome, ini, fim = self.bookmark()
        self.toc.append((1, titulo, nome))
        sub = (f'<w:p><w:pPr><w:spacing w:after="80"/><w:jc w:val="center"/></w:pPr>{self.inline(subtitulo)}</w:p>'
               if subtitulo else "")
        return (f'<w:tbl><w:tblPr><w:tblW w:w="{LARGURA_CAIXA}" w:type="dxa"/><w:tblBorders>{borda}</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr>'
                f'<w:tblGrid><w:gridCol w:w="{LARGURA_CAIXA}"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:w="{LARGURA_CAIXA}" w:type="dxa"/>'
                '<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="Ttulo1"/><w:keepNext/><w:spacing w:before="80"/><w:jc w:val="center"/></w:pPr>{ini}{run(titulo.upper(), b=True, sz=24)}{fim}</w:p>'
                f'{sub}</w:tc></w:tr></w:tbl><w:p/>')


# ----------------------------------------------------------------------------- leitura das fontes
def ler_tabela(linhas: list[str], i: int):
    tab = []
    while i < len(linhas) and linhas[i].strip().startswith("|"):
        # "\|" é uma barra dentro da célula (ex.: valor absoluto), não separador de coluna
        conteudo = linhas[i].strip().removeprefix("|").removesuffix("|")
        cel = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", conteudo)]
        if not all(re.fullmatch(r":?-{3,}:?", c) for c in cel):
            tab.append(cel)
        i += 1
    return tab, i


def converter(doc: Doc, texto: str) -> list[str]:
    """Converte uma fonte Markdown em blocos do corpo."""
    corpo: list[str] = []
    linhas = texto.splitlines()
    secao_titulo = None
    secao_toc = True
    linhas_caixa: list[tuple[str, str]] = []
    pendente: list = []   # figura adiada: [xml, blocos que ainda devem vir antes dela]

    def soltar_figura():
        if pendente:
            linhas_caixa.append(("figura", pendente[0]))
            pendente.clear()

    class Blocos(list):
        """Cada bloco vira uma linha própria da caixa: a quebra de página cai entre blocos."""
        def append(self, xml):
            linhas_caixa.append(("texto", xml))
            # uma figura adiada só entra depois de um bloco completo, nunca entre um
            # subtítulo ou legenda de quadro (que têm keepNext) e o que vem depois deles
            if pendente and not xml.startswith("<w:p><w:pPr><w:keepNext/>"):
                pendente[1] -= 1
                if pendente[1] <= 0:
                    soltar_figura()

    atual = Blocos()
    larguras = None
    buffer: list[str] = []

    def fechar_paragrafo():
        if buffer:
            esquerda = bool(secao_titulo and secao_titulo.startswith("Referências"))
            atual.append(doc.par(" ".join(s.strip() for s in buffer), esquerda))
            buffer.clear()

    def fechar_linha(tipo="texto"):
        fechar_paragrafo()
        if atual:
            linhas_caixa.append((tipo, "".join(atual)))
            atual.clear()

    def fechar_secao():
        nonlocal secao_titulo
        fechar_linha()
        soltar_figura()
        if secao_titulo is not None:
            corpo.append(doc.caixa(secao_titulo, linhas_caixa[:] or [("texto", "<w:p/>")], toc=secao_toc))
        linhas_caixa.clear()
        secao_titulo = None

    i = 0
    while i < len(linhas):
        l = linhas[i]
        s = l.strip()
        if s.startswith("%%"):            # comentário da fonte
            i += 1
            continue
        if s.startswith("#C ") or s.startswith("#U "):
            fechar_secao()
            titulo, _, sub = s[3:].partition("|")
            if s.startswith("#C "):
                doc.cap += 1
                doc.numerado = True
                titulo = f"CAPÍTULO {doc.cap} – {titulo.strip()}"
            else:
                doc.numerado = False
                titulo = titulo.strip()
            doc.sec = 0
            corpo.append(doc.faixa(titulo, sub.strip()))
        elif s == "\\quebra":
            fechar_secao()
            if corpo and corpo[-1].endswith("<w:p/>"):
                corpo[-1] = corpo[-1][: -len("<w:p/>")]
            corpo.append(QUEBRA)
        elif s.startswith("##U "):
            fechar_secao()
            secao_titulo = s[4:].strip()
            secao_toc = False
        elif s.startswith("## "):
            fechar_secao()
            titulo = s[3:].strip()
            if doc.numerado:
                doc.sec += 1
                doc.sub = 0
                titulo = f"{doc.cap}.{doc.sec} {titulo}"
            secao_titulo = titulo
            secao_toc = True
        elif s.startswith("### "):
            fechar_paragrafo()
            atual.append(doc.subtitulo(s[4:].strip()))
        elif s.startswith("#### "):
            fechar_paragrafo()
            atual.append(doc.subtitulo(s[5:].strip(), numerar=False))
        elif s.startswith("- "):
            fechar_paragrafo()
            atual.append(doc.item(s[2:].strip()))
        elif s.startswith("Larguras:"):
            larguras = [float(x) for x in s.split(":", 1)[1].split(",")]
        elif s.startswith("Quadro:"):
            fechar_paragrafo()
            atual.append(doc.legenda("Quadro", s.split(":", 1)[1].strip()))
            i += 1
            while i < len(linhas) and not linhas[i].strip():
                i += 1
            if i < len(linhas) and linhas[i].strip().startswith("Larguras:"):
                larguras = [float(x) for x in linhas[i].split(":", 1)[1].split(",")]
                i += 1
            tab, i = ler_tabela(linhas, i)
            atual.append(doc.tabela(tab, larguras))
            larguras = None
            continue
        elif s.startswith("|"):
            fechar_paragrafo()
            tab, i = ler_tabela(linhas, i)
            atual.append(doc.tabela(tab, larguras))
            atual.append('<w:p><w:pPr><w:spacing w:after="80"/></w:pPr></w:p>')
            larguras = None
            continue
        elif s.startswith("Fonte:"):
            fechar_paragrafo()
            atual.append(doc.fonte(s.split(":", 1)[1].strip()))
        elif s.startswith("Figura:"):
            fechar_linha()
            soltar_figura()
            arquivo, cm, titulo = [x.strip() for x in s.split(":", 1)[1].split("|", 2)]
            doc.arquivos_fig.append(arquivo)
            fig = doc.legenda("Figura", titulo) + doc.imagem(arquivo, float(cm.replace(",", ".")))
            i += 1
            while i < len(linhas) and not linhas[i].strip():
                i += 1
            if i < len(linhas) and linhas[i].strip().startswith("Fonte:"):
                fig += doc.fonte(linhas[i].strip().split(":", 1)[1].strip())
                i += 1
            soltar_figura()
            adiar = ADIAMENTOS.get(arquivo, 0)
            if adiar > 0:
                pendente.extend([fig, adiar])
            else:
                linhas_caixa.append(("figura", fig))
            continue
        elif s.startswith("```"):
            fechar_paragrafo()
            bloco = []
            i += 1
            while i < len(linhas) and not linhas[i].strip().startswith("```"):
                bloco.append(linhas[i].rstrip())
                i += 1
            atual.append(doc.codigo(bloco))
        elif s.startswith("!! "):
            fechar_paragrafo()
            atual.append(doc.destaque(s[3:].strip()))
        elif not s:
            fechar_paragrafo()
        else:
            buffer.append(s)
        i += 1
    fechar_secao()
    return corpo


# ----------------------------------------------------------------------------- sumário e listas
def entrada(texto, nome, pagina, estilo=None, nivel_rpr=True):
    tabs = '<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8780"/></w:tabs>'
    ppr = (f'<w:pStyle w:val="{estilo}"/>{tabs}' if estilo else f'{tabs}<w:spacing w:after="60"/>')
    rp = '<w:rPr><w:noProof/><w:webHidden/></w:rPr>'
    sz = "" if estilo else '<w:sz w:val="20"/>'
    return (f'<w:p><w:pPr>{ppr}</w:pPr><w:hyperlink w:anchor="{nome}" w:history="1">'
            f'<w:r><w:rPr><w:noProof/>{sz}</w:rPr>{t(texto)}</w:r>'
            f'<w:r>{rp}<w:tab/></w:r>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r>{rp}<w:instrText xml:space="preserve"> PAGEREF {nome} \\h </w:instrText></w:r>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="separate"/></w:r>'
            f'<w:r><w:rPr><w:noProof/><w:webHidden/>{sz}</w:rPr>{t(str(pagina))}</w:r>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="end"/></w:r></w:hyperlink></w:p>')


def campo(instr: str, entradas: list[str]) -> str:
    """Envolve as entradas num campo TOC (o Word atualiza; o LibreOffice mostra o resultado)."""
    if not entradas:
        return "<w:p/>"
    ini = (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> {escape(instr)} </w:instrText></w:r>'
           '<w:r><w:fldChar w:fldCharType="separate"/></w:r>')
    primeira = entradas[0].replace("</w:pPr>", "</w:pPr>" + ini, 1)
    ultima_fim = '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    corpo = [primeira] + entradas[1:]
    corpo[-1] = corpo[-1][: -len("</w:p>")] + ultima_fim
    return "".join(corpo)


def caixa_lista(doc: Doc, titulo: str, xml: str) -> str:
    return doc.caixa(titulo, [("texto", xml)], toc=False)


# ----------------------------------------------------------------------------- montagem
def montar(paginas: dict[str, int]):
    doc = Doc()
    fontes = sorted(AQUI.glob("[0-9][0-9]_*.md"))
    capa_md = AQUI / "00_capa.json"
    capa = json.loads(capa_md.read_text(encoding="utf-8"))
    pre, corpo = [], []
    for f in fontes:
        blocos = converter(doc, f.read_text(encoding="utf-8"))
        if f.name < "10_":
            pre.extend(blocos)
        else:
            corpo.extend(blocos)

    pg = lambda nome: paginas.get(nome, 0)
    sumario = [entrada(txt, nome, pg(nome), "Sumrio1" if nivel == 1 else "Sumrio2") for nivel, txt, nome in doc.toc]
    sumario_xml = (QUEBRA
                   + caixa_lista(doc, "Sumário", campo("TOC \\o \"1-2\" \\h \\z \\u", sumario)))

    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(MODELO) as z:
        z.extractall(tmp)
    arvore = etree.parse(str(tmp / "word/document.xml"))
    body = arvore.getroot().find(W + "body")
    filhos = list(body)
    capa_els = filhos[:13]            # parágrafos da capa (até a quebra de página)
    sect = filhos[-1]
    ident = copy.deepcopy(filhos[13])  # quadro de identificação
    for el in filhos:
        body.remove(el)

    # capa: textos trocados no lugar, mantendo a formatação da AV4
    trocas = capa["capa"]
    for el in capa_els:
        txt = "".join(el.itertext())
        if txt in trocas:
            rs = el.findall(".//" + W + "r")
            for r in rs[1:]:
                r.getparent().remove(r)
            for pe in el.findall(".//" + W + "proofErr"):
                pe.getparent().remove(pe)
            rs[0].find(W + "t").text = trocas[txt]
        body.append(el)
    # logotipos do Radar ENEM e da KiraSapiens na capa, entre o subtítulo e o título do produto
    textos = ["".join(el.itertext()) for el in body]
    def paragrafo_vazio(antes):
        return etree.fromstring(f'<w:p {DECL}><w:pPr><w:spacing w:before="{antes}"/><w:jc w:val="center"/></w:pPr></w:p>')
    def espaco_antes(el, valor):
        sp = el.find(f"{W}pPr/{W}spacing")
        if sp is not None:
            sp.set(W + "before", str(valor))
    if capa.get("logos"):
        k_titulo = textos.index(trocas["RELATÓRIO TÉCNICO – AV4"])
        espaco_antes(body[k_titulo], 200)
        body.insert(k_titulo, paragrafo_vazio(200))
        k_sub = k_titulo + 2
        logos = "".join(doc.desenho(arq, cx, cy) for arq, cx, cy in capa["logos"])
        body.insert(k_sub + 1, etree.fromstring(
            f'<w:p {DECL}><w:pPr><w:spacing w:before="120"/><w:jc w:val="center"/></w:pPr>{logos}</w:p>'))
        k_desc = k_sub + 2
        body.insert(k_desc + 1, paragrafo_vazio(360))
        espaco_antes(body[k_desc + 2], 360)   # "Equipe:"

    # destaque do link na capa, antes da cidade
    destaque_capa = etree.fromstring(
        f'<w:body {DECL}><w:p><w:pPr><w:spacing w:before="360" w:after="0"/><w:jc w:val="center"/></w:pPr>'
        f'{run("Aplicação publicada em nuvem (link público):", b=True, sz=20)}</w:p>'
        f'<w:p><w:pPr><w:spacing w:before="40"/><w:jc w:val="center"/></w:pPr>{doc.hyperlink(capa["link"], sz=22, b=True)}</w:p></w:body>')
    pos_cidade = [k for k, el in enumerate(body) if "".join(el.itertext()) == trocas.get("FLORIANÓPOLIS - SC", "FLORIANÓPOLIS - SC")]
    k = pos_cidade[0] if pos_cidade else len(body)
    for el in reversed(list(destaque_capa)):
        body.insert(k, el)
    # reduz o espaço antes da cidade, que agora vem depois do link
    cidade = body[k + 2]
    sp = cidade.find(f"{W}pPr/{W}spacing")
    if sp is not None:
        sp.set(W + "before", "900")

    # quadro de identificação: troca as linhas de dados
    interno = ident.find(".//" + W + "tbl")
    modelo_linha = interno.findall(W + "tr")[1]
    for tr in interno.findall(W + "tr")[1:]:
        interno.remove(tr)
    for item, valor in capa["identificacao"]:
        tr = copy.deepcopy(modelo_linha)
        tcs = tr.findall(W + "tc")
        for tc, texto in ((tcs[0], item), (tcs[1], valor)):
            for p in tc.findall(W + "p"):
                tc.remove(p)
            bold = item in ("Aplicação publicada", "Repositório")
            p = etree.fromstring(f'<w:p {DECL}><w:pPr><w:spacing w:after="20"/></w:pPr>{doc.inline(texto, sz=18, b=bold and tc is tcs[1])}</w:p>')
            tc.append(p)
        interno.append(tr)
    body.append(ident)

    quebra = QUEBRA
    tira = lambda x: x[: -len("<w:p/>")] if x.endswith("<w:p/>") else x
    pre[-1] = tira(pre[-1])
    resto = "".join([quebra, *pre, tira(sumario_xml), quebra, *corpo])
    # pré-textuais começam em página nova depois da identificação
    frag = etree.fromstring(f"<w:body {DECL}>{resto}</w:body>")
    for el in frag:
        body.append(el)
    body.append(sect)

    # relações: hiperlinks e imagens novas; remove as figuras da AV4
    rels_path = tmp / "word/_rels/document.xml.rels"
    rels = etree.parse(str(rels_path))
    raiz = rels.getroot()
    rns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    for rel in list(raiz):
        if rel.get("Type").endswith("/image"):
            raiz.remove(rel)
    usados = {"image20.png", "image21.png"}
    for img in (tmp / "word/media").iterdir():
        if img.name not in usados:
            img.unlink()
    for rid, caminho in doc.imagens:
        destino = f"media/av6_{rid[5:]:0>2}_{caminho.name}"
        shutil.copy(caminho, tmp / "word" / destino)
        etree.SubElement(raiz, rns + "Relationship", Id=rid,
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image", Target=destino)
    for url, rid in doc.links.items():
        etree.SubElement(raiz, rns + "Relationship", Id=rid,
                         Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                         Target=url, TargetMode="External")
    rels.write(str(rels_path), xml_declaration=True, encoding="UTF-8", standalone=True)
    arvore.write(str(tmp / "word/document.xml"), xml_declaration=True, encoding="UTF-8", standalone=True)

    # rodapé: no modelo, a célula "Página N de M" (1276 dxa) quebra em duas linhas a partir da
    # página 10; passa 300 dxa da primeira coluna (código do formulário, com folga) para ela
    for rodape in sorted((tmp / "word").glob("footer*.xml")):
        t_rod = rodape.read_text(encoding="utf-8")
        t_rod = t_rod.replace('<w:gridCol w:w="2836"/>', '<w:gridCol w:w="2536"/>')
        t_rod = t_rod.replace('<w:gridCol w:w="1276"/>', '<w:gridCol w:w="1576"/>')
        t_rod = t_rod.replace('<w:tcW w:w="2836" w:type="dxa"/>', '<w:tcW w:w="2536" w:type="dxa"/>')
        t_rod = t_rod.replace('<w:tcW w:w="1276" w:type="dxa"/>', '<w:tcW w:w="1576" w:type="dxa"/>')
        rodape.write_text(t_rod, encoding="utf-8")

    # tipo de conteúdo para as imagens JPEG da capa
    ct = tmp / "[Content_Types].xml"
    t_ct = ct.read_text(encoding="utf-8")
    if 'Extension="jpeg"' not in t_ct:
        t_ct = t_ct.replace("<Default Extension=", '<Default Extension="jpeg" ContentType="image/jpeg"/><Default Extension=', 1)
        ct.write_text(t_ct, encoding="utf-8")

    # propriedades do documento
    core = tmp / "docProps/core.xml"
    c = core.read_text(encoding="utf-8")
    c = re.sub(r"<dc:title>.*?</dc:title>", "<dc:title>AV6 – Relatório Final do Produto de Dados – Radar ENEM</dc:title>", c)
    if "<dc:title>" not in c:
        c = c.replace("</cp:coreProperties>", "<dc:title>AV6 – Relatório Final do Produto de Dados – Radar ENEM</dc:title></cp:coreProperties>")
    core.write_text(c, encoding="utf-8")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    if SAIDA.exists():
        SAIDA.unlink()
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as z:
        for arq in sorted(tmp.rglob("*")):
            if arq.is_file():
                z.write(arq, arq.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)
    # mapa de marcadores para medir as páginas
    mapa = {nome: txt for _, txt, nome in doc.toc}
    mapa.update({nome: txt for txt, nome in doc.figuras + doc.quadros})
    mapa["_figuras"] = doc.arquivos_fig
    (AQUI / "marcadores.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{SAIDA.relative_to(RAIZ)}: {doc.cap} capítulos, {len(doc.figuras)} figuras, {len(doc.quadros)} quadros")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paginas", type=Path)
    a = ap.parse_args()
    if ARQ_ADIAMENTOS.exists():
        ADIAMENTOS.update(json.loads(ARQ_ADIAMENTOS.read_text(encoding="utf-8")))
    montar(json.loads(a.paginas.read_text()) if a.paginas else {})
