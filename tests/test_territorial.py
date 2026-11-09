"""Testes do módulo Recorte territorial (autor: Vinícius Joacir dos Anjos).

Cobrem as regras da DL-04 (docs/decisoes): tabela de UFs e regiões, códigos
de grupo, validação da entrada, os três cenários e as medidas entre grupos,
casos de erro (UF abaixo do piso, região ausente, UF inválida) e a agregação
de ponta a ponta com microdados sintéticos, conferida contra um cálculo
independente em Python puro.

Rodam sem os microdados do INEP:
  ./.venv/bin/python -m unittest tests/test_territorial.py -v
"""

from __future__ import annotations

import math
import os
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import etl  # noqa: E402
import territorial as tr  # noqa: E402
from colunas import PISO_GRUPO  # noqa: E402
import estatistica as est  # noqa: E402
from estatistica import construir_acumulada  # noqa: E402
from test_etl import ANO, escrever_csv, linha_base  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None

PAGINA = RAIZ / "app" / "pages" / "2_Recorte_territorial.py"


def cdf(*pares: tuple[float, int]):
    return construir_acumulada([(float(nota), n) for nota, n in pares])


def percentil_bruto(notas: list[float], nota: float) -> float:
    return (sum(x < nota for x in notas) + sum(x == nota for x in notas) / 2) / len(notas) * 100


# ================================================================ REGRAS


class TestTerritorio(unittest.TestCase):
    def test_27_ufs_em_5_regioes_sem_repeticao(self):
        ufs = [uf for _, lista in tr.REGIOES.values() for uf in lista]
        self.assertEqual(len(ufs), 27)
        self.assertEqual(len(set(ufs)), 27)
        self.assertEqual(set(ufs), set(tr.NOMES_UF))
        self.assertEqual(len(tr.REGIOES), 5)

    def test_regioes_do_ibge(self):
        self.assertEqual(tr.REGIAO_DA_UF["SC"], "S")
        self.assertEqual(tr.REGIAO_DA_UF["DF"], "CO")
        self.assertEqual(tr.REGIAO_DA_UF["TO"], "N")
        self.assertEqual(tr.REGIAO_DA_UF["SE"], "NE")  # Sergipe, não Sudeste
        self.assertEqual(tr.REGIAO_DA_UF["ES"], "SE")
        self.assertEqual(set(tr.REGIOES["SE"][1]), {"MG", "ES", "RJ", "SP"})

    def test_codigos_de_grupo_sem_ambiguidade(self):
        # "SE" é sigla de Sergipe e do Sudeste; os prefixos separam os dois.
        self.assertNotEqual(tr.grupo_uf("SE"), tr.grupo_regiao("SE"))
        self.assertEqual(len(tr.GRUPOS), len(set(tr.GRUPOS)))
        self.assertEqual(len(tr.GRUPOS), 1 + 5 + 27)
        self.assertEqual(tr.rotulo_grupo(tr.grupo_uf("SE")), "Sergipe")
        self.assertEqual(tr.rotulo_grupo(tr.grupo_regiao("SE")), "Região Sudeste")
        self.assertEqual(tr.rotulo_grupo(tr.BRASIL), "Brasil")

    def test_rotulo_de_grupo_desconhecido(self):
        for grupo in ["UF-XX", "RG-ZZ", "SC", ""]:
            with self.subTest(grupo=grupo), self.assertRaises(ValueError):
                tr.rotulo_grupo(grupo)

    def test_ufs_do_contrato_batem_com_a_tabela(self):
        # O contrato registra 27 UFs nas quatro edições (SG_UF_PROVA).
        from colunas import CONTRATO
        self.assertIn("27 unidades federativas", CONTRATO["SG_UF_PROVA"]["transformacao"])


class TestValidacaoEntrada(unittest.TestCase):
    ANOS = [2021, 2022]

    def validar(self, **campos):
        base = dict(ano=2022, area="mt", nota=650.0, uf="SC", anos_disponiveis=self.ANOS)
        base.update(campos)
        return tr.validar_entrada(**base)

    def test_entrada_valida_normalizada(self):
        e = self.validar(uf=" sc ", nota=650)
        self.assertEqual((e.ano, e.area, e.nota, e.uf, e.regiao), (2022, "mt", 650.0, "SC", "S"))

    def test_erros(self):
        casos = {
            "edicao": dict(ano=2018),
            "edicao_bool": dict(ano=True),
            "area": dict(area="fisica"),
            "nota_vazia": dict(nota=None),
            "nota_texto": dict(nota="650"),
            "nota_nan": dict(nota=float("nan")),
            "nota_infinita": dict(nota=float("inf")),
            "nota_negativa": dict(nota=-0.1),
            "nota_acima": dict(nota=1000.1),
            "duas_casas": dict(nota=650.25),
            "redacao_fora_do_passo": dict(area="redacao", nota=610.0),
            "uf_vazia": dict(uf=""),
            "uf_none": dict(uf=None),
            "uf_inexistente": dict(uf="XX"),
            "uf_por_extenso": dict(uf="Santa Catarina"),
            "regiao_no_lugar_da_uf": dict(uf="NE"),
        }
        for nome, campos in casos.items():
            with self.subTest(nome), self.assertRaises(tr.EntradaInvalida):
                self.validar(**campos)

    def test_sergipe_e_valido(self):
        self.assertEqual(self.validar(uf="SE").regiao, "NE")


