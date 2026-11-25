"""Gera o .docx sem buracos grandes e com os números de página do sumário preenchidos.

1. Monta o documento e o converte para PDF com o LibreOffice.
2. Procura páginas que terminam com muito espaço em branco porque a figura seguinte não
   coube; nesses casos, adia a figura para depois do bloco de texto seguinte da mesma
   seção (como faria uma figura flutuante) e monta de novo. Os adiamentos ficam em
   adiamentos.json.
3. Mede em que página aparece cada capítulo e seção e monta de novo com os números.

No Word, o gerar-pdf-av6.ps1 atualiza os números de página antes de exportar o PDF,
porque a paginação do Word pode diferir um pouco da do LibreOffice.

Uso (na raiz do repositório): python docs/av6/relatorio/paginar.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
DOCX = RAIZ / "docs/av6/AV6_Relatorio_Final_RadarENEM_EquipeA.docx"
ADIAMENTOS = AQUI / "adiamentos.json"
LIMITE_VAZIO = 0.18      # fração da área útil da página em branco no fim
MAX_ADIAR = 6


def normal(texto: str) -> str:
    return re.sub(r"[\s­​]+", "", texto).upper()


def renderizar(docx: Path):
    """Devolve o texto e a fração vazia no fim de cada página."""
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(docx, tmp / "r.docx")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "r.docx"], cwd=tmp,
                   check=True, capture_output=True, timeout=600)
    texto = subprocess.run(["pdftotext", "-layout", str(tmp / "r.pdf"), "-"],
                           check=True, capture_output=True, text=True).stdout.split("\f")
    subprocess.run(["pdftoppm", "-r", "30", "-gray", "-png", "r.pdf", "p"], cwd=tmp, check=True)
    vazios = []
    for img in sorted(tmp.glob("p-*.png")):
        im = Image.open(img).convert("L")
        w, h = im.size
        px = im.load()
        topo, base = int(h * 0.14), int(h * 0.905)
        ultimo = topo
        for y in range(topo, base):
            if any(px[x, y] < 200 for x in range(int(w * 0.08), int(w * 0.92), 2)):
                ultimo = y
        vazios.append((base - ultimo) / (base - topo))
    shutil.rmtree(tmp)
    return texto, vazios


def primeira_figura(pagina: str):
    """Número da figura que abre a página, se ela começar por uma figura."""
    linhas = [l.strip() for l in pagina.splitlines() if l.strip()]
    linhas = [l for l in linhas if not re.search(r"Relatório Técnico|Discente|Documento padronizado", l)]
    for l in linhas[:3]:
        m = re.match(r"Figura (\d+) –", l)
        if m:
            return int(m.group(1))
        if not re.match(r"^\d+\.\d+ [A-ZÁÉÍÓÚÂÊÔÃÕÇ]", l):
            return None
    return None


def montar(paginas=None):
    cmd = [sys.executable, str(AQUI / "montar_docx.py")]
    if paginas:
        cmd += ["--paginas", str(paginas)]
    subprocess.run(cmd, check=True)


def main():
    adiar = json.loads(ADIAMENTOS.read_text()) if ADIAMENTOS.exists() else {}
    for rodada in range(12):
        montar()
        texto, vazios = renderizar(DOCX)
        figuras = json.loads((AQUI / "marcadores.json").read_text(encoding="utf-8"))["_figuras"]
        mudou = False
        for i in range(len(vazios) - 1):
            if vazios[i] <= LIMITE_VAZIO:
                continue
            n = primeira_figura(texto[i + 1])
            if n is None:
                continue
            arquivo = figuras[n - 1]
            if adiar.get(arquivo, 0) < MAX_ADIAR:
                adiar[arquivo] = adiar.get(arquivo, 0) + 1
                mudou = True
        ADIAMENTOS.write_text(json.dumps(adiar, indent=1, sort_keys=True), encoding="utf-8")
        buracos = [(i + 1, round(v * 100)) for i, v in enumerate(vazios[:-1]) if v > LIMITE_VAZIO]
        print(f"rodada {rodada + 1}: {len(vazios)} páginas; páginas com mais de 18% em branco: {buracos}")
        if not mudou:
            break

    normais = [normal(p) for p in texto]
    lista = [("......" in p) for p in texto]
    mapa = json.loads((AQUI / "marcadores.json").read_text(encoding="utf-8"))
    mapa.pop("_figuras", None)
    resultado, faltando = {}, []
    for nome, titulo in mapa.items():
        chave = normal(titulo)[:40]
        achou = next((i for i, p in enumerate(normais) if chave in p and not lista[i]), None)
        if achou is None:
            faltando.append(titulo)
            continue
        resultado[nome] = achou + 1
    arq = AQUI / "paginas.json"
    arq.write_text(json.dumps(resultado, indent=1), encoding="utf-8")
    montar(arq)
    print(f"{len(resultado)} entradas paginadas")
    for t in faltando:
        print("sem página:", t)


if __name__ == "__main__":
    main()
