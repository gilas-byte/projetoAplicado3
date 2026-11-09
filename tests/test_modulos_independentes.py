"""Módulos autorais não importam uns aos outros.

Observação de autoria da AV4 no Plano de Trabalho e review da DL-05, item 13:
a lógica de cada módulo (Equidade, Recorte territorial, Capital escolar
familiar) fica no próprio arquivo, e o que é comum fica em
`scripts/estatistica.py`. Este teste lê os imports com `ast`, sem executar os
módulos, e falha se um módulo ou uma página passar a depender de outro módulo.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import estatistica  # noqa: E402

AUTORAIS = {"equidade", "territorial", "capital_escolar"}
COMPARTILHADAS = (
    "alcance_do_limite",
    "densidade_protegida",
    "dobro_posicao",
    "exibir_percentil",
    "formatar_percentil",
    "limites_exibicao",
    "texto_da_posicao",
)


def modulos_importados(caminho: Path) -> set[str]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            nomes.add(no.module.split(".")[0])
    return nomes


class TestModulosIndependentes(unittest.TestCase):
    def test_scripts_autorais_nao_importam_outro_modulo(self):
        for nome in sorted(AUTORAIS):
            caminho = RAIZ / "scripts" / f"{nome}.py"
            if not caminho.exists():
                continue
            with self.subTest(modulo=nome):
                self.assertEqual(modulos_importados(caminho) & (AUTORAIS - {nome}), set())

    def test_paginas_importam_no_maximo_um_modulo(self):
        for caminho in sorted((RAIZ / "app" / "pages").glob("*.py")):
            with self.subTest(pagina=caminho.name):
                self.assertLessEqual(len(modulos_importados(caminho) & AUTORAIS), 1)

    def test_compartilhadas_moram_em_estatistica(self):
        for nome in COMPARTILHADAS:
            with self.subTest(funcao=nome):
                self.assertEqual(getattr(estatistica, nome).__module__, "estatistica")


if __name__ == "__main__":
    unittest.main()