# ============================================================ COMPARAÇÃO


class TestComparacao(unittest.TestCase):
    """Valores esperados calculados à mão. Edição 2022, Matemática.

    SC: 100 notas 500, 100 notas 600 (N = 200).
    PR: 100 notas 400, 100 notas 500 (N = 200).
    RS: 150 notas 450 (N = 150).
    Sul = SC + PR + RS (N = 550). BA: 200 notas 400. Brasil = Sul + BA (N = 750).
    """

    def setUp(self):
        sc = [(500, 100), (600, 100)]
        pr = [(400, 100), (500, 100)]
        rs = [(450, 150)]
        ba = [(400, 200)]
        sul = [(400, 100), (450, 150), (500, 200), (600, 100)]
        br = [(400, 300), (450, 150), (500, 200), (600, 100)]
        self.cdfs = {
            (2022, "mt", "UF-SC"): cdf(*sc),
            (2022, "mt", "UF-PR"): cdf(*pr),
            (2022, "mt", "UF-RS"): cdf(*rs),
            (2022, "mt", "UF-BA"): cdf(*ba),
            (2022, "mt", "RG-S"): cdf(*sul),
            (2022, "mt", "RG-NE"): cdf(*ba),
            (2022, "mt", "BR"): cdf(*br),
        }

    def entrada(self, nota=500.0, uf="SC", area="mt"):
        return tr.validar_entrada(2022, area, nota, uf, [2022])

    def test_tres_cenarios(self):
        r = tr.comparar(self.cdfs, self.entrada())
        # UF: (0 + 100/2) / 200 = 25%. Exato no backend; em limite na tela.
        self.assertAlmostEqual(r.uf.percentil, 25.0)
        self.assertEqual((r.uf.texto_percentil, r.uf.em_limite), ("abaixo de 50,0%", True))
        # Sul: (100 + 150 + 200/2) / 550.
        self.assertAlmostEqual(r.regiao.percentil, 350 / 550 * 100)
        self.assertEqual((r.regiao.texto_percentil, r.regiao.em_limite), ("63,6%", False))
        # Brasil: (300 + 150 + 200/2) / 750. Sempre exato.
        self.assertAlmostEqual(r.brasil.percentil, 550 / 750 * 100)
        self.assertEqual((r.brasil.texto_percentil, r.brasil.em_limite), ("73,3%", False))
        # UF em limite: a diferença para o Brasil não sai (DL-04, 8.7).
        self.assertIsNone(r.diferenca_pp)
        self.assertEqual((r.uf.n, r.regiao.n, r.brasil.n), (200, 550, 750))
        self.assertEqual((r.uf.rotulo, r.regiao.rotulo, r.brasil.rotulo),
                         ("Santa Catarina", "Região Sul", "Brasil"))

    def test_diferenca_quando_a_uf_nao_esta_em_limite(self):
        # SC com 1.000 pessoas: limites 10,0% e 90,0%; 500 fica no meio.
        self.cdfs[(2022, "mt", "UF-SC")] = cdf((400, 300), (500, 400), (600, 300))
        r = tr.comparar(self.cdfs, self.entrada())
        self.assertFalse(r.uf.em_limite)
        self.assertEqual(r.uf.texto_percentil, "50,0%")
        self.assertAlmostEqual(r.diferenca_pp, 50.0 - 550 / 750 * 100)

    def test_medidas_do_motor(self):
        r = tr.comparar(self.cdfs, self.entrada())
        self.assertAlmostEqual(r.uf.media, 550.0)
        self.assertAlmostEqual(r.uf.desvio, 50.0)
        self.assertEqual(r.uf.mediana, 500.0)  # mediana inferior (DL-01)
        self.assertAlmostEqual(r.uf.z, -1.0)

    def test_superioridade_contra_o_restante_do_pais(self):
        r = tr.comparar(self.cdfs, self.entrada())
        # Restante = PR + RS + BA: 400 x 300, 450 x 150, 500 x 100 (N = 550).
        # SC 500 (100): vence 450 pessoas, empata 100 -> 100 * (450 + 50).
        # SC 600 (100): vence as 550 -> 100 * 550.
        esperado = (100 * 500 + 100 * 550) / (200 * 550)
        self.assertAlmostEqual(r.prob_superioridade, esperado)

    def test_superioridade_da_regiao_contra_o_restante_do_pais(self):
        r = tr.comparar(self.cdfs, self.entrada())
        # Sul (550): 400 x100, 450 x150, 500 x200, 600 x100. Restante = BA: 400 x200.
        # 400: empata 200 -> 100 * 100; 450, 500, 600: vencem os 200.
        esperado = (100 * 100 + (150 + 200 + 100) * 200) / (550 * 200)
        self.assertAlmostEqual(r.superioridade_regiao, esperado)

    def test_regiao_que_e_o_pais_inteiro(self):
        cdfs = {(2022, "mt", "UF-SC"): cdf((500, 300)), (2022, "mt", "RG-S"): cdf((500, 300)),
                (2022, "mt", "BR"): cdf((500, 300))}
        r = tr.comparar(cdfs, self.entrada())
        self.assertIsNone(r.superioridade_regiao)
        self.assertTrue(any("fora da região" in a for a in r.avisos))

    def test_restante_e_o_brasil_menos_a_uf(self):
        resto = tr.restante(self.cdfs[(2022, "mt", "BR")], self.cdfs[(2022, "mt", "UF-SC")])
        self.assertEqual(resto, cdf((400, 300), (450, 150), (500, 100)))

    def test_restante_rejeita_parte_fora_do_total(self):
        with self.assertRaises(ValueError):
            tr.restante(cdf((500, 10)), cdf((500, 11)))
        with self.assertRaises(ValueError):
            tr.restante(cdf((500, 10)), cdf((600, 1)))
        with self.assertRaises(ValueError):
            tr.restante(cdf((500, 10)), cdf((500, 10)))

    def test_posicao_da_mediana_entre_as_ufs(self):
        # Medianas: SC 500, RS 450, PR 400, BA 400. PR e BA dividem a 3ª posição.
        ranking = tr.medianas_ufs(self.cdfs, 2022, "mt")
        self.assertEqual([uf for uf, *_ in ranking], ["SC", "RS", "BA", "PR"])
        r = tr.comparar(self.cdfs, self.entrada(uf="RS"))
        self.assertEqual((r.posicao_mediana, r.ufs_comparadas, r.mediana_empatada_com), (2, 4, 0))
        self.assertTrue(any("23 UF(s) sem grupo publicado" in a for a in r.avisos))

    def test_mediana_empatada_divide_a_posicao(self):
        # A sigla não desempata: PR e BA ficam ambas em 3º, e ninguém fica em 4º.
        for uf in ("PR", "BA"):
            r = tr.comparar(self.cdfs, self.entrada(uf=uf))
            with self.subTest(uf=uf):
                self.assertEqual((r.posicao_mediana, r.mediana_empatada_com), (3, 1))

    def test_uf_abaixo_do_piso_nao_quebra(self):
        r = tr.comparar(self.cdfs, self.entrada(uf="SP"))  # SP e Sudeste ausentes
        self.assertFalse(r.uf.disponivel)
        self.assertFalse(r.regiao.disponivel)
        self.assertIn("grupo insuficiente", r.uf.motivo)
        self.assertTrue(r.brasil.disponivel)
        self.assertIsNone(r.diferenca_pp)
        self.assertIsNone(r.prob_superioridade)
        self.assertIsNone(r.posicao_mediana)

    def test_uf_publicada_com_regiao_presente(self):
        r = tr.comparar(self.cdfs, self.entrada(uf="BA"))
        self.assertTrue(r.regiao.disponivel)
        self.assertEqual(r.regiao.n, 200)

    def test_area_sem_nenhum_grupo(self):
        r = tr.comparar(self.cdfs, self.entrada(area="redacao", nota=600.0))
        self.assertFalse(r.uf.disponivel or r.regiao.disponivel or r.brasil.disponivel)
        self.assertEqual(r.ufs_comparadas, 0)

    def test_nota_fora_da_distribuicao(self):
        r = tr.comparar(self.cdfs, self.entrada(nota=1000.0))
        self.assertEqual((r.uf.percentil, r.regiao.percentil, r.brasil.percentil), (100.0, 100.0, 100.0))
        r = tr.comparar(self.cdfs, self.entrada(nota=0.0))
        self.assertEqual((r.uf.percentil, r.brasil.percentil), (0.0, 0.0))

    def test_desvio_zero_vira_aviso(self):
        r = tr.comparar(self.cdfs, self.entrada(uf="RS", nota=450.0))
        self.assertIsNone(r.uf.z)
        self.assertTrue(any("indefinido" in a for a in r.avisos))

    def test_pais_de_uma_uf_so(self):
        cdfs = {(2022, "mt", "UF-SC"): cdf((500, 100)), (2022, "mt", "RG-S"): cdf((500, 100)),
                (2022, "mt", "BR"): cdf((500, 100))}
        r = tr.comparar(cdfs, self.entrada())
        self.assertIsNone(r.prob_superioridade)
        self.assertTrue(any("restante do país" in a for a in r.avisos))

    def test_formatacao(self):
        self.assertEqual(est.formatar_percentil(73.333), "73,3%")
        self.assertEqual(tr.formatar_z(-1.0), "-1,00")
        self.assertEqual(tr.formatar_inteiro(1927753), "1.927.753")


