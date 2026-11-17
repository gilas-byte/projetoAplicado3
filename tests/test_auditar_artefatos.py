"""Testes da barreira de publicação (scripts/auditar_artefatos.py) com artefatos sintéticos."""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import auditar_artefatos as aud  # noqa: E402
from estatistica import construir_acumulada, faixas  # noqa: E402

CONTAGENS = [(float(n), 300) for n in range(400, 600)]  # 60.000 pessoas por edição e área


def linhas_cdf(grupos: dict[str, list[tuple[float, int]]], recorte: str):
    for grupo, contagens in grupos.items():
        cdf = construir_acumulada(contagens)
        total = cdf[-1][1] + cdf[-1][2]
        for nota, n, abaixo in cdf:
            yield (2022, "mt", recorte, grupo, nota, n, abaixo, total)


def gravar(con, pasta: Path, nome: str, colunas: str, linhas) -> None:
    con.execute(f"CREATE OR REPLACE TABLE t ({colunas})")
    con.executemany(f"INSERT INTO t VALUES ({', '.join('?' * len(colunas.split(',')))})", list(linhas))
    con.execute(f"COPY t TO '{(pasta / nome).as_posix()}' (FORMAT parquet)")


CDF_COLS = "ano BIGINT, area VARCHAR, recorte VARCHAR, grupo VARCHAR, nota DOUBLE, n BIGINT, abaixo BIGINT, total BIGINT"


class TestAuditoria(unittest.TestCase):
    def montar(self, pasta: Path, territorial=None, capital_br=CONTAGENS):
        con = duckdb.connect()
        gravar(con, pasta, "dist_notas.parquet", "ano BIGINT, area VARCHAR, nota_min DOUBLE, nota_max DOUBLE, n BIGINT",
               ((2022, "mt", a, b, n) for a, b, n in faixas(CONTAGENS)))
        cdf = construir_acumulada(CONTAGENS)
        gravar(con, pasta, "dist_exata.parquet", "ano BIGINT, area VARCHAR, nota DOUBLE, n BIGINT, abaixo BIGINT, total BIGINT",
               ((2022, "mt", nota, n, abaixo, 60000) for nota, n, abaixo in cdf))
        metade = [(nota, n // 2) for nota, n in CONTAGENS]
        gravar(con, pasta, "dist_equidade.parquet", CDF_COLS, linhas_cdf({"R1": metade, "R2": metade}, "renda"))
        gravar(con, pasta, "dist_territorial.parquet", CDF_COLS,
               territorial if territorial is not None else linhas_cdf({"BR": CONTAGENS, "UF-SC": metade}, "territorial"))
        gravar(con, pasta, "dist_capital.parquet", CDF_COLS, linhas_cdf({"BR": capital_br, "NV-A": metade}, "capital"))
        con.close()

    def rodar(self, pasta: Path) -> tuple[int, str]:
        saida = io.StringIO()
        with mock.patch.object(aud, "ANALYTICS", pasta), \
                mock.patch.object(aud, "MANIFESTO", pasta / "_manifesto_publicacao.json"), \
                mock.patch.object(aud, "REFERENCIA", pasta / "sem_referencia.sha256"), \
                mock.patch.object(sys, "argv", ["auditar_artefatos.py"]), redirect_stdout(saida):
            codigo = aud.main()
        return codigo, saida.getvalue()

    def test_artefatos_validos_passam_e_gravam_manifesto(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            self.montar(pasta)
            codigo, saida = self.rodar(pasta)
            self.assertEqual(codigo, 0, saida)
            self.assertTrue((pasta / "_manifesto_publicacao.json").exists())

    def test_grupo_abaixo_do_piso_bloqueia(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            pequeno = [(500.0, 40), (510.0, 30)]  # 70 pessoas
            self.montar(pasta, territorial=linhas_cdf({"BR": CONTAGENS, "UF-RR": pequeno}, "territorial"))
            codigo, saida = self.rodar(pasta)
            self.assertEqual(codigo, 1)
            self.assertIn("menos de 100 participantes", saida)
            self.assertFalse((pasta / "_manifesto_publicacao.json").exists())

    def test_chave_repetida_e_cdf_incoerente_bloqueiam(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            linhas = list(linhas_cdf({"BR": CONTAGENS}, "territorial"))
            linhas.append(linhas[10])  # mesma nota duas vezes no grupo
            self.montar(pasta, territorial=linhas)
            codigo, saida = self.rodar(pasta)
            self.assertEqual(codigo, 1)
            self.assertIn("chave(s) do grao repetidas", saida)
            self.assertIn("incoerentes", saida)

    def test_brasil_diferente_entre_artefatos_bloqueia(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            self.montar(pasta, capital_br=CONTAGENS[:-1])
            codigo, saida = self.rodar(pasta)
            self.assertEqual(codigo, 1)
            self.assertIn("Brasil de dist_capital difere", saida)

    def test_artefato_ausente_bloqueia(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            self.montar(pasta)
            (pasta / "dist_capital.parquet").unlink()
            codigo, saida = self.rodar(pasta)
            self.assertEqual(codigo, 1)
            self.assertIn("dist_capital.parquet: ausente", saida)


if __name__ == "__main__":
    unittest.main()
