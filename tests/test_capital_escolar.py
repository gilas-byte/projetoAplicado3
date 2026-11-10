"""Testes do módulo Capital escolar familiar (autor: Guilherme da Silva Anselmo).

Cobrem as regras da DL-05 (docs/decisoes): níveis a partir de Q001 e Q002,
tratamento de "Não sei", vazio e código inválido, validação da entrada, os
cenários e as medidas entre níveis, casos de erro (nível vizinho abaixo do
piso, sem nível, grupo ausente) e a agregação de ponta a ponta com microdados
sintéticos, conferida contra um cálculo independente em Python puro.

Rodam sem os microdados do INEP:
  ./.venv/bin/python -m unittest tests/test_capital_escolar.py -v
"""

from __future__ import annotations

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

import capital_escolar as ce  # noqa: E402
import estatistica as est  # noqa: E402
import etl  # noqa: E402
from colunas import PISO_GRUPO  # noqa: E402
from estatistica import construir_acumulada  # noqa: E402
from test_etl import ANO, escrever_csv, linha_base  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None

PAGINA = RAIZ / "app" / "pages" / "3_Capital_escolar_familiar.py"


def cdf(*pares: tuple[float, int]):
    return construir_acumulada([(float(nota), n) for nota, n in pares])


def somar(*listas):
    """Soma listas de (nota, n) nota a nota: monta o Brasil a partir dos níveis."""
    soma: dict[float, int] = {}
    for lista in listas:
        for nota, n in lista:
            soma[nota] = soma.get(nota, 0) + n
    return sorted(soma.items())


def percentil_bruto(notas: list[float], nota: float) -> float:
    """Posto médio direto sobre a lista de notas, sem estrutura agregada."""
    return (sum(x < nota for x in notas) + sum(x == nota for x in notas) / 2) / len(notas) * 100


# Níveis à mão, edição 2022, Matemática (N entre parênteses).
NV_D = [(400, 300), (500, 300), (600, 300)]  # 900
NV_E = [(500, 300), (600, 300), (700, 300)]  # 900
NV_F = [(500, 100), (600, 100)]  # 200: só a posição de 50,0% sai exata
NV_G = [(600, 200), (700, 200)]  # 400


def cdfs_de_teste(sem: tuple[str, ...] = ()) -> dict:
    niveis = {"D": NV_D, "E": NV_E, "F": NV_F, "G": NV_G}
    saida = {(2022, "mt", ce.grupo_nivel(n)): cdf(*c) for n, c in niveis.items() if n not in sem}
    saida[(2022, "mt", ce.BRASIL)] = cdf(*somar(*niveis.values()))  # 2.400, com todos os níveis
    return saida


# ================================================================ REGRAS


class TestNiveis(unittest.TestCase):
    def test_seis_niveis_e_cada_letra_em_exatamente_um(self):
        self.assertEqual(len(ce.NIVEIS), 6)
        letras = [letra for n in ce.NIVEIS for letra in ce.LETRAS_DO_NIVEL[n]]
        self.assertEqual(sorted(letras), list("ABCDEFG"))  # H não é nível
        self.assertEqual(ce.LETRAS_DO_NIVEL["BC"], ("B", "C"))

    def test_posicoes_em_ordem_crescente(self):
        self.assertEqual([ce.POSICAO_DO_NIVEL[n] for n in ce.NIVEIS], [1, 2, 3, 4, 5, 6])

    def test_codigos_de_grupo_sem_ambiguidade(self):
        self.assertEqual(len(ce.GRUPOS), 7)
        self.assertEqual(len(ce.GRUPOS), len(set(ce.GRUPOS)))
        self.assertNotIn("A", ce.GRUPOS)  # "A" é alternativa; o grupo leva prefixo
        self.assertEqual(ce.grupo_nivel("BC"), "NV-BC")

    def test_rotulos(self):
        self.assertEqual(ce.rotulo_grupo(ce.BRASIL), "Brasil")
        self.assertEqual(ce.rotulo_grupo("NV-F"), "Responsáveis com ensino superior completo")
        for nivel in ce.NIVEIS:
            self.assertIn(nivel, ce.ROTULOS)
            ce.rotulo_grupo(ce.grupo_nivel(nivel))

    def test_rotulo_de_grupo_desconhecido(self):
        for grupo in ("NV-H", "NV-B", "UF-SC", "XX"):
            with self.subTest(grupo=grupo), self.assertRaises(ValueError):
                ce.rotulo_grupo(grupo)

    def test_nivel_do_participante_maior_entre_pai_e_mae(self):
        casos = [
            ("A", "A", "A"), ("B", "C", "BC"), ("C", "A", "BC"), ("D", "B", "D"), ("E", "G", "G"),
            ("G", "F", "G"), ("F", "F", "F"), ("A", "E", "E"),
        ]
        for pai, mae, esperado in casos:
            with self.subTest(pai=pai, mae=mae):
                self.assertEqual(ce.nivel_do_participante(pai, mae), esperado)

    def test_nao_sei_ou_vazio_num_campo_vale_o_outro(self):
        # DL-05, item 2. Limitação documentada: pai = H e mãe = A entra no nível A.
        for pai, mae, esperado in [("H", "A", "A"), ("A", "H", "A"), ("", "E", "E"), (None, "F", "F"),
                                   ("G", None, "G"), ("H", "", None)]:
            with self.subTest(pai=pai, mae=mae):
                self.assertEqual(ce.nivel_do_participante(pai, mae), esperado)

    def test_sem_informacao_nos_dois_fica_sem_nivel(self):
        # DL-05, item 3: não existe nível a atribuir.
        for pai, mae in [("H", "H"), ("", ""), (None, None), ("H", ""), (None, "H")]:
            with self.subTest(pai=pai, mae=mae):
                self.assertIsNone(ce.nivel_do_participante(pai, mae))

    def test_codigo_invalido_contamina_o_registro(self):
        # DL-05, itens 8 e 9: o outro campo, mesmo válido, não salva o registro.
        for pai, mae in [("Z", "G"), ("G", "Z"), ("1", "A"), ("AB", "A"), (7, "A"), ("Z", "H"), ("Z", "")]:
            with self.subTest(pai=pai, mae=mae):
                self.assertIsNone(ce.nivel_do_participante(pai, mae))

    def test_aceita_espaco_e_minuscula(self):
        self.assertEqual(ce.nivel_do_participante(" e ", "d"), "E")

    def test_nivel_de_comparacao_e_o_vizinho_acima(self):
        self.assertEqual(ce.nivel_de_comparacao("A"), ("BC", "acima"))
        self.assertEqual(ce.nivel_de_comparacao("BC"), ("D", "acima"))
        self.assertEqual(ce.nivel_de_comparacao("D"), ("E", "acima"))
        self.assertEqual(ce.nivel_de_comparacao("F"), ("G", "acima"))

    def test_nivel_mais_alto_compara_com_o_de_baixo(self):
        # DL-05, item 7.
        self.assertEqual(ce.nivel_de_comparacao("G"), ("F", "abaixo"))