# ================================================= LIMITES DE EXIBIÇÃO (DL-04, 8)


def chave_ordem(texto: str) -> tuple:
    """Posição lida na tela: "abaixo de X" logo abaixo de X, "acima de X" logo acima.

    "100,0%" seguido de "acima de 99,9%" conta como inversão.
    """
    if texto.startswith("abaixo de"):
        return (float(texto[10:].rstrip("%").replace(",", ".")), 0)
    if texto.startswith("acima de"):
        return (float(texto[9:].rstrip("%").replace(",", ".")), 2)
    return (float(texto.rstrip("%").replace(",", ".")), 1)


def conferir_exibicao(caso: unittest.TestCase, distribuicao) -> None:
    """Varre todas as notas do grupo e vizinhas: sem rótulo falso e sem inversão."""
    total = distribuicao[-1][1] + distribuicao[-1][2]
    inferior, superior = est.limites_exibicao(total)
    notas = sorted({x for nota, _, _ in distribuicao for x in (nota - 0.05, nota, nota + 0.05)})
    anterior = None
    for nota in notas:
        p = tr.percentil_exato_acumulado(distribuicao, nota)
        texto, em_limite = est.exibir_percentil(distribuicao, nota)
        if texto.startswith("acima de"):
            caso.assertGreater(p, superior / 10, (nota, texto))
        elif texto.startswith("abaixo de"):
            caso.assertLess(p, inferior / 10, (nota, texto))
        else:
            caso.assertFalse(em_limite)
            caso.assertTrue(inferior <= round(p * 10) <= superior, (nota, texto))
        chave = chave_ordem(texto)
        if anterior is not None:
            caso.assertLessEqual(anterior, chave, (nota, texto))
        anterior = chave


