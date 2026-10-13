"""Teste do app com um artefato ANALYTICS sintetico (sem microdados).

  ./.venv/bin/python -m unittest discover tests
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from estatistica import faixas, construir_acumulada  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None


@unittest.skipIf(AppTest is None, "streamlit nao instalado")
class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        arquivo = Path(cls.tmp.name) / "dist_notas.parquet"
        # 1000 participantes por nota inteira de 300 a 799: percentil conhecido.
        linhas = []
        for area in ["cn", "ch", "lc", "mt"]:
            f = faixas([(float(n), 1000) for n in range(300, 800)])
            linhas += [(2022, area, a, b, n) for a, b, n in f]
        con = duckdb.connect()
        con.execute("CREATE TABLE d (ano BIGINT, area VARCHAR, nota_min DOUBLE, nota_max DOUBLE, n BIGINT)")
        con.executemany("INSERT INTO d VALUES (?, ?, ?, ?, ?)", linhas)
        con.execute(f"COPY d TO '{arquivo}' (FORMAT parquet)")
        exatas = []
        for area in ["cn", "ch", "lc", "mt"]:
            exatas += [(2022, area, nota, n, abaixo) for nota, n, abaixo in
                       construir_acumulada([(float(n), 1000) for n in range(300, 800)])]
        con.execute("CREATE TABLE e (ano BIGINT, area VARCHAR, nota DOUBLE, n BIGINT, abaixo BIGINT)")
        con.executemany("INSERT INTO e VALUES (?, ?, ?, ?, ?)", exatas)
        arquivo_exato = Path(cls.tmp.name) / "dist_exata.parquet"
        con.execute(f"COPY e TO '{arquivo_exato}' (FORMAT parquet)")
        con.close()
        os.environ["RADAR_DIST_NOTAS"] = str(arquivo)
        os.environ["RADAR_DIST_EXATA"] = str(arquivo_exato)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("RADAR_DIST_NOTAS", None)
        os.environ.pop("RADAR_DIST_EXATA", None)
        cls.tmp.cleanup()

    def abrir(self) -> AppTest:
        at = AppTest.from_file(str(RAIZ / "app" / "app.py"), default_timeout=30)
        at.run()
        self.assertFalse(at.exception)
        return at

    @staticmethod
    def campo(at: AppTest, rotulo: str):
        return next(c for c in at.number_input if c.label == rotulo)

    def test_percentil_da_nota_informada(self):
        at = self.abrir()
        self.campo(at, "Matemática").set_value(550.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m.label for m in at.metric], ["Matemática"])
        # 250 notas abaixo de 550 e metade do empate: (250 + 0,5) / 500.
        self.assertEqual(at.metric[0].delta, "acima de 50.1% dos participantes")

    def test_area_sem_dados_vira_grupo_insuficiente(self):
        at = self.abrir()
        self.campo(at, "Redação").set_value(600.0)  # nao existe no artefato
        at.button[0].click().run()
        self.assertIn("grupo insuficiente", at.info[0].value)

    def test_sem_nota_pede_ao_menos_uma(self):
        at = self.abrir()
        at.button[0].click().run()
        self.assertIn("ao menos uma nota", at.warning[0].value)

    def test_notas_nao_vao_para_a_url(self):
        at = self.abrir()
        self.campo(at, "Ciências Humanas").set_value(700.0)
        at.button[0].click().run()
        self.assertEqual(dict(at.query_params), {})


if __name__ == "__main__":
    unittest.main()
