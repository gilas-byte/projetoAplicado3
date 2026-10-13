"""Testes independentes dos microdados e de DuckDB para percentis exatos."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from estatistica import construir_acumulada, percentil_exato_acumulado


class TestDistribuicaoExata(unittest.TestCase):
    def test_empates_e_mediana(self):
        dist = construir_acumulada([(400, 1), (500, 2), (600, 1)])
        self.assertEqual(percentil_exato_acumulado(dist, 500), 50.0)
        self.assertEqual(percentil_exato_acumulado(dist, 550), 75.0)
        self.assertEqual(percentil_exato_acumulado(dist, 100), 0.0)
        self.assertEqual(percentil_exato_acumulado(dist, 700), 100.0)

    def test_sem_interpolacao_entre_notas(self):
        dist = construir_acumulada([(100, 2), (900, 2)])
        self.assertEqual(percentil_exato_acumulado(dist, 899.9), 50.0)
        self.assertEqual(percentil_exato_acumulado(dist, 900), 75.0)

    def test_singular(self):
        self.assertEqual(percentil_exato_acumulado(construir_acumulada([(600, 1)]), 600), 50.0)

    def test_frequencias_invalidas(self):
        for freq in [[(500, 0)], [(500, -1)], [(600, 1), (500, 1)], [(500, 1), (500, 1)], [(math.nan, 5)]]:
            with self.subTest(freq=freq), self.assertRaises(ValueError):
                construir_acumulada(freq)
        with self.assertRaises(ValueError):
            percentil_exato_acumulado([], 500)
        with self.assertRaises(ValueError):
            percentil_exato_acumulado(construir_acumulada([(500, 1)]), math.inf)


if __name__ == '__main__':
    unittest.main()