class TestLimitesExibicao(unittest.TestCase):
    def test_formula_roraima_matematica_2022(self):
        # N = 3.984: 100 · 3.884 / 3.984 = 97,49 -> 97,4; 100 · 100 / 3.984 = 2,51 -> 2,6.
        self.assertEqual(est.limites_exibicao(3984), (26, 974))

    def test_arredondamento_dos_limites(self):
        self.assertEqual(est.limites_exibicao(1000), (100, 900))  # exatos, sem arredondar
        self.assertEqual(est.limites_exibicao(200), (500, 500))  # se encontram
        self.assertEqual(est.limites_exibicao(221954), (1, 999))  # 0,045% -> 0,1%; 99,95% -> 99,9%

    def test_grupo_menor_que_200_nunca_tem_posicao_exata(self):
        inferior, superior = est.limites_exibicao(150)
        self.assertGreater(inferior, superior)
        distribuicao = cdf(*[(n, 1) for n in range(300, 450)])
        for nota in [299.0, 300.0, 374.0, 375.0, 449.0, 500.0]:
            with self.subTest(nota=nota):
                self.assertTrue(est.exibir_percentil(distribuicao, nota)[1])

    def test_borda_exata_nao_vira_limite(self):
        # N = 1.000 (notas 0 a 999, uma pessoa cada) e limites 10,0% / 90,0%.
        # p = 90,0% em cheio sai exato; 90,05% já vira "acima de 90,0%".
        distribuicao = cdf(*[(n, 1) for n in range(1000)])
        self.assertEqual(est.exibir_percentil(distribuicao, 899.5), ("90,0%", False))  # 900 / 1000
        self.assertEqual(est.exibir_percentil(distribuicao, 900.0), ("acima de 90,0%", True))  # 900,5 / 1000
        self.assertEqual(est.exibir_percentil(distribuicao, 99.5), ("10,0%", False))  # 100 / 1000
        self.assertEqual(est.exibir_percentil(distribuicao, 99.0), ("abaixo de 10,0%", True))  # 99,5 / 1000

    def test_empates_nao_geram_rotulo_falso(self):
        # Caso tipo Redação: muitas pessoas empatadas na nota consultada. O
        # rótulo sai do percentil (empate conta metade), não de contar quem
        # está acima: "acima de X%" só aparece se a posição real passa de X.
        distribuicao = cdf((500, 1850), (980, 150))  # N = 2.000, limites 5,0% e 95,0%
        self.assertAlmostEqual(tr.percentil_exato_acumulado(distribuicao, 980.0), 96.25)
        self.assertEqual(est.exibir_percentil(distribuicao, 980.0), ("acima de 95,0%", True))
        # Empate grande no meio: 1.000 pessoas em 500 de N = 2.000 -> p = 50% exato,
        # mesmo sem ninguém com nota exatamente 500 dos dois lados.
        distribuicao = cdf((400, 500), (500, 1000), (600, 500))
        self.assertEqual(est.exibir_percentil(distribuicao, 500.0), ("50,0%", False))
        conferir_exibicao(self, distribuicao)

    def test_varredura_sem_rotulo_falso_nem_inversao(self):
        rng = random.Random(4)
        for n in [200, 201, 250, 999, 1000, 1001, 3984, 20000]:
            pesos = [rng.choice([1, 1, 1, 2, 5, 40]) for _ in range(n)]
            contagens, acumulado, nota = [], 0, 300.0
            for peso in pesos:
                if acumulado >= n:
                    break
                peso = min(peso, n - acumulado)
                contagens.append((nota, peso))
                acumulado += peso
                nota = round(nota + rng.choice([0.1, 0.1, 0.5, 2.0]), 1)
            with self.subTest(n=n):
                conferir_exibicao(self, cdf(*contagens))

    def test_alcance_do_limite(self):
        # Roraima, Matemática 2022 (N = 3.984): limites 2,6% e 97,4%.
        self.assertAlmostEqual(est.alcance_do_limite(3984, "acima"), 3984 * 26 / 1000)  # 103,6
        self.assertAlmostEqual(est.alcance_do_limite(3984, "abaixo"), 3984 * 26 / 1000)
        # Grupos grandes: cerca de 0,1% de N (São Paulo e Nordeste, 2022).
        self.assertEqual(round(est.alcance_do_limite(304615, "acima")), 305)
        self.assertEqual(round(est.alcance_do_limite(692087, "acima")), 692)
        for n in (200, 201, 999, 3984, 50020, 1116723):
            with self.subTest(n=n):
                self.assertGreaterEqual(est.alcance_do_limite(n, "acima"), PISO_GRUPO)
                self.assertGreaterEqual(est.alcance_do_limite(n, "abaixo"), PISO_GRUPO)
        with self.assertRaises(ValueError):
            est.alcance_do_limite(3984, "meio")

    def test_alcance_e_a_borda_real_do_limite(self):
        # Varre uma nota por pessoa: toda posição em limite fica a menos do
        # alcance da ponta, e toda posição exata fica a pelo menos o alcance.
        for n in (250, 1000, 3984):
            distribuicao = cdf(*[(i / 10, 1) for i in range(n)])
            for nota, cont, abaixo in distribuicao:
                texto, em_limite = est.exibir_percentil(distribuicao, nota)
                acima_meio, abaixo_meio = n - abaixo - cont / 2, abaixo + cont / 2
                with self.subTest(n=n, nota=nota):
                    if texto.startswith("acima"):
                        self.assertLess(acima_meio, est.alcance_do_limite(n, "acima"))
                    elif texto.startswith("abaixo"):
                        self.assertLess(abaixo_meio, est.alcance_do_limite(n, "abaixo"))
                    else:
                        self.assertGreaterEqual(acima_meio, est.alcance_do_limite(n, "acima"))
                        self.assertGreaterEqual(abaixo_meio, est.alcance_do_limite(n, "abaixo"))

    def test_posicao_unica_igual_ao_motor(self):
        # dobro_posicao é a fonte única da posição na exibição. O percentil que
        # sai dele é a fração exata 100·(2·abaixo + iguais)/(2N) com um só
        # arredondamento; o do motor arredonda duas vezes e pode diferir no
        # último dígito (1 ulp), nunca mais que isso.
        from fractions import Fraction
        rng = random.Random(11)
        distribuicao = cdf(*sorted({round(rng.uniform(0, 1000), 1): rng.randint(1, 30)
                                    for _ in range(800)}.items()))
        notas = [n for n, _, _ in distribuicao]
        total = distribuicao[-1][1] + distribuicao[-1][2]
        for nota in notas + [n + 0.05 for n in notas] + [-1.0, 0.0, 1000.0, 1001.0]:
            dobro, n_total = est.dobro_posicao(distribuicao, nota)
            abaixo = sum(n for x, n, _ in distribuicao if x < nota)
            iguais = sum(n for x, n, _ in distribuicao if x == nota)
            self.assertEqual((dobro, n_total), (2 * abaixo + iguais, total))
            percentil = tr._cenario({(2022, "mt", "UF-SC"): distribuicao}, 2022, "mt", "UF-SC", nota).percentil
            self.assertEqual(percentil, float(Fraction(100 * dobro, 2 * total)))
            self.assertAlmostEqual(percentil, tr.percentil_exato_acumulado(distribuicao, nota), places=12)
            self.assertEqual(est.exibir_percentil(distribuicao, nota), est.texto_da_posicao(dobro, total))
        for invalida in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                est.dobro_posicao(distribuicao, invalida)
        with self.assertRaises(ValueError):
            est.dobro_posicao([], 500.0)

    def test_brasil_segue_exato(self):
        cdfs = {(2022, "mt", "BR"): cdf((500, 100), (600, 100)),
                (2022, "mt", "UF-SC"): cdf((500, 100), (600, 100))}
        r = tr.comparar(cdfs, tr.validar_entrada(2022, "mt", 600.0, "SC", [2022]))
        self.assertEqual((r.brasil.texto_percentil, r.brasil.em_limite), ("75,0%", False))
        self.assertEqual((r.uf.texto_percentil, r.uf.em_limite), ("acima de 50,0%", True))

    def test_empate_grande_na_nota_zero_sai_exato(self):
        # Caso real (Redação 2019, Centro-Oeste): 6.241 empatados na nota 0 de
        # 249.253, ninguém estritamente abaixo, e a posição sai exata (1,3%):
        # abaixo + metade dos empatados = 3.120,5 >= 100. Reproduzido em escala.
        distribuicao = cdf((0, 6241), (500, 243012))
        self.assertEqual(est.limites_exibicao(249253), (1, 999))  # 0,04% -> 0,1%; 99,96% -> 99,9%
        self.assertEqual(est.exibir_percentil(distribuicao, 0.0), ("1,3%", False))


