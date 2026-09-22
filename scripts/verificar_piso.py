#!/usr/bin/env python3
"""Barreira de LGPD: falha se algum artefato versionado expoe grupo pequeno.

Percorre todo JSON em docs/ e acusa qualquer contagem `n` abaixo de
PISO_GRUPO (ver docs/privacidade.md). Roda sem os microdados, entao serve
para quem clonou o repositorio e para revisar um PR antes do merge.

Uso:
  ./.venv/bin/python scripts/verificar_piso.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from colunas import PISO_GRUPO  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"


def violacoes(no, caminho: str = ""):
    if isinstance(no, dict):
        n = no.get("n")
        if isinstance(n, int) and not isinstance(n, bool) and n < PISO_GRUPO:
            yield caminho, n
        for chave, valor in no.items():
            yield from violacoes(valor, f"{caminho}/{chave}")
    elif isinstance(no, list):
        for i, valor in enumerate(no):
            yield from violacoes(valor, f"{caminho}[{i}]")


def main() -> int:
    achados = []
    for arquivo in sorted(DOCS.rglob("*.json")):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        for caminho, n in violacoes(dados):
            achados.append(f"{arquivo.relative_to(RAIZ)}:{caminho} n={n}")

    if achados:
        print(f"{len(achados)} contagem(ns) abaixo do piso de {PISO_GRUPO}:")
        for linha in achados:
            print(f"  {linha}")
        return 1
    print(f"OK: nenhuma contagem abaixo do piso de {PISO_GRUPO} em docs/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
