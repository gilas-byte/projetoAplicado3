"""Testes do motor v1: medidas conferidas contra registros sintéticos."""
from __future__ import annotations

import math
import random
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from estatistica import construir_acumulada, prob_superioridade, quantil, resumo, z_score


def expandir(contagens: list[tuple[float, int]]) -> list[float]:
    return [nota for nota, n in contagens for _ in range(n)]


class TestResumo(unittest.TestCase):
    def test_valores_a_mao(self):
        medidas = resumo(construir_acumulada([(400, 1), (500, 2), (600, 1)]))
        self.assertEqual(medidas['N'], 4)
        self.assertEqual(medidas['media'], 500.0)
        self.assertEqual(medidas['variancia'], 5000.0)
        self.assertAlmostEqual(medidas['desvio'], math.sqrt(5000))
        self.assertEqual(medidas['mediana'], 500.0)

    def test_confere_com_registros_sinteticos(self):
        gerador = random.Random(2026)
        contagens = [(300 + i * 0.1, gerador.randint(1, 40)) for i in range(0, 5000, 7)]
        registros = expandir(contagens)
        medidas = resumo(construir_acumulada(contagens))
        self.assertEqual(medidas['N'], len(registros))
        self.assertAlmostEqual(medidas['media'], statistics.fmean(registros), places=9)
        self.assertAlmostEqual(medidas['variancia'], statistics.pvariance(registros), places=6)
        self.assertEqual(medidas['mediana'], statistics.median_low(registros))

    def test_nota_unica_tem_variancia_exatamente_zero(self):
        medidas = resumo(construir_acumulada([(612.3, 7)]))
        self.assertEqual(medidas['media'], 612.3)
        self.assertEqual(medidas['variancia'], 0.0)
        self.assertEqual(medidas['desvio'], 0.0)
        self.assertEqual(medidas['mediana'], 612.3)


class TestQuantil(unittest.TestCase):
    def setUp(self):
        self.dist = construir_acumulada([(400, 1), (500, 2), (600, 1)])

    def test_menor_nota_que_alcanca_p(self):
        self.assertEqual(quantil(self.dist, 0.25), 400.0)
        self.assertEqual(quantil(self.dist, 0.26), 500.0)
        self.assertEqual(quantil(self.dist, 0.75), 500.0)
        self.assertEqual(quantil(self.dist, 0.76), 600.0)

    def test_extremos(self):
        self.assertEqual(quantil(self.dist, 0), 400.0)
        self.assertEqual(quantil(self.dist, 1), 600.0)

    def test_mediana_com_n_par_e_a_nota_inferior(self):
        self.assertEqual(quantil(construir_acumulada([(1, 1), (2, 1), (3, 1), (4, 1)]), 0.5), 2.0)

    def test_p_decimal_nao_sofre_arredondamento(self):
        dist = construir_acumulada([(float(i), 1) for i in range(1, 101)])
        self.assertGreater(0.07 * 100, 7)
        self.assertEqual(quantil(dist, 0.07), 7.0)

    def test_p_invalido(self):
        for p in [-0.1, 1.1, math.nan, math.inf]:
            with self.subTest(p=p), self.assertRaises(ValueError):
                quantil(self.dist, p)


class TestZScore(unittest.TestCase):
    def setUp(self):
        self.dist = construir_acumulada([(400, 1), (500, 2), (600, 1)])

    def test_dentro_e_fora_da_distribuicao(self):
        desvio = math.sqrt(5000)
        self.assertEqual(z_score(self.dist, 500), 0.0)
        self.assertAlmostEqual(z_score(self.dist, 600), 100 / desvio)
        self.assertAlmostEqual(z_score(self.dist, 1000), 500 / desvio)
        self.assertAlmostEqual(z_score(self.dist, 0), -500 / desvio)

    def test_desvio_zero(self):
        with self.assertRaises(ValueError):
            z_score(construir_acumulada([(612.3, 7)]), 612.3)

    def test_nota_nao_finita(self):
        for nota in [math.nan, math.inf, -math.inf]:
            with self.subTest(nota=nota), self.assertRaises(ValueError):
                z_score(self.dist, nota)


class TestProbSuperioridade(unittest.TestCase):
    def test_valores_a_mao(self):
        a = construir_acumulada([(500, 1), (700, 1)])
        b = construir_acumulada([(500, 1), (600, 1)])
        # Pares (A, B): 500x500 empate, 500x600 perde, 700x500 ganha, 700x600 ganha.
        self.assertEqual(prob_superioridade(a, b), 2.5 / 4)

    def test_extremos(self):
        baixo = construir_acumulada([(100, 3), (200, 2)])
        alto = construir_acumulada([(300, 4), (400, 1)])
        self.assertEqual(prob_superioridade(alto, baixo), 1.0)
        self.assertEqual(prob_superioridade(baixo, alto), 0.0)
        self.assertEqual(prob_superioridade(baixo, baixo), 0.5)

    def test_confere_com_todos_os_pares(self):
        gerador = random.Random(2026)
        cont_a = [(float(nota), gerador.randint(1, 5)) for nota in range(400, 700, 10)]
        cont_b = [(float(nota), gerador.randint(1, 5)) for nota in range(350, 760, 20)]
        reg_a, reg_b = expandir(cont_a), expandir(cont_b)
        vitorias = sum((x > y) + 0.5 * (x == y) for x in reg_a for y in reg_b)
        a, b = construir_acumulada(cont_a), construir_acumulada(cont_b)
        self.assertAlmostEqual(prob_superioridade(a, b), vitorias / (len(reg_a) * len(reg_b)))
        self.assertAlmostEqual(prob_superioridade(a, b) + prob_superioridade(b, a), 1.0)

    def test_grupos_do_tamanho_do_enem_nao_perdem_precisao(self):
        a = construir_acumulada([(500, 2_000_001), (600, 1_999_999)])
        b = construir_acumulada([(500, 1_000_000), (600, 3_000_000)])
        esperado = (1_999_999 * 1_000_000 + 0.5 * (2_000_001 * 1_000_000 + 1_999_999 * 3_000_000)) / 16e12
        self.assertAlmostEqual(prob_superioridade(a, b), esperado, places=12)


class TestDistribuicaoVazia(unittest.TestCase):
    def test_todas_as_funcoes_recusam(self):
        cheia = construir_acumulada([(500, 1)])
        chamadas = [
            lambda: resumo([]),
            lambda: quantil([], 0.5),
            lambda: z_score([], 500),
            lambda: prob_superioridade([], cheia),
            lambda: prob_superioridade(cheia, []),
        ]
        for chamada in chamadas:
            with self.subTest(), self.assertRaises(ValueError):
                chamada()


if __name__ == '__main__':
    unittest.main()