class TestAuditoria(unittest.TestCase):
    """scripts/auditoria_limites.py: a contagem que sustenta a DL-04, item 8."""

    @classmethod
    def setUpClass(cls):
        import auditoria_limites as au
        cls.au = au
        rng = random.Random(8)
        cls.cdfs = {}
        for ano, area, grupo, n in [(2022, "mt", "UF-RR", 3984), (2022, "cn", "UF-AP", 4200),
                                    (2019, "redacao", "RG-CO", 2500), (2022, "mt", "BR", 9000)]:
            passo = 20.0 if area == "redacao" else 0.1
            contagens: dict[float, int] = {}
            for _ in range(n):
                nota = round(min(max(rng.gauss(520, 90), 0.0), 1000.0) / passo) * passo
                contagens[round(nota, 1)] = contagens.get(round(nota, 1), 0) + 1
            cls.cdfs[(ano, area, grupo)] = construir_acumulada(sorted(contagens.items()))
        cls.r = au.auditar(cls.cdfs)

    def test_regra_atual_sem_rotulo_falso_nem_inversao(self):
        self.assertEqual(self.r["grupos_varridos"], 3)  # Brasil fica de fora
        self.assertEqual(self.r["regra_atual"], {"rotulos_falsos": 0, "inversoes": 0})

    def test_regra_anterior_inverte(self):
        self.assertGreater(self.r["regra_anterior_grupos_com_inversao"], 0)

    def test_posicao_exata_tem_100_de_cada_lado_com_empates_pela_metade(self):
        self.assertGreaterEqual(self.r["menor_lado_posicao_exata"]["abaixo_mais_metade_empatados"], PISO_GRUPO)

    def test_residual_conta_so_2022_e_areas_objetivas(self):
        res = self.r["risco_residual_2022_areas_objetivas"]
        self.assertEqual(res["combinacoes_varridas"], 2)  # RR/mt e AP/cn; redação e 2019 fora
        o = res["ocorrencias"]
        self.assertLessEqual(o["com_limite"], o["sem_limite"])
        self.assertEqual(o["com_limite_grupo_menor_100mil"], o["com_limite"])

    def test_chave_de_ordem_le_o_limite(self):
        self.assertLess(self.au.chave("acima de 99,9%"), self.au.chave("100,0%"))
        self.assertLess(self.au.chave("abaixo de 2,6%"), self.au.chave("2,6%"))
        self.assertLess(self.au.chave("2,6%"), self.au.chave("acima de 2,6%"))


