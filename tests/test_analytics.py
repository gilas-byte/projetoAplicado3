"""Teste de ponta a ponta da etapa ANALYTICS com microdados sinteticos.

Gera um CSV sintetico (com empates de nota), passa por RAW -> TRUSTED ->
ANALYTICS usando as funcoes reais do ETL e confere os artefatos contra um
calculo independente em Python puro. Roda sem os microdados do INEP:

  ./.venv/bin/python -m unittest tests/test_analytics.py -v
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import estatistica  # noqa: E402
import etl  # noqa: E402
from test_etl import ANO, escrever_csv, linha_base  # noqa: E402

AREAS_COM_NOTA = {"cn": "NU_NOTA_CN", "ch": "NU_NOTA_CH", "lc": "NU_NOTA_LC", "mt": "NU_NOTA_MT", "redacao": "NU_NOTA_REDACAO"}
N_ELEGIVEIS = 1500


def gerar_linhas() -> tuple[list[dict], dict[str, list[float]]]:
    """Participantes elegiveis com notas em passos de 0,1 (muitos empates)."""
    rng = random.Random(2022)
    linhas, notas = [], {a: [] for a in AREAS_COM_NOTA}
    for i in range(N_ELEGIVEIS):
        linha = linha_base()
        linha["NU_INSCRICAO"] = str(210000000000 + i)
        for area, coluna in AREAS_COM_NOTA.items():
            nota = round(min(max(rng.gauss(520, 90), 0.0), 1000.0), 1)
            if area == "redacao":
                nota = float(round(nota / 40) * 40)  # redacao em multiplos de 40: empates pesados
            linha[coluna] = f"{nota}"
            notas[area].append(nota)
        linhas.append(linha)
    # Nao elegiveis: nao podem entrar em nenhuma distribuicao.
    for ajuste in ({"IN_TREINEIRO": "1"}, {"TP_PRESENCA_MT": "2", "NU_NOTA_MT": ""}, {"TP_PRESENCA_CN": "0", "NU_NOTA_CN": ""}):
        linhas.append({**linha_base(), **ajuste, "NU_NOTA_CH": "999.9", "NU_NOTA_LC": "999.9", "NU_NOTA_REDACAO": "1000.0"})
    return linhas, notas


def percentil_bruto(notas: list[float], nota: float) -> float:
    """Definicao do percentil por posto medio, sem nenhuma estrutura agregada."""
    abaixo = sum(n < nota for n in notas)
    iguais = sum(n == nota for n in notas)
    return (abaixo + iguais / 2) / len(notas) * 100


class TestEtapaAnalytics(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        csv = self.tmp / "microdados.csv"
        linhas, self.notas = gerar_linhas()
        escrever_csv(csv, linhas)

        self.trusted = self.tmp / "data" / "trusted" / "enem"
        self.analytics = self.tmp / "data" / "analytics"
        con = duckdb.connect()
        etl.gerar_trusted(con, csv, ANO, self.trusted)
        con.close()

        alvos = {
            "RAIZ": self.tmp,
            "TRUSTED": self.trusted,
            "ANALYTICS": self.analytics,
            "DIST_NOTAS": self.analytics / "dist_notas.parquet",
            "DIST_EXATA": self.analytics / "dist_exata.parquet",
            "MANIFESTO_ANALYTICS": self.analytics / "_manifesto_analytics.json",
        }
        for nome, valor in alvos.items():
            patcher = mock.patch.object(etl, nome, valor)
            patcher.start()
            self.addCleanup(patcher.stop)

    def ler(self, sql: str):
        con = duckdb.connect()
        try:
            return con.execute(sql).fetchall()
        finally:
            con.close()

    def test_gera_os_tres_artefatos_e_nenhum_temporario(self):
        etl.etapa_analytics()
        nomes = sorted(p.name for p in self.analytics.iterdir())
        self.assertEqual(nomes, ["_manifesto_analytics.json", "dist_exata.parquet", "dist_notas.parquet"])

    def test_cdf_exata_confere_com_calculo_independente(self):
        etl.etapa_analytics()
        exata = self.analytics / "dist_exata.parquet"
        for area, notas in self.notas.items():
            linhas = self.ler(
                f"SELECT nota, n, abaixo, total FROM read_parquet('{exata}') "
                f"WHERE ano = {ANO} AND area = '{area}' ORDER BY nota"
            )
            self.assertEqual({t for *_, t in linhas}, {N_ELEGIVEIS}, f"{area}: total deve ser so os elegiveis")
            cdf = [(nota, n, abaixo) for nota, n, abaixo, _ in linhas]
            # Nota observada, nota entre duas observadas, abaixo do minimo e acima do maximo.
            consultas = {linhas[0][0], linhas[-1][0], linhas[len(linhas) // 2][0], -5.0, 1500.0}
            consultas |= {linhas[i][0] + 0.03 for i in range(0, len(linhas) - 1, max(1, len(linhas) // 15))}
            for nota in consultas:
                self.assertAlmostEqual(
                    estatistica.percentil_exato_acumulado(cdf, nota), percentil_bruto(notas, nota), places=9,
                    msg=f"{area} nota {nota}",
                )

    def test_nao_elegiveis_nao_entram_na_distribuicao(self):
        etl.etapa_analytics()
        exata = self.analytics / "dist_exata.parquet"
        maior = self.ler(f"SELECT max(nota) FROM read_parquet('{exata}') WHERE area = 'redacao'")[0][0]
        self.assertLess(maior, 1000.0)  # as notas 1000.0 sinteticas eram de nao elegiveis

    def test_histograma_conserva_contagens_e_respeita_o_piso(self):
        etl.etapa_analytics()
        hist = self.analytics / "dist_notas.parquet"
        for area in AREAS_COM_NOTA:
            soma, menor = self.ler(
                f"SELECT sum(n), min(n) FROM read_parquet('{hist}') WHERE ano = {ANO} AND area = '{area}'"
            )[0]
            self.assertEqual(soma, N_ELEGIVEIS)
            self.assertGreaterEqual(menor, 100)

    def test_manifesto_bate_com_os_arquivos(self):
        etl.etapa_analytics()
        manifesto = json.loads((self.analytics / "_manifesto_analytics.json").read_text(encoding="utf-8"))
        for nome, info in manifesto["arquivos"].items():
            arquivo = self.analytics / nome
            self.assertEqual(info["bytes"], arquivo.stat().st_size)
            self.assertEqual(info["sha256"], hashlib.sha256(arquivo.read_bytes()).hexdigest())
        self.assertEqual(manifesto["anos"], [ANO])
        self.assertEqual(manifesto["distribuicoes"][f"{ANO}/cn"]["participantes"], N_ELEGIVEIS)
        self.assertLess(manifesto["verificacao_cdf_exata"]["maior_divergencia_pontos_percentuais"], 1e-9)

    def test_execucao_repetida_e_idempotente(self):
        def conteudo() -> dict[str, list]:
            return {
                nome: self.ler(f"SELECT * FROM read_parquet('{self.analytics / nome}') ORDER BY ALL")
                for nome in ("dist_exata.parquet", "dist_notas.parquet")
            }

        etl.etapa_analytics()
        primeira = conteudo()
        etl.etapa_analytics()
        segunda = conteudo()
        # Mesmo conteudo logico apos reexecutar, sem duplicar linhas.
        self.assertEqual(primeira, segunda)
        self.assertTrue(all(len(linhas) > 0 for linhas in primeira.values()))

    def test_validacao_que_falha_nao_publica_nem_deixa_residuo(self):
        with mock.patch.object(etl, "percentil_exato_acumulado", return_value=-1.0):
            with self.assertRaises(AssertionError):
                etl.etapa_analytics()
        restos = list(self.analytics.iterdir()) if self.analytics.exists() else []
        self.assertEqual(restos, [], "falha na validacao nao pode deixar artefato publicado nem temporario")

    def test_sem_grupo_minimo_aborta_sem_publicar(self):
        pequeno = self.tmp / "pequeno.csv"
        escrever_csv(pequeno, [linha_base() for _ in range(10)])
        shutil.rmtree(self.trusted)
        con = duckdb.connect()
        etl.gerar_trusted(con, pequeno, ANO, self.trusted)
        con.close()
        with self.assertRaises(ValueError):
            etl.etapa_analytics()
        restos = list(self.analytics.iterdir()) if self.analytics.exists() else []
        self.assertEqual(restos, [])


if __name__ == "__main__":
    unittest.main()
