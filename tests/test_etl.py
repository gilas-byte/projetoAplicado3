"""Testes do ETL com microdados sinteticos de resultado conhecido.

Rodam sem os microdados do INEP:
  ./.venv/bin/python -m unittest discover tests
"""

from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import estatistica  # noqa: E402
import etl  # noqa: E402
from colunas import CONTRATO, tipo  # noqa: E402

ANO = 2022


def linha_base() -> dict:
    """Participante elegivel com valores validos em todas as colunas do RAW."""
    valores = {}
    for c in CONTRATO:
        valores[c] = {"texto": "A", "real": "500.0", "inteiro": "1"}[tipo(c)]
    valores.update(
        NU_ANO=str(ANO), NU_INSCRICAO="210000000001", IN_TREINEIRO="0",
        TP_SEXO="F", SG_UF_PROVA="RJ", NO_MUNICIPIO_PROVA="São Gonçalo",
        TP_ANO_CONCLUIU="3", Q006="C",
    )
    return valores


def escrever_csv(caminho: Path, linhas: list[dict]) -> None:
    colunas = list(CONTRATO)
    texto = [";".join(colunas)] + [";".join(l[c] for c in colunas) for l in linhas]
    caminho.write_text("\n".join(texto) + "\n", encoding="latin-1")


class TestTrusted(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.csv = self.tmp / "microdados.csv"
        linhas = []
        for ajuste in [
            {},  # elegivel
            {"IN_TREINEIRO": "1"},
            {"TP_PRESENCA_MT": "2", "NU_NOTA_MT": ""},  # eliminado
            {"TP_PRESENCA_CN": "0", "NU_NOTA_CN": ""},  # faltou
            {"TP_ANO_CONCLUIU": "16", "Q006": "Q"},  # 2022 - 2006 = antes de 2007
            {"TP_ANO_CONCLUIU": "0", "Q006": "", "SG_UF_ESC": ""},
        ]:
            linhas.append({**linha_base(), **ajuste})
        escrever_csv(self.csv, linhas)
        self.con = duckdb.connect()

    def tearDown(self):
        self.con.close()
        import shutil

        shutil.rmtree(self.tmp)

    def ler(self, sql: str):
        fonte = f"read_parquet('{self.tmp}/trusted/*/*.parquet', hive_partitioning=true)"
        return self.con.execute(sql.replace("{fonte}", fonte)).fetchall()

    def test_colunas_do_contrato(self):
        etl.gerar_trusted(self.con, self.csv, ANO, self.tmp / "trusted")
        nomes = [r[0] for r in self.ler("DESCRIBE SELECT * FROM {fonte}")]
        self.assertNotIn("NU_INSCRICAO", nomes)
        self.assertNotIn("inscricao", " ".join(nomes))
        for c in ["ano", "nota_mt", "renda_familiar", "renda_sm", "elegivel", "ano_conclusao"]:
            self.assertIn(c, nomes)
        self.assertEqual(self.ler("SELECT DISTINCT ano FROM {fonte}"), [(ANO,)])
        self.assertEqual(self.ler("SELECT DISTINCT municipio_prova FROM {fonte}"), [("São Gonçalo",)])

    def test_regras(self):
        etl.gerar_trusted(self.con, self.csv, ANO, self.tmp / "trusted")
        linhas = self.ler(
            "SELECT elegivel, ano_conclusao, conclusao_antes_2007, renda_sm, uf_escola FROM {fonte}"
        )
        self.assertEqual(
            linhas,
            [
                (True, 2019, False, 1.0, "A"),
                (False, 2019, False, 1.0, "A"),
                (False, 2019, False, 1.0, "A"),
                (False, 2019, False, 1.0, "A"),
                (True, None, True, 20.0, "A"),
                (True, None, False, None, None),
            ],
        )

    def test_funil_fecha_com_o_total(self):
        particao = etl.gerar_trusted(self.con, self.csv, ANO, self.tmp / "trusted")
        f = etl.funil(self.con, particao)
        self.assertEqual(
            f,
            {"inscritos": 6, "treineiros": 1, "eliminados": 1, "faltou_alguma_area": 1, "elegiveis": 3},
        )

    def test_ano_errado_falha_sem_deixar_residuo(self):
        with self.assertRaises(duckdb.Error):
            etl.gerar_trusted(self.con, self.csv, ANO - 1, self.tmp / "trusted")
        self.assertEqual(list((self.tmp / "trusted").rglob("*")), [])


class TestFaixas(unittest.TestCase):
    def setUp(self):
        rng = random.Random(42)
        notas = [round(rng.gauss(520, 110), 1) for _ in range(20_000)]
        self.notas = [min(max(n, 0.0), 1000.0) for n in notas]
        contagem: dict[float, int] = {}
        for n in self.notas:
            contagem[n] = contagem.get(n, 0) + 1
        self.contagens = sorted(contagem.items())

    def exato(self, nota: float) -> float:
        abaixo = sum(n < nota for n in self.notas)
        igual = sum(n == nota for n in self.notas)
        return (abaixo + igual / 2) / len(self.notas) * 100

    def test_toda_faixa_respeita_o_piso(self):
        f = estatistica.faixas(self.contagens, piso=100)
        self.assertTrue(all(n >= 100 for *_, n in f))
        self.assertEqual(sum(n for *_, n in f), len(self.notas))
        # Faixas contiguas e sem sobreposicao.
        self.assertTrue(all(a[1] < b[0] for a, b in zip(f, f[1:])))

    def test_total_abaixo_do_piso_nao_publica(self):
        self.assertEqual(estatistica.faixas([(500.0, 40), (600.0, 59)], piso=100), [])

    def test_sobra_final_entra_na_ultima_faixa(self):
        f = estatistica.faixas([(1.0, 100), (2.0, 60), (3.0, 30)], piso=100)
        self.assertEqual(f, [(1.0, 3.0, 190)])

    def test_piso_um_e_exato(self):
        f = estatistica.faixas(self.contagens, piso=1)
        for nota in [0.0, 312.4, 520.0, self.contagens[500][0], 999.9]:
            self.assertAlmostEqual(estatistica.percentil_faixas(f, nota), self.exato(nota), places=9)

    def test_erro_limitado_ao_peso_da_faixa(self):
        f = estatistica.faixas(self.contagens, piso=100)
        limite = max(n for *_, n in f) / len(self.notas) * 100
        for nota in [f[0][0], 250.0, 433.3, 520.0, 610.7, 790.0, f[-1][1]]:
            self.assertLessEqual(abs(estatistica.percentil_faixas(f, nota) - self.exato(nota)), limite)


if __name__ == "__main__":
    unittest.main()