class TestValidacaoEntrada(unittest.TestCase):
    def validar(self, nota=500.0, pai="E", mae="D", area="mt", ano=2022):
        return ce.validar_entrada(ano, area, nota, pai, mae, [2021, 2022])

    def test_entrada_valida_normalizada(self):
        e = self.validar(nota=512.34 - 0.04, pai=" e ", mae="d")
        self.assertEqual((e.ano, e.area, e.nota, e.pai, e.mae, e.nivel), (2022, "mt", 512.3, "E", "D", "E"))

    def test_nivel_derivado(self):
        self.assertEqual(self.validar(pai="H", mae="B").nivel, "BC")
        self.assertIsNone(self.validar(pai="H", mae="H").nivel)

    def test_h_nos_dois_e_resposta_valida(self):
        e = self.validar(pai="H", mae="h")
        self.assertEqual((e.pai, e.mae, e.nivel), ("H", "H", None))

    def test_erros(self):
        casos = {
            "edicao": (dict(ano=2018), "Edição 2018 indisponível"),
            "edicao_bool": (dict(ano=True), "indisponível"),
            "area": (dict(area="xx"), "Área 'xx' inválida"),
            "sem_nota": (dict(nota=None), "Informe a nota"),
            "nota_texto": (dict(nota="500"), "precisa ser um número"),
            "nota_bool": (dict(nota=True), "precisa ser um número"),
            "nota_nan": (dict(nota=float("nan")), "número finito"),
            "nota_inf": (dict(nota=float("inf")), "número finito"),
            "nota_negativa": (dict(nota=-1.0), "entre 0 e 1000"),
            "nota_acima": (dict(nota=1000.1), "entre 0 e 1000"),
            "duas_casas": (dict(nota=500.05), "uma casa decimal"),
            "redacao_fora_do_passo": (dict(area="redacao", nota=610.0), "múltipla de 20"),
            "sem_pai": (dict(pai=None), "escolaridade de seu pai"),
            "pai_em_branco": (dict(pai="  "), "escolaridade de seu pai"),
            "sem_mae": (dict(mae=None), "escolaridade de sua mãe"),
            "pai_inexistente": (dict(pai="Z"), "não existe"),
            "mae_inexistente": (dict(mae="I"), "não existe"),
            "mae_numero": (dict(mae=3), "alternativa de A a H"),
        }
        for nome, (ajuste, trecho) in casos.items():
            with self.subTest(caso=nome):
                with self.assertRaises(ce.EntradaInvalida) as erro:
                    self.validar(**ajuste)
                self.assertIn(trecho, str(erro.exception))

    def test_redacao_multipla_de_20_vale(self):
        self.assertEqual(self.validar(area="redacao", nota=620.0).nota, 620.0)


