"""Testes das medidas da AV6: caixa protegida, KS, PSI e percentil da normal.

Cada medida é conferida contra um cálculo independente sobre os registros
sintéticos expandidos (uma nota por pessoa), sem usar a CDF.
"""
from __future__ import annotations

import math
import random
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from estatistica import (  # noqa: E402
    caixa_protegida,
    construir_acumulada,
    contagem_ate,
    ks_distancia,
    percentil_normal,
    psi,
)


def expandir(contagens: list[tuple[float, int]]) -> list[float]:
    return [nota for nota, n in contagens for _ in range(n)]


def quantil_bruto(registros: list[float], p: float) -> float:
    """Menor nota x com #(nota <= x) >= p · N, direto nos registros ordenados."""
    ordenados = sorted(registros)
    alvo = Fraction(str(p)) * len(ordenados)
    indice = max(math.ceil(alvo) - 1, 0)
    return ordenados[indice]


def sintetico(semente: int, deslocamento: float = 0.0) -> list[tuple[float, int]]:
    gerador = random.Random(semente)
    return [(round(300 + deslocamento + i * 0.5, 1), gerador.randint(1, 60)) for i in range(0, 1200, 3)]


class TestContagemAte(unittest.TestCase):
    def test_nota_observada_entre_e_fora(self):
        dist = construir_acumulada([(400, 2), (500, 3), (600, 5)])
        self.assertEqual(contagem_ate(dist, 399), 0)
        self.assertEqual(contagem_ate(dist, 400), 2)
        self.assertEqual(contagem_ate(dist, 450), 2)
        self.assertEqual(contagem_ate(dist, 500), 5)
        self.assertEqual(contagem_ate(dist, 600), 10)
        self.assertEqual(contagem_ate(dist, 1000), 10)


class TestCaixaProtegida(unittest.TestCase):
    def test_confere_com_registros(self):
        contagens = sintetico(7)
        registros = expandir(contagens)
        caixa = caixa_protegida(construir_acumulada(contagens))
        self.assertIsNotNone(caixa)
        self.assertEqual(caixa['N'], len(registros))
        for chave, p in (('bigode_inferior', 0.05), ('q1', 0.25), ('mediana', 0.5),
                         ('q3', 0.75), ('bigode_superior', 0.95)):
            self.assertEqual(caixa[chave], quantil_bruto(registros, p), chave)
        self.assertEqual(caixa['iqr'], caixa['q3'] - caixa['q1'])

    def test_bigodes_deixam_pelo_menos_o_piso_de_fora(self):
        contagens = sintetico(11)
        dist = construir_acumulada(contagens)
        caixa = caixa_protegida(dist, piso=100)
        total = caixa['N']
        # Ninguém fica sozinho na ponta: pelo menos o piso de pessoas tem nota
        # menor ou igual ao bigode inferior, e pelo menos o piso tem nota maior
        # ou igual ao bigode superior.
        ate_inferior = contagem_ate(dist, caixa['bigode_inferior'])
        estritamente_abaixo_do_superior = next(abaixo for nota, _, abaixo in dist
                                               if nota == caixa['bigode_superior'])
        self.assertGreaterEqual(ate_inferior, 100)
        self.assertGreaterEqual(total - estritamente_abaixo_do_superior, 100)
        self.assertLessEqual(caixa['bigode_inferior'], caixa['q1'])
        self.assertGreaterEqual(caixa['bigode_superior'], caixa['q3'])

    def test_grupo_pequeno_nao_tem_caixa(self):
        # 5% de 1.999 = 99,95 < 100: a ponta deixada de fora seria menor que o piso.
        self.assertIsNone(caixa_protegida(construir_acumulada([(500.0, 1999)]), piso=100))
        self.assertIsNotNone(caixa_protegida(construir_acumulada([(500.0, 2000)]), piso=100))