# ============================================ AGREGAÇÃO DE PONTA A PONTA


class TestAgregacao(unittest.TestCase):
    """RAW sintético -> TRUSTED (ETL real) -> dist_territorial, contra cálculo bruto.

    Composição (todos com nota nas cinco áreas):
      SC: 200 elegíveis; PR: exatamente 100 (limite do piso);
      RS: 99 elegíveis + 1 treineiro (abaixo do piso);
      SP: 150; BA: 120; SE (Sergipe): 110.
    Sul = 399 (RS entra na região mesmo suprimido como UF).
    """

    AREAS = {"cn": "NU_NOTA_CN", "ch": "NU_NOTA_CH", "lc": "NU_NOTA_LC",
             "mt": "NU_NOTA_MT", "redacao": "NU_NOTA_REDACAO"}
    COMPOSICAO = {"SC": (200, 560), "PR": (100, 540), "RS": (99, 530), "SP": (150, 570),
                  "BA": (120, 500), "SE": (110, 490)}

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        rng = random.Random(2004)
        cls.registros: list[dict] = []
        linhas = []

        def pessoa(uf, media, elegivel=True):
            linha = linha_base()
            linha["NU_INSCRICAO"] = str(230000000000 + len(linhas))
            linha["SG_UF_PROVA"] = uf
            if not elegivel:
                linha["IN_TREINEIRO"] = "1"
            notas = {}
            for area, coluna in cls.AREAS.items():
                nota = round(min(max(rng.gauss(media, 80), 0.0), 1000.0), 1)
                nota = float(round(nota / 40) * 40) if area == "redacao" else round(nota / 5) * 5.0
                linha[coluna] = f"{nota}"
                notas[area] = nota
            linhas.append(linha)
            cls.registros.append({"uf": uf, "elegivel": elegivel, **notas})

        for uf, (quantidade, media) in cls.COMPOSICAO.items():
            for _ in range(quantidade):
                pessoa(uf, media)
        pessoa("RS", 530, elegivel=False)

        csv = cls.tmp / "microdados.csv"
        escrever_csv(csv, linhas)
        con = duckdb.connect()
        etl.gerar_trusted(con, csv, ANO, cls.tmp / "trusted")
        con.close()
        cls.destino = cls.tmp / "analytics" / "dist_territorial.parquet"
        cls.manifesto = cls.tmp / "analytics" / "_manifesto_territorial.json"
        cls.resultado = tr.etapa_territorial(cls.tmp / "trusted", cls.destino, cls.manifesto)
        cls.cdfs = tr.carregar(cls.destino)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def notas(self, area: str, grupo: str) -> list[float]:
        def pertence(r):
            if not r["elegivel"]:
                return False
            if grupo == tr.BRASIL:
                return True
            tipo, _, sigla = grupo.partition("-")
            return tr.REGIAO_DA_UF[r["uf"]] == sigla if tipo == "RG" else r["uf"] == sigla
        return [r[area] for r in self.registros if pertence(r)]

    def test_grupos_publicados_e_suprimidos(self):
        grupos = {g for (_, area, g) in self.cdfs if area == "mt"}
        self.assertEqual(grupos, {"BR", "RG-S", "RG-SE", "RG-NE",
                                  "UF-SC", "UF-PR", "UF-SP", "UF-BA", "UF-SE"})
        self.assertIn(f"{ANO}/mt/UF-RS", self.resultado["grupos"]["suprimidos_abaixo_do_piso"])

    def test_tamanhos_dos_grupos(self):
        total = lambda g: self.cdfs[(ANO, "mt", g)][-1][1] + self.cdfs[(ANO, "mt", g)][-1][2]  # noqa: E731
        self.assertEqual(total("UF-PR"), PISO_GRUPO)  # no limite: publicado
        self.assertEqual(total("RG-S"), 399)  # RS conta na região
        self.assertEqual(total("RG-NE"), 230)  # BA + Sergipe
        self.assertEqual(total("RG-SE"), 150)  # Sudeste = só SP
        self.assertEqual(total("UF-SE"), 110)  # Sergipe não se mistura ao Sudeste
        self.assertEqual(total("BR"), 779)

    def test_percentil_igual_ao_calculo_bruto(self):
        for (ano, area, grupo), distribuicao in self.cdfs.items():
            notas = self.notas(area, grupo)
            for nota in {min(notas), max(notas), 300.0, 500.0, 512.5, 640.0, 1000.0}:
                with self.subTest(area=area, grupo=grupo, nota=nota):
                    obtido = tr._cenario(self.cdfs, ano, area, grupo, nota).percentil
                    self.assertAlmostEqual(obtido, percentil_bruto(notas, nota), places=9)

    def test_superioridade_igual_a_contagem_de_pares(self):
        for area in self.AREAS:
            a = self.notas(area, "UF-SC")
            b = [r[area] for r in self.registros if r["elegivel"] and r["uf"] != "SC"]
            esperado = sum((x > y) + 0.5 * (x == y) for x in a for y in b) / (len(a) * len(b))
            entrada = tr.validar_entrada(ANO, area, 500.0, "SC", [ANO])
            with self.subTest(area=area):
                self.assertAlmostEqual(tr.comparar(self.cdfs, entrada).prob_superioridade, esperado, places=12)
            # Região Sul (SC + PR + RS, inclusive RS abaixo do piso) contra o resto.
            sul = {"SC", "PR", "RS"}
            a = [r[area] for r in self.registros if r["elegivel"] and r["uf"] in sul]
            b = [r[area] for r in self.registros if r["elegivel"] and r["uf"] not in sul]
            esperado = sum((x > y) + 0.5 * (x == y) for x in a for y in b) / (len(a) * len(b))
            with self.subTest(area=area, nivel="regiao"):
                self.assertAlmostEqual(tr.comparar(self.cdfs, entrada).superioridade_regiao, esperado, places=12)

    def test_auditoria_da_uf(self):
        u = self.resultado["uf_prova"][str(ANO)]
        self.assertEqual(u, {"elegiveis": 779, "uf_ausente": 0, "uf_invalida": 0, "ufs_presentes": 6})
        self.assertEqual(self.resultado["verificacao"]["maior_divergencia_pp"], 0.0)

    def test_sem_identificador_no_artefato(self):
        colunas = [c[0] for c in duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{self.destino}')").fetchall()]
        self.assertEqual(colunas, ["ano", "area", "recorte", "grupo", "nota", "n", "abaixo", "total"])
        minimo = duckdb.sql(f"SELECT min(total) FROM read_parquet('{self.destino}')").fetchone()[0]
        self.assertGreaterEqual(minimo, PISO_GRUPO)

    def test_divergencia_entre_sql_e_python_bloqueia_a_publicacao(self):
        destino = self.tmp / "defeito" / "dist_territorial.parquet"
        original = tr.sql_artefato
        defeituoso = lambda fonte, piso: original(fonte, piso).replace(  # noqa: E731
            "CAST(n AS BIGINT) AS n", "CAST(n + 1 AS BIGINT) AS n")
        with mock.patch.object(tr, "sql_artefato", defeituoso), self.assertRaises(AssertionError):
            tr.etapa_territorial(self.tmp / "trusted", destino, self.tmp / "defeito" / "m.json")
        self.assertFalse(destino.exists())

    def test_regiao_errada_bloqueia_a_publicacao(self):
        # Simula SC classificada no Sudeste: a soma UFs -> região tem de barrar.
        destino = self.tmp / "regiao" / "dist_territorial.parquet"
        trocada = dict(tr.REGIAO_DA_UF, SC="SE")
        with mock.patch.object(tr, "REGIAO_DA_UF", trocada), self.assertRaises(AssertionError):
            tr.etapa_territorial(self.tmp / "trusted", destino, self.tmp / "regiao" / "m.json")
        self.assertFalse(destino.exists())

    def test_piso_inalcancavel_nao_publica_nada(self):
        destino = self.tmp / "vazio" / "dist_territorial.parquet"
        with self.assertRaises(ValueError):
            tr.etapa_territorial(self.tmp / "trusted", destino, self.tmp / "vazio" / "m.json", piso=10_000)
        self.assertFalse(destino.exists())


class TestUfInvalidaNaTrusted(unittest.TestCase):
    """UF fora das 27 siglas: fora de todos os grupos e contada no manifesto."""

    def test_uf_invalida(self):
        con = duckdb.connect()
        con.execute("CREATE TABLE t (ano BIGINT, elegivel BOOLEAN, uf_prova VARCHAR, nota_cn DOUBLE,"
                    " nota_ch DOUBLE, nota_lc DOUBLE, nota_mt DOUBLE, nota_redacao DOUBLE)")
        linhas = [(2022, True, "SC", 500.0, 500.0, 500.0, 500.0 + i, 600.0) for i in range(120)]
        linhas += [(2022, True, "XX", 900.0, 900.0, 900.0, 900.0, 900.0)] * 3
        linhas += [(2022, True, "", 900.0, 900.0, 900.0, 900.0, 900.0)] * 2
        con.executemany("INSERT INTO t VALUES (?, ?, ?, ?, ?, ?, ?, ?)", linhas)
        cdfs, _, _ = tr.calcular_cdfs(con, "t")
        self.assertEqual(cdfs[(2022, "mt", "BR")][-1][1] + cdfs[(2022, "mt", "BR")][-1][2], 120)
        self.assertEqual(tr.auditar_uf(con, "t")["2022"],
                         {"elegiveis": 125, "uf_ausente": 2, "uf_invalida": 3, "ufs_presentes": 1})
        con.close()


# ================================================== INTERFACE (STREAMLIT)


@unittest.skipIf(AppTest is None, "streamlit nao instalado")
class TestPagina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        arquivo = Path(cls.tmp.name) / "dist_territorial.parquet"
        grupos = TestComparacao()
        grupos.setUp()
        linhas = [(ano, area, "territorial", g, nota, n, abaixo, d[-1][1] + d[-1][2])
                  for (ano, area, g), d in grupos.cdfs.items() for nota, n, abaixo in d]
        con = duckdb.connect()
        con.execute("CREATE TABLE e (ano BIGINT, area VARCHAR, recorte VARCHAR, grupo VARCHAR,"
                    " nota DOUBLE, n BIGINT, abaixo BIGINT, total BIGINT)")
        con.executemany("INSERT INTO e VALUES (?, ?, ?, ?, ?, ?, ?, ?)", linhas)
        con.execute(f"COPY e TO '{arquivo}' (FORMAT parquet)")
        con.close()
        os.environ["RADAR_DIST_TERRITORIAL"] = str(arquivo)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("RADAR_DIST_TERRITORIAL", None)
        cls.tmp.cleanup()

    def abrir(self) -> AppTest:
        at = AppTest.from_file(str(PAGINA), default_timeout=30)
        at.run()
        self.assertFalse(at.exception)
        return at

    @staticmethod
    def campo(at, rotulo):
        return next(c for c in at.number_input if c.label == rotulo)

    def uf(self, at, sigla):
        next(s for s in at.selectbox if s.label.startswith("Em qual UF")).set_value(sigla)

    def test_tres_cenarios_na_tela(self):
        at = self.abrir()
        self.uf(at, "SC")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m.value for m in at.metric], ["abaixo de 50,0%", "63,6%", "73,3%"])
        # SC em limite: sem a diferença para o Brasil (DL-04, 8.7).
        self.assertFalse(any("pontos percentuais" in m.value for m in at.markdown))
        self.assertTrue(any("perto do topo" in c.value or "perto da base" in c.value for c in at.caption))
        # SC tem N = 200 no teste: limite 50,0%, alcance de 100 pessoas.
        self.assertTrue(any("cerca de 100 pessoas mais perto da base, num grupo de 200" in c.value
                            for c in at.caption))
        self.assertTrue(any("1ª maior mediana entre as 4 UFs" in m.value for m in at.markdown))

    def test_explicacao_descreve_a_regra_pela_posicao(self):
        # A regra por contagem ("menos de 100 pessoas de um dos lados") foi
        # rejeitada na DL-04, 8.4; o texto da página não pode descrevê-la.
        texto = PAGINA.read_text(encoding="utf-8")
        self.assertNotIn("pessoas de um dos lados", texto)
        self.assertIn("contando pela metade", texto)

    def test_sem_uf_pede_a_uf(self):
        at = self.abrir()
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertIn("UF", at.warning[0].value)

    def test_sem_nota_pede_ao_menos_uma(self):
        at = self.abrir()
        self.uf(at, "SC")
        at.button[0].click().run()
        self.assertIn("ao menos uma nota", at.warning[0].value)

    def test_uf_abaixo_do_piso_vira_grupo_insuficiente(self):
        at = self.abrir()
        self.uf(at, "SP")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("grupo insuficiente" in i.value for i in at.info))
        self.assertEqual(at.metric[2].value, "73,3%")  # Brasil continua

    def test_redacao_invalida_mostra_erro_sem_quebrar(self):
        at = self.abrir()
        self.uf(at, "SC")
        self.campo(at, "Redação").set_value(610.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertIn("múltipla de 20", at.error[0].value)

    def test_dados_digitados_nao_vao_para_a_url(self):
        at = self.abrir()
        self.uf(at, "SC")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertEqual(dict(at.query_params), {})

    def test_artefato_ausente(self):
        anterior = os.environ["RADAR_DIST_TERRITORIAL"]
        os.environ["RADAR_DIST_TERRITORIAL"] = str(Path(self.tmp.name) / "nao_existe.parquet")
        try:
            at = AppTest.from_file(str(PAGINA), default_timeout=30)
            at.run()
            self.assertIn("Artefato do módulo ausente", at.error[0].value)
        finally:
            os.environ["RADAR_DIST_TERRITORIAL"] = anterior


if __name__ == "__main__":
    unittest.main()