class TestOpcoesDoDicionario(unittest.TestCase):
    def test_oito_alternativas_com_texto_oficial_nas_quatro_edicoes(self):
        for ano in (2019, 2020, 2021, 2022):
            for variavel in ("Q001", "Q002"):
                with self.subTest(ano=ano, variavel=variavel):
                    opcoes = ce.opcoes_escolaridade(ano, variavel)
                    self.assertEqual([c for c, _ in opcoes], list("ABCDEFGH"))
                    self.assertEqual(opcoes[0][1], "Nunca estudou")
                    self.assertEqual(opcoes[-1][1], "Não sei")

    def test_edicao_sem_dicionario(self):
        with self.assertRaises(ce.EntradaInvalida):
            ce.opcoes_escolaridade(1999, "Q001")

    def test_variavel_ausente(self):
        with self.assertRaises(ce.EntradaInvalida):
            ce.opcoes_escolaridade(2022, "Q999")

    def test_dicionario_sem_todas_as_alternativas(self):
        with tempfile.TemporaryDirectory() as pasta:
            (Path(pasta) / "dicionario_2022.json").write_text(
                '{"x": [{"variavel": "Q001", "categorias": {"A": "Nunca estudou."}}]}', encoding="utf-8")
            with self.assertRaises(ce.EntradaInvalida):
                ce.opcoes_escolaridade(2022, "Q001", Path(pasta))


# ============================================================= COMPARAÇÃO