class TestKS(unittest.TestCase):
    def ks_bruto(self, a: list[float], b: list[float]) -> float:
        a, b = sorted(a), sorted(b)
        pontos = sorted(set(a) | set(b))
        import bisect
        return max(abs(bisect.bisect_right(a, x) / len(a) - bisect.bisect_right(b, x) / len(b))
                   for x in pontos)

    def test_confere_com_registros(self):
        ca, cb = sintetico(1), sintetico(2, deslocamento=12.0)
        esperado = self.ks_bruto(expandir(ca), expandir(cb))
        obtido = ks_distancia(construir_acumulada(ca), construir_acumulada(cb))
        self.assertAlmostEqual(obtido, esperado, places=12)

    def test_iguais_dao_zero_e_disjuntas_dao_um(self):
        a = construir_acumulada([(400, 3), (500, 4)])
        self.assertEqual(ks_distancia(a, a), 0.0)
        b = construir_acumulada([(700, 2), (800, 9)])
        self.assertEqual(ks_distancia(a, b), 1.0)

    def test_simetrica(self):
        a, b = construir_acumulada(sintetico(3)), construir_acumulada(sintetico(4, 5.0))
        self.assertEqual(ks_distancia(a, b), ks_distancia(b, a))


class TestPSI(unittest.TestCase):
    def psi_bruto(self, ref: list[float], atual: list[float], classes: int = 10) -> float:
        cortes = sorted({quantil_bruto(ref, k / classes) for k in range(1, classes)})

        def proporcoes(registros):
            caixas = [0] * (len(cortes) + 1)
            for x in registros:
                caixas[sum(1 for c in cortes if x > c)] += 1
            return [c / len(registros) for c in caixas]

        total = 0.0
        for r, a in zip(proporcoes(ref), proporcoes(atual)):
            r, a = max(r, 1e-6), max(a, 1e-6)
            total += (a - r) * math.log(a / r)
        return total

    def test_confere_com_registros(self):
        ca, cb = sintetico(5), sintetico(6, deslocamento=20.0)
        esperado = self.psi_bruto(expandir(ca), expandir(cb))
        obtido = psi(construir_acumulada(ca), construir_acumulada(cb))
        self.assertAlmostEqual(obtido, esperado, places=9)

    def test_mesma_distribuicao_da_zero(self):
        a = construir_acumulada(sintetico(8))
        self.assertAlmostEqual(psi(a, a), 0.0, places=12)

    def test_classes_invalidas(self):
        a = construir_acumulada(sintetico(9))
        with self.assertRaises(ValueError):
            psi(a, a, classes=1)


class TestPercentilNormal(unittest.TestCase):
    def test_valores_conhecidos(self):
        self.assertAlmostEqual(percentil_normal(0.0), 50.0, places=12)
        self.assertAlmostEqual(percentil_normal(1.959963984540054), 97.5, places=9)
        self.assertAlmostEqual(percentil_normal(-1.0), 15.865525393145707, places=9)

    def test_rejeita_infinito(self):
        with self.assertRaises(ValueError):
            percentil_normal(float('inf'))



try:
    import analises_av6
except ImportError:  # duckdb ausente
    analises_av6 = None


@unittest.skipIf(analises_av6 is None, "duckdb nao instalado")
class TestAmostragemMesmaPopulacao(unittest.TestCase):
    """A simples (CDF nacional) e a estratificada (soma das UFs) sorteiam da mesma populacao."""

    NACIONAL = construir_acumulada([(400.0, 60), (600.0, 40)])

    def rodar(self, ufs):
        with mock.patch.object(analises_av6, "carregar_ufs", return_value=ufs):
            return analises_av6.analise_amostragem({(2022, "mt"): self.NACIONAL}, 2022, "mt",
                                                    fracao=0.5, repeticoes=2)

    def test_recusa_quando_a_soma_das_ufs_difere_do_total_nacional(self):
        ufs = {"UF-AA": construir_acumulada([(400.0, 30), (600.0, 20)]),
               "UF-BB": construir_acumulada([(400.0, 29), (600.0, 20)])}  # falta 1 participante
        with self.assertRaisesRegex(ValueError, "difere do total nacional"):
            self.rodar(ufs)

    def test_aceita_quando_os_totais_batem(self):
        ufs = {"UF-AA": construir_acumulada([(400.0, 30), (600.0, 20)]),
               "UF-BB": construir_acumulada([(400.0, 30), (600.0, 20)])}
        self.assertIsInstance(self.rodar(ufs), dict)


if __name__ == "__main__":
    unittest.main()