class TestComparacao(unittest.TestCase):
    """Valores calculados à mão. Edição 2022, Matemática, com NV_D, NV_E, NV_F e NV_G acima.

    Brasil = D + E + F + G: nota 400 (300), 500 (700), 600 (900), 700 (500); N = 2.400.
    """

    def setUp(self):
        self.cdfs = cdfs_de_teste()

    def entrada(self, nota=500.0, pai="D", mae="D", area="mt"):
        return ce.validar_entrada(2022, area, nota, pai, mae, [2022])

    def test_cenario_padrao_e_o_proprio_nivel_e_o_brasil(self):
        r = ce.comparar(self.cdfs, self.entrada())
        self.assertEqual(r.proprio.rotulo, "Responsáveis com ensino fundamental completo")
        self.assertTrue(r.proprio.disponivel)
        self.assertIsNone(r.vizinho)  # comparação com outro nível é opcional (DL-05, item 5)
        self.assertIsNone(r.diferenca_pp)
        self.assertIsNone(r.prob_superioridade)
        # D: 300 abaixo e 300 iguais em 900 -> (300 + 150) / 900 = 50,0%.
        self.assertEqual((r.proprio.n, r.proprio.texto_percentil, r.proprio.em_limite), (900, "50,0%", False))
        self.assertAlmostEqual(r.proprio.percentil, 50.0)
        # Brasil: (300 + 700 / 2) / 2400 = 27,08...%, sempre exato.
        self.assertEqual((r.brasil.n, r.brasil.texto_percentil), (2400, "27,1%"))
        self.assertAlmostEqual(r.brasil.percentil, 650 / 2400 * 100)

    def test_medidas_do_motor(self):
        r = ce.comparar(self.cdfs, self.entrada())
        self.assertAlmostEqual(r.proprio.media, 500.0)
        self.assertEqual(r.proprio.mediana, 500.0)
        self.assertAlmostEqual(r.proprio.desvio, (2 * 100 ** 2 / 3) ** 0.5)
        self.assertAlmostEqual(r.proprio.z, 0.0)
        for chave, esperado in (("percentil", est.percentil_exato_acumulado(self.cdfs[(2022, "mt", "NV-D")], 500.0)),):
            self.assertAlmostEqual(getattr(r.proprio, chave), esperado)

    def test_comparacao_com_o_nivel_acima(self):
        r = ce.comparar(self.cdfs, self.entrada(), comparar_outro_nivel=True)
        self.assertEqual(r.sentido_vizinho, "acima")
        self.assertEqual(r.vizinho.rotulo, "Responsáveis com ensino médio completo")
        # E: 0 abaixo e 300 iguais em 900 -> 150 / 900 = 16,67%.
        self.assertEqual(r.vizinho.texto_percentil, "16,7%")
        self.assertAlmostEqual(r.diferenca_pp, 50.0 - 150 / 900 * 100)
        # P(D > E) + 0,5 P(=): 1 par maior e 2 empates em 9 pares -> 2 / 9.
        self.assertAlmostEqual(r.prob_superioridade, 2 / 9, places=12)

    def test_superioridade_igual_a_contagem_de_pares(self):
        # Mesma proporção por nota com 1/10 dos participantes: bem menos pares, mesmo resultado.
        d = [x for x, n in NV_D for _ in range(n // 10)]
        e = [x for x, n in NV_E for _ in range(n // 10)]
        esperado = sum((a > b) + 0.5 * (a == b) for a in d for b in e) / (len(d) * len(e))
        r = ce.comparar(self.cdfs, self.entrada(), comparar_outro_nivel=True)
        self.assertAlmostEqual(r.prob_superioridade, esperado, places=12)

    def test_nivel_mais_alto_compara_com_o_de_baixo(self):
        r = ce.comparar(self.cdfs, self.entrada(nota=600.0, pai="G", mae="A"), comparar_outro_nivel=True)
        self.assertEqual(r.entrada.nivel, "G")
        self.assertEqual(r.sentido_vizinho, "abaixo")
        self.assertEqual(r.vizinho.grupo, "NV-F")
        # P(G > F) + 0,5 P(=): 60.000 pares maiores e 20.000 empates em 80.000 -> 70.000 / 80.000.
        self.assertAlmostEqual(r.prob_superioridade, 0.875, places=12)

    def test_limite_de_um_nivel_esconde_a_diferenca_mas_nao_a_superioridade(self):
        # F tem N = 200: a nota 600 fica em 75%, acima do limite de 50,0% (DL-05, item 13).
        r = ce.comparar(self.cdfs, self.entrada(nota=600.0, pai="G", mae="A"), comparar_outro_nivel=True)
        self.assertEqual((r.vizinho.texto_percentil, r.vizinho.em_limite), ("acima de 50,0%", True))
        self.assertFalse(r.proprio.em_limite)  # G: 25,0%
        self.assertIsNone(r.diferenca_pp)
        self.assertIsNotNone(r.prob_superioridade)
        self.assertTrue(any("pontas" in a for a in r.avisos))

    def test_proprio_nivel_em_limite_usa_a_regra_compartilhada(self):
        r = ce.comparar(self.cdfs, self.entrada(nota=600.0, pai="F", mae="F"))
        esperado = est.exibir_percentil(self.cdfs[(2022, "mt", "NV-F")], 600.0)
        self.assertEqual((r.proprio.texto_percentil, r.proprio.em_limite), esperado)
        self.assertTrue(r.proprio.em_limite)

    def test_brasil_segue_exato_mesmo_nas_pontas(self):
        r = ce.comparar(self.cdfs, self.entrada(nota=1000.0))
        self.assertEqual((r.brasil.texto_percentil, r.brasil.em_limite), ("100,0%", False))

    def test_h_nos_dois_mostra_so_o_brasil(self):
        r = ce.comparar(self.cdfs, self.entrada(pai="H", mae="H"), comparar_outro_nivel=True)
        self.assertIsNone(r.proprio)
        self.assertIsNone(r.vizinho)
        self.assertTrue(r.brasil.disponivel)
        self.assertTrue(any("Não sei" in a and "só a posição nacional" in a for a in r.avisos))

    def test_h_num_campo_avisa_a_limitacao(self):
        r = ce.comparar(self.cdfs, self.entrada(pai="H", mae="D"))
        self.assertEqual(r.entrada.nivel, "D")
        self.assertTrue(any("o do outro" in a or "vale a escolaridade do outro" in a for a in r.avisos))
        sem_h = ce.comparar(self.cdfs, self.entrada(pai="D", mae="D"))
        self.assertFalse(any("Não sei" in a for a in sem_h.avisos))

    def test_nivel_vizinho_abaixo_do_piso_nao_pula_de_nivel(self):
        # DL-05, item 6: sem E publicado, a comparação não vira F nem G.
        cdfs = cdfs_de_teste(sem=("E",))
        r = ce.comparar(cdfs, self.entrada(), comparar_outro_nivel=True)
        self.assertFalse(r.vizinho.disponivel)
        self.assertEqual(r.vizinho.grupo, "NV-E")
        self.assertIn("grupo insuficiente", r.vizinho.motivo)
        self.assertIsNone(r.diferenca_pp)
        self.assertIsNone(r.prob_superioridade)
        self.assertTrue(r.proprio.disponivel)

    def test_proprio_nivel_abaixo_do_piso_nao_quebra(self):
        cdfs = cdfs_de_teste(sem=("D",))
        r = ce.comparar(cdfs, self.entrada(), comparar_outro_nivel=True)
        self.assertFalse(r.proprio.disponivel)
        self.assertIn("grupo insuficiente", r.proprio.motivo)
        self.assertIsNone(r.diferenca_pp)
        self.assertIsNone(r.prob_superioridade)
        self.assertTrue(r.brasil.disponivel)

    def test_area_sem_nenhum_grupo(self):
        r = ce.comparar(self.cdfs, self.entrada(area="cn"), comparar_outro_nivel=True)
        for cenario in (r.proprio, r.vizinho, r.brasil):
            self.assertFalse(cenario.disponivel)
        self.assertIsNone(r.diferenca_pp)

    def test_nota_fora_da_distribuicao(self):
        baixa = ce.comparar(self.cdfs, self.entrada(nota=0.0))
        alta = ce.comparar(self.cdfs, self.entrada(nota=1000.0))
        self.assertEqual(baixa.proprio.percentil, 0.0)
        self.assertEqual(alta.proprio.percentil, 100.0)

    def test_desvio_zero_vira_aviso(self):
        cdfs = {(2022, "mt", "NV-A"): cdf((500, 150)), (2022, "mt", ce.BRASIL): cdf((500, 150), (600, 150))}
        r = ce.comparar(cdfs, self.entrada(pai="A", mae="A"))
        self.assertIsNone(r.proprio.z)
        self.assertTrue(any("Z-Score indefinido" in a for a in r.avisos))

    def test_formatacao(self):
        self.assertEqual(ce.formatar_nota(512.3), "512,3")
        self.assertEqual(ce.formatar_z(1.234), "+1,23")
        self.assertEqual(ce.formatar_z(None), "indefinido")
        self.assertEqual(ce.formatar_inteiro(1234567), "1.234.567")


# ================================================ AGREGAÇÃO DE PONTA A PONTA


class TestAgregacao(unittest.TestCase):
    """RAW sintético -> TRUSTED (ETL real) -> dist_capital, contra cálculo bruto.

    Composição (pai, mãe, quantidade; todos elegíveis, com nota nas cinco áreas):
      A: (A, A) 110.
      BC: (B, C) 90 + (C, H) 30 = 120.
      D: (D, D) 150.
      E: (E, A) 60 + (H, E) 60 = 120.
      F: (F, E) 99, mais 1 treineiro F que não conta: abaixo do piso.
      G: (G, G) 100, exatamente o piso.
      Sem nível: (H, H) 40, (vazio, vazio) 10, (H, vazio) 5.
      Campo inválido: (Z, G) 15, que fica só no Brasil.
    Brasil = 769 elegíveis.
    """

    AREAS = {"cn": "NU_NOTA_CN", "ch": "NU_NOTA_CH", "lc": "NU_NOTA_LC",
             "mt": "NU_NOTA_MT", "redacao": "NU_NOTA_REDACAO"}
    COMPOSICAO = [
        ("A", "A", 110, 480), ("B", "C", 90, 500), ("C", "H", 30, 510), ("D", "D", 150, 520),
        ("E", "A", 60, 560), ("H", "E", 60, 570), ("F", "E", 99, 600), ("G", "G", 100, 640),
        ("H", "H", 40, 530), ("", "", 10, 530), ("H", "", 5, 530), ("Z", "G", 15, 640),
    ]
    TAMANHOS = {"BR": 769, "NV-A": 110, "NV-BC": 120, "NV-D": 150, "NV-E": 120, "NV-G": 100}

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        rng = random.Random(2026)
        cls.registros: list[dict] = []
        linhas = []

        def pessoa(pai, mae, media, elegivel=True):
            linha = linha_base()
            linha["NU_INSCRICAO"] = str(230000000000 + len(linhas))
            linha["Q001"], linha["Q002"] = pai, mae
            if not elegivel:
                linha["IN_TREINEIRO"] = "1"
            notas = {}
            for area, coluna in cls.AREAS.items():
                nota = round(min(max(rng.gauss(media, 80), 0.0), 1000.0), 1)
                nota = float(round(nota / 40) * 40) if area == "redacao" else round(nota / 5) * 5.0
                linha[coluna] = f"{nota}"
                notas[area] = nota
            linhas.append(linha)
            cls.registros.append({"pai": pai, "mae": mae, "elegivel": elegivel, **notas})

        for pai, mae, quantidade, media in cls.COMPOSICAO:
            for _ in range(quantidade):
                pessoa(pai, mae, media)
        pessoa("F", "E", 600, elegivel=False)

        csv = cls.tmp / "microdados.csv"
        escrever_csv(csv, linhas)
        con = duckdb.connect()
        etl.gerar_trusted(con, csv, ANO, cls.tmp / "trusted")
        con.close()
        cls.destino = cls.tmp / "analytics" / "dist_capital.parquet"
        cls.manifesto = cls.tmp / "analytics" / "_manifesto_capital.json"
        cls.resultado = ce.etapa_capital(cls.tmp / "trusted", cls.destino, cls.manifesto)
        cls.cdfs = ce.carregar(cls.destino)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def notas(self, area: str, grupo: str) -> list[float]:
        def pertence(r):
            if not r["elegivel"]:
                return False
            if grupo == ce.BRASIL:
                return True
            return ce.grupo_nivel(ce.nivel_do_participante(r["pai"], r["mae"]) or "-") == grupo
        return [r[area] for r in self.registros if pertence(r)]

    def test_grupos_publicados_e_suprimidos(self):
        grupos = {g for (_, area, g) in self.cdfs if area == "mt"}
        self.assertEqual(grupos, set(self.TAMANHOS))
        self.assertNotIn("NV-F", grupos)  # 99 participantes: abaixo do piso
        suprimidos = self.resultado["grupos"]["suprimidos_abaixo_do_piso"]
        self.assertIn(f"{ANO}/mt/NV-F", suprimidos)
        self.assertEqual(len([s for s in suprimidos if s.endswith("/NV-F")]), len(ce.AREAS))

    def test_tamanhos_dos_grupos(self):
        for area in ce.AREAS:
            for grupo, esperado in self.TAMANHOS.items():
                with self.subTest(area=area, grupo=grupo):
                    ultimo = self.cdfs[(ANO, area, grupo)][-1]
                    self.assertEqual(ultimo[1] + ultimo[2], esperado)
        self.assertEqual(self.resultado["grupos"]["publicados"][f"{ANO}/mt/NV-G"], PISO_GRUPO)  # borda do piso

    def test_treineiro_fica_fora_de_todos_os_grupos(self):
        ultimo = self.cdfs[(ANO, "mt", ce.BRASIL)][-1]
        self.assertEqual(ultimo[1] + ultimo[2], 769)  # sem o treineiro

    def test_percentil_igual_ao_calculo_bruto(self):
        for area in ce.AREAS:
            for grupo in self.TAMANHOS:
                notas = self.notas(area, grupo)
                for nota in (min(notas) - 20, min(notas), sorted(notas)[len(notas) // 2], max(notas), max(notas) + 20):
                    with self.subTest(area=area, grupo=grupo, nota=nota):
                        obtido = est.percentil_exato_acumulado(self.cdfs[(ANO, area, grupo)], nota)
                        self.assertAlmostEqual(obtido, percentil_bruto(notas, nota), places=9)

    def test_estatisticas_iguais_ao_calculo_bruto(self):
        for grupo in self.TAMANHOS:
            notas = self.notas("mt", grupo)
            medidas = est.resumo(self.cdfs[(ANO, "mt", grupo)])
            with self.subTest(grupo=grupo):
                self.assertAlmostEqual(medidas["media"], sum(notas) / len(notas), places=9)
                self.assertEqual(medidas["N"], len(notas))
                self.assertEqual(medidas["mediana"], sorted(notas)[(len(notas) + 1) // 2 - 1])

    def test_superioridade_igual_a_contagem_de_pares(self):
        for area in ("mt", "redacao"):
            for proprio in ("A", "BC", "D"):  # o vizinho de E (F) fica abaixo do piso
                vizinho, _ = ce.nivel_de_comparacao(proprio)
                a, b = self.notas(area, ce.grupo_nivel(proprio)), self.notas(area, ce.grupo_nivel(vizinho))
                esperado = sum((x > y) + 0.5 * (x == y) for x in a for y in b) / (len(a) * len(b))
                entrada = ce.validar_entrada(ANO, area, 500.0 if area == "mt" else 520.0, proprio[0], proprio[0], [ANO])
                with self.subTest(area=area, nivel=proprio):
                    r = ce.comparar(self.cdfs, entrada, comparar_outro_nivel=True)
                    self.assertAlmostEqual(r.prob_superioridade, esperado, places=12)

    def test_nivel_d_compara_com_e_e_nivel_g_com_f_ausente(self):
        entrada = ce.validar_entrada(ANO, "mt", 560.0, "G", "G", [ANO])
        r = ce.comparar(self.cdfs, entrada, comparar_outro_nivel=True)
        self.assertEqual(r.vizinho.grupo, "NV-F")
        self.assertFalse(r.vizinho.disponivel)  # F ficou abaixo do piso (DL-05, item 6)
        self.assertIsNone(r.prob_superioridade)

    def test_auditoria_da_escolaridade(self):
        e = self.resultado["escolaridade"][str(ANO)]
        self.assertEqual(e, {"elegiveis": 769, "com_nivel": 699, "sem_nivel_nao_sei_ou_vazio": 55,
                             "campo_invalido": 15, "pai_nao_sei": 105, "mae_nao_sei": 70})
        self.assertEqual(e["com_nivel"] + e["sem_nivel_nao_sei_ou_vazio"] + e["campo_invalido"], e["elegiveis"])
        self.assertEqual(self.resultado["verificacao"]["maior_divergencia_pp"], 0.0)

    def test_sem_identificador_no_artefato(self):
        colunas = [c[0] for c in duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{self.destino}')").fetchall()]
        self.assertEqual(colunas, ["ano", "area", "recorte", "grupo", "nota", "n", "abaixo", "total"])
        minimo = duckdb.sql(f"SELECT min(total) FROM read_parquet('{self.destino}')").fetchone()[0]
        self.assertGreaterEqual(minimo, PISO_GRUPO)
        self.assertEqual(duckdb.sql(f"SELECT DISTINCT recorte FROM read_parquet('{self.destino}')").fetchall(),
                         [("capital",)])

    def test_manifesto_sem_registro_individual(self):
        texto = self.manifesto.read_text(encoding="utf-8")
        self.assertNotIn("NU_INSCRICAO", texto)
        self.assertNotIn("230000000", texto)

    def test_divergencia_entre_sql_e_python_bloqueia_a_publicacao(self):
        destino = self.tmp / "defeito" / "dist_capital.parquet"
        original = ce.sql_artefato
        defeituoso = lambda fonte, piso: original(fonte, piso).replace(  # noqa: E731
            "CAST(n AS BIGINT) AS n", "CAST(n + 1 AS BIGINT) AS n")
        with mock.patch.object(ce, "sql_artefato", defeituoso), self.assertRaises(AssertionError):
            ce.etapa_capital(self.tmp / "trusted", destino, self.tmp / "defeito" / "m.json")
        self.assertFalse(destino.exists())

    def test_letra_no_nivel_errado_bloqueia_a_publicacao(self):
        # Simula B classificada como D no SQL: a contagem direta por letras tem de barrar.
        destino = self.tmp / "nivel" / "dist_capital.parquet"
        trocada = dict(ce.NIVEL_DA_LETRA, B="D")
        with mock.patch.object(ce, "NIVEL_DA_LETRA", trocada), self.assertRaises(AssertionError):
            ce.etapa_capital(self.tmp / "trusted", destino, self.tmp / "nivel" / "m.json")
        self.assertFalse(destino.exists())

    def test_piso_inalcancavel_nao_publica_nada(self):
        destino = self.tmp / "vazio" / "dist_capital.parquet"
        with self.assertRaises(ValueError):
            ce.etapa_capital(self.tmp / "trusted", destino, self.tmp / "vazio" / "m.json", piso=10_000)
        self.assertFalse(destino.exists())


class TestSqlIgualAoPython(unittest.TestCase):
    """Os dois caminhos (SQL do ETL e nivel_do_participante) dão o mesmo nível, em todas as combinações."""

    def test_todas_as_combinacoes_de_pai_e_mae(self):
        valores = [*"ABCDEFGH", "", None, "Z", "a", " g "]
        combinacoes = [(p, m) for p in valores for m in valores]
        con = duckdb.connect()
        con.execute("CREATE TABLE t (ano BIGINT, elegivel BOOLEAN, escolaridade_pai VARCHAR,"
                    " escolaridade_mae VARCHAR, nota_mt DOUBLE)")
        # Uma nota única por combinação: a linha de cada grupo no SQL identifica a combinação.
        con.executemany("INSERT INTO t VALUES (2022, TRUE, ?, ?, ?)",
                        [(p, m, float(i)) for i, (p, m) in enumerate(combinacoes)])
        grupo_por_nota = {}
        for _, grupo, nota, n in con.execute(ce.sql_contagens("t", "mt")).fetchall():
            self.assertEqual(n, 1)
            if grupo != ce.BRASIL:
                grupo_por_nota[nota] = grupo
        for i, (pai, mae) in enumerate(combinacoes):
            esperado = ce.nivel_do_participante(pai, mae)
            with self.subTest(pai=pai, mae=mae):
                self.assertEqual(grupo_por_nota.get(float(i)), None if esperado is None else ce.grupo_nivel(esperado))
        con.close()

    def test_brasil_inclui_quem_nao_tem_nivel(self):
        con = duckdb.connect()
        con.execute("CREATE TABLE t (ano BIGINT, elegivel BOOLEAN, escolaridade_pai VARCHAR,"
                    " escolaridade_mae VARCHAR, nota_cn DOUBLE, nota_ch DOUBLE, nota_lc DOUBLE,"
                    " nota_mt DOUBLE, nota_redacao DOUBLE)")
        linhas = [(2022, True, "D", "D", 500.0)] * 120
        linhas += [(2022, True, "H", "H", 900.0)] * 3 + [(2022, True, "Z", "D", 900.0)] * 2
        linhas += [(2022, True, None, None, 900.0)] * 2 + [(2022, False, "D", "D", 100.0)] * 5
        con.executemany("INSERT INTO t VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [(a, b, c, d, n, n, n, n, n) for a, b, c, d, n in linhas])
        cdfs, _, _ = ce.calcular_cdfs(con, "t")
        brasil = cdfs[(2022, "mt", ce.BRASIL)]
        self.assertEqual(brasil[-1][1] + brasil[-1][2], 127)  # 120 + 7 sem nível; treineiros fora
        nivel = cdfs[(2022, "mt", "NV-D")]
        self.assertEqual(nivel[-1][1] + nivel[-1][2], 120)
        con.close()


class TestConferirSomas(unittest.TestCase):
    def test_niveis_que_somam_menos_que_o_brasil_passam(self):
        ce.conferir_somas({(2022, "mt", ce.BRASIL): [(500.0, 300)], (2022, "mt", "NV-D"): [(500.0, 200)]})

    def test_niveis_que_somam_igual_ao_brasil_passam(self):
        ce.conferir_somas({(2022, "mt", ce.BRASIL): [(500.0, 300)], (2022, "mt", "NV-D"): [(500.0, 100)],
                           (2022, "mt", "NV-E"): [(500.0, 200)]})

    def test_participante_contado_em_dois_niveis_levanta(self):
        with self.assertRaises(AssertionError):
            ce.conferir_somas({(2022, "mt", ce.BRASIL): [(500.0, 300)], (2022, "mt", "NV-D"): [(500.0, 200)],
                               (2022, "mt", "NV-E"): [(500.0, 150)]})

    def test_nivel_com_nota_que_nao_existe_no_brasil_levanta(self):
        with self.assertRaises(AssertionError):
            ce.conferir_somas({(2022, "mt", ce.BRASIL): [(500.0, 300)], (2022, "mt", "NV-D"): [(510.0, 10)]})


class TestModuloIndependente(unittest.TestCase):
    def test_exibir_percentil_e_o_compartilhado(self):
        self.assertIs(ce.exibir_percentil, est.exibir_percentil)  # DL-05, item 13: importado, sem copiar

    def test_nao_define_a_regra_de_limite_por_conta_propria(self):
        texto = (RAIZ / "scripts" / "capital_escolar.py").read_text(encoding="utf-8")
        self.assertNotIn("def exibir_percentil", texto)
        self.assertNotIn("def limites_exibicao", texto)


# ================================================== INTERFACE (STREAMLIT)


def escrever_artefato(cdfs: dict, arquivo: Path) -> None:
    linhas = [(ano, area, "capital", g, nota, n, abaixo, d[-1][1] + d[-1][2])
              for (ano, area, g), d in cdfs.items() for nota, n, abaixo in d]
    con = duckdb.connect()
    con.execute("CREATE TABLE e (ano BIGINT, area VARCHAR, recorte VARCHAR, grupo VARCHAR,"
                " nota DOUBLE, n BIGINT, abaixo BIGINT, total BIGINT)")
    con.executemany("INSERT INTO e VALUES (?, ?, ?, ?, ?, ?, ?, ?)", linhas)
    con.execute(f"COPY e TO '{arquivo}' (FORMAT parquet)")
    con.close()


@unittest.skipIf(AppTest is None, "streamlit nao instalado")
class TestPagina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.arquivo = Path(cls.tmp.name) / "dist_capital.parquet"
        escrever_artefato(cdfs_de_teste(), cls.arquivo)
        os.environ["RADAR_DIST_CAPITAL"] = str(cls.arquivo)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("RADAR_DIST_CAPITAL", None)
        cls.tmp.cleanup()

    def abrir(self) -> AppTest:
        import streamlit as st
        st.cache_data.clear()  # o cache é global ao processo; cada teste pode usar outro artefato
        at = AppTest.from_file(str(PAGINA), default_timeout=30)
        at.run()
        self.assertFalse(at.exception)
        return at

    @staticmethod
    def campo(at, rotulo):
        return next(c for c in at.number_input if c.label == rotulo)

    @staticmethod
    def responsaveis(at, pai, mae):
        next(s for s in at.selectbox if s.label.startswith("Até que série seu pai")).set_value(pai)
        next(s for s in at.selectbox if s.label.startswith("Até que série sua mãe")).set_value(mae)

    def test_cenario_padrao_na_tela(self):
        at = self.abrir()
        self.responsaveis(at, "D", "D")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m.label for m in at.metric],
                         ["Responsáveis com ensino fundamental completo", "Brasil"])
        self.assertEqual([m.value for m in at.metric], ["50,0%", "27,1%"])
        self.assertFalse(any("pontos percentuais" in m.value for m in at.markdown))  # sem o outro nível

    def test_outro_nivel_comeca_desligado_e_aparece_quando_ligado(self):
        at = self.abrir()
        self.assertFalse(at.checkbox[0].value)  # DL-05, item 5: opcional
        self.responsaveis(at, "D", "D")
        self.campo(at, "Matemática").set_value(500.0)
        at.checkbox[0].check()
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m.value for m in at.metric], ["50,0%", "16,7%", "27,1%"])
        self.assertTrue(any("33,3 pontos percentuais acima" in m.value for m in at.markdown))
        self.assertTrue(any("22,2%" in m.value for m in at.markdown))  # 2 / 9

    def test_vizinho_em_limite_esconde_a_diferenca(self):
        at = self.abrir()
        self.responsaveis(at, "G", "A")
        self.campo(at, "Matemática").set_value(600.0)
        at.checkbox[0].check()
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[1].value, "acima de 50,0%")
        self.assertFalse(any("pontos percentuais" in m.value for m in at.markdown))
        self.assertTrue(any("87,5%" in m.value for m in at.markdown))  # superioridade continua
        self.assertTrue(any("abaixo" in m.value for m in at.markdown))  # G compara com o nível de baixo

    def test_nao_sei_nos_dois_mostra_so_a_posicao_nacional(self):
        at = self.abrir()
        self.responsaveis(at, "H", "H")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m.label for m in at.metric], ["Brasil"])
        self.assertTrue(any("Não sei" in c.value for c in at.caption))

    def test_nivel_vizinho_abaixo_do_piso_vira_grupo_insuficiente(self):
        escrever_artefato(cdfs_de_teste(sem=("E",)), self.arquivo)
        try:
            at = self.abrir()
            self.responsaveis(at, "D", "D")
            self.campo(at, "Matemática").set_value(500.0)
            at.checkbox[0].check()
            at.button[0].click().run()
            self.assertFalse(at.exception)
            self.assertTrue(any("grupo insuficiente" in i.value for i in at.info))
            self.assertEqual(at.metric[0].value, "50,0%")
        finally:
            escrever_artefato(cdfs_de_teste(), self.arquivo)

    def test_sem_escolaridade_pede_os_dois_responsaveis(self):
        at = self.abrir()
        next(s for s in at.selectbox if s.label.startswith("Até que série seu pai")).set_value("D")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertIn("dos dois responsáveis", at.warning[0].value)

    def test_sem_nota_pede_ao_menos_uma(self):
        at = self.abrir()
        self.responsaveis(at, "D", "D")
        at.button[0].click().run()
        self.assertIn("ao menos uma nota", at.warning[0].value)

    def test_redacao_invalida_mostra_erro_sem_quebrar(self):
        at = self.abrir()
        self.responsaveis(at, "D", "D")
        self.campo(at, "Redação").set_value(610.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertIn("múltipla de 20", at.error[0].value)

    def test_texto_neutro_sem_causalidade_e_sem_ranking_de_pessoas(self):
        texto = PAGINA.read_text(encoding="utf-8").lower()
        self.assertIn("não indica que a escolaridade", texto)
        for proibida in ("ranking de pessoas", "melhores", "piores", "capacidade"):
            self.assertNotIn(proibida, texto)

    def test_dados_digitados_nao_vao_para_a_url(self):
        at = self.abrir()
        self.responsaveis(at, "D", "E")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertEqual(dict(at.query_params), {})

    def test_artefato_ausente(self):
        os.environ["RADAR_DIST_CAPITAL"] = str(Path(self.tmp.name) / "nao_existe.parquet")
        try:
            at = AppTest.from_file(str(PAGINA), default_timeout=30)
            at.run()
            self.assertIn("Artefato do módulo ausente", at.error[0].value)
        finally:
            os.environ["RADAR_DIST_CAPITAL"] = str(self.arquivo)


if __name__ == "__main__":
    unittest.main()
