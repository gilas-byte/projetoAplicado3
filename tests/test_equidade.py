"""Testes do módulo Equidade socioeconômica (autor: Samuel Silva de Rezende).

Cobrem as regras de negócio da DL-03 (docs/decisoes), a validação da entrada
do usuário, os casos de erro (faixa ausente, faixa abaixo do piso, contraste
vazio, entradas inválidas) e a agregação de ponta a ponta com microdados
sintéticos, conferida contra um cálculo independente em Python puro.

Rodam sem os microdados do INEP:
  ./.venv/bin/python -m unittest tests/test_equidade.py -v
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

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

import equidade as eq  # noqa: E402
import etl  # noqa: E402
from colunas import ANOS, PISO_GRUPO  # noqa: E402
from estatistica import construir_acumulada  # noqa: E402
from test_etl import ANO, escrever_csv, linha_base  # noqa: E402

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None

PAGINA = RAIZ / "app" / "pages" / "1_Equidade_socioeconomica.py"


def cdf(*pares: tuple[float, int]):
    return construir_acumulada([(float(nota), n) for nota, n in pares])


def percentil_bruto(notas: list[float], nota: float) -> float:
    """Posto médio direto sobre a lista de notas, sem estrutura agregada."""
    return (sum(x < nota for x in notas) + sum(x == nota for x in notas) / 2) / len(notas) * 100


# =========================================================== REGRAS DA Q006


class TestFaixasQ006(unittest.TestCase):
    def test_cada_alternativa_em_exatamente_uma_faixa(self):
        alternativas = [a for f in eq.FAIXAS for a in f.alternativas]
        self.assertEqual(sorted(alternativas), list("ABCDEFGHIJKLMNOPQ"))
        self.assertEqual(len(alternativas), len(set(alternativas)))

    def test_faixas_contiguas_em_salarios_minimos(self):
        for anterior, atual in zip(eq.FAIXAS, eq.FAIXAS[1:]):
            self.assertEqual(anterior.sm_max, atual.sm_min)
        self.assertEqual(eq.FAIXAS[0].sm_min, 0)
        self.assertIsNone(eq.FAIXAS[-1].sm_max)

    def test_faixas_coincidem_com_o_piso_de_renda_do_etl(self):
        # PISO_RENDA_SM (etl.py) é a fonte da conversão Q006 -> salários
        # mínimos; cada alternativa precisa cair dentro da sua faixa.
        for alternativa, piso in etl.PISO_RENDA_SM.items():
            faixa = eq.FAIXA_POR_CODIGO[eq.faixa_de_q006(alternativa)]
            self.assertGreaterEqual(piso, faixa.sm_min, alternativa)
            if faixa.sm_max is not None:
                self.assertLess(piso, faixa.sm_max, alternativa)

    def test_exemplos(self):
        self.assertEqual(eq.faixa_de_q006("A"), "R1")  # nenhuma renda
        self.assertEqual(eq.faixa_de_q006("B"), "R1")
        self.assertEqual(eq.faixa_de_q006("H"), "R4")
        self.assertEqual(eq.faixa_de_q006("M"), "R5")
        self.assertEqual(eq.faixa_de_q006("N"), "R6")
        self.assertEqual(eq.faixa_de_q006(" q "), "R6")

    def test_resposta_ausente_nao_tem_faixa(self):
        self.assertIsNone(eq.faixa_de_q006(None))
        self.assertIsNone(eq.faixa_de_q006(""))
        self.assertIsNone(eq.faixa_de_q006("   "))

    def test_alternativa_invalida(self):
        for valor in ["R", "Z", "AB", "1", 3, 2.0]:
            with self.subTest(valor=valor), self.assertRaises(eq.EntradaInvalida):
                eq.faixa_de_q006(valor)

    def test_contraste_e_o_topo_de_renda(self):
        self.assertEqual(eq.CONTRASTE_FAIXA, eq.FAIXAS[-1].codigo)
        self.assertEqual(eq.CONTRASTE_TIPO_ESCOLA, 3)


class TestOpcoesDoQuestionario(unittest.TestCase):
    def test_texto_oficial_de_cada_edicao(self):
        for ano in ANOS:
            with self.subTest(ano=ano):
                opcoes = eq.opcoes_q006(ano)
                self.assertEqual([c for c, _ in opcoes], list("ABCDEFGHIJKLMNOPQ"))
        textos = dict(eq.opcoes_q006(2022))
        self.assertEqual(textos["B"], "Até R$ 1.212,00")
        self.assertEqual(textos["Q"], "Acima de R$ 24.240,00")
        self.assertEqual(dict(eq.opcoes_q006(2019))["B"], "Até R$ 998,00")

    def test_edicao_sem_dicionario(self):
        with self.assertRaises(eq.EntradaInvalida):
            eq.opcoes_q006(2015)

    def test_dicionario_sem_alternativa(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "dicionario_2022.json").write_text(
            '{"x": [{"variavel": "Q006", "categorias": {"A": "Nenhuma"}}]}', encoding="utf-8")
        with self.assertRaises(eq.EntradaInvalida):
            eq.opcoes_q006(2022, tmp)


# =================================================== VALIDAÇÃO DA ENTRADA


class TestValidacaoEntrada(unittest.TestCase):
    ANOS = [2021, 2022]

    def validar(self, **campos):
        base = dict(ano=2022, area="mt", nota=650.0, alternativa="C", anos_disponiveis=self.ANOS)
        base.update(campos)
        return eq.validar_entrada(**base)

    def test_entrada_valida_normalizada(self):
        e = self.validar(alternativa=" d ", nota=650)
        self.assertEqual((e.ano, e.area, e.nota, e.alternativa, e.faixa), (2022, "mt", 650.0, "D", "R2"))

    def test_limites_de_nota_aceitos(self):
        self.assertEqual(self.validar(nota=0.0).nota, 0.0)
        self.assertEqual(self.validar(nota=1000.0).nota, 1000.0)
        self.assertEqual(self.validar(nota=612.3).nota, 612.3)
        self.assertEqual(self.validar(area="redacao", nota=620.0).nota, 620.0)

    def test_erros(self):
        casos = {
            "edição indisponível": dict(ano=2019),
            "edição como texto": dict(ano="2022"),
            "edição booleana": dict(ano=True),
            "área inexistente": dict(area="fisica"),
            "nota ausente": dict(nota=None),
            "nota em texto": dict(nota="650"),
            "nota booleana": dict(nota=True),
            "nota NaN": dict(nota=math.nan),
            "nota infinita": dict(nota=math.inf),
            "nota negativa": dict(nota=-0.1),
            "nota acima de 1000": dict(nota=1000.1),
            "duas casas decimais": dict(nota=650.25),
            "redação fora do passo de 20": dict(area="redacao", nota=610.0),
            "renda ausente": dict(alternativa=None),
            "renda vazia": dict(alternativa=""),
            "renda inexistente": dict(alternativa="Z"),
        }
        for nome, campos in casos.items():
            with self.subTest(nome), self.assertRaises(eq.EntradaInvalida):
                self.validar(**campos)

    def test_mensagem_legivel_para_a_interface(self):
        with self.assertRaises(eq.EntradaInvalida) as ctx:
            self.validar(area="redacao", nota=610.0)
        self.assertIn("múltipla de 20", str(ctx.exception))


# ============================================================ COMPARAÇÃO


class TestComparacao(unittest.TestCase):
    """Valores esperados calculados à mão.

    Faixa R2: 50 notas 400, 50 notas 500, 50 notas 600 (N = 150).
    Contraste: 50 de cada em 500, 600, 700, 800 (N = 200).
    """

    def setUp(self):
        self.cdfs = {
            (2022, "mt", "R2"): cdf((400, 50), (500, 50), (600, 50)),
            (2022, "mt", eq.CONTRASTE): cdf((500, 50), (600, 50), (700, 50), (800, 50)),
        }

    def entrada(self, nota=500.0, alternativa="C", area="mt"):
        return eq.validar_entrada(2022, area, nota, alternativa, [2022])

    def test_dois_cenarios(self):
        r = eq.comparar(self.cdfs, self.entrada())
        # Real: (50 abaixo + 50/2 iguais) / 150 = 50%.
        self.assertAlmostEqual(r.real.percentil, 50.0)
        # Simulado: (0 + 50/2) / 200 = 12,5%.
        self.assertAlmostEqual(r.simulado.percentil, 12.5)
        self.assertAlmostEqual(r.diferenca_pp, 37.5)
        self.assertEqual((r.real.n, r.simulado.n), (150, 200))

    def test_medidas_do_motor(self):
        r = eq.comparar(self.cdfs, self.entrada())
        self.assertAlmostEqual(r.real.media, 500.0)
        self.assertAlmostEqual(r.real.desvio, math.sqrt(2 * 50 * 100**2 / 150))
        self.assertEqual(r.real.mediana, 500.0)
        self.assertAlmostEqual(r.real.z, 0.0)
        self.assertAlmostEqual(r.simulado.media, 650.0)
        # Mediana inferior (DL-01): N = 200, 100 notas <= 600; a média das
        # centrais daria 650.
        self.assertEqual(r.simulado.mediana, 600.0)
        self.assertAlmostEqual(r.simulado.z, (500 - 650) / math.sqrt(12500))

    def test_probabilidade_de_superioridade(self):
        r = eq.comparar(self.cdfs, self.entrada())
        # 500 x 500: 50*50 empates (meio ponto); 600 x 500: 50*50 vitórias;
        # 600 x 600: 50*50 empates. (1250 + 2500 + 1250) / (150 * 200).
        self.assertAlmostEqual(r.prob_superioridade, 5000 / 30000)

    def test_faixa_ausente_nao_quebra(self):
        r = eq.comparar(self.cdfs, self.entrada(alternativa="I"))  # R5 não existe no artefato
        self.assertFalse(r.real.disponivel)
        self.assertIn("grupo insuficiente", r.real.motivo)
        self.assertTrue(r.simulado.disponivel)
        self.assertIsNone(r.diferenca_pp)
        self.assertIsNone(r.prob_superioridade)

    def test_contraste_vazio_nao_quebra(self):
        del self.cdfs[(2022, "mt", eq.CONTRASTE)]
        r = eq.comparar(self.cdfs, self.entrada())
        self.assertTrue(r.real.disponivel)
        self.assertFalse(r.simulado.disponivel)
        self.assertIsNone(r.diferenca_pp)

    def test_area_sem_nenhum_grupo(self):
        r = eq.comparar(self.cdfs, self.entrada(area="redacao", nota=600.0))
        self.assertFalse(r.real.disponivel or r.simulado.disponivel)

    def test_nota_fora_da_distribuicao(self):
        r = eq.comparar(self.cdfs, self.entrada(nota=1000.0))
        self.assertEqual((r.real.percentil, r.simulado.percentil), (100.0, 100.0))
        r = eq.comparar(self.cdfs, self.entrada(nota=0.0))
        self.assertEqual((r.real.percentil, r.simulado.percentil), (0.0, 0.0))

    def test_desvio_zero_vira_aviso(self):
        self.cdfs[(2022, "mt", "R2")] = cdf((500, 150))
        r = eq.comparar(self.cdfs, self.entrada())
        self.assertIsNone(r.real.z)
        self.assertTrue(any("indefinido" in a for a in r.avisos))

    def test_aviso_quando_a_faixa_e_a_do_contraste(self):
        self.cdfs[(2022, "mt", "R6")] = cdf((700, 150))
        r = eq.comparar(self.cdfs, self.entrada(alternativa="P"))
        self.assertTrue(any("mesma do grupo de contraste" in a for a in r.avisos))

    def test_formatacao_da_exibicao(self):
        self.assertEqual(eq.formatar_percentil(12.5), "12,5%")
        self.assertEqual(eq.formatar_percentil(99.96), "100,0%")
        self.assertEqual(eq.formatar_z(-1.3416), "-1,34")
        self.assertEqual(eq.formatar_z(None), "indefinido")


# ============================================ AGREGAÇÃO DE PONTA A PONTA


class TestAgregacao(unittest.TestCase):
    """RAW sintético -> TRUSTED (ETL real) -> dist_equidade, contra cálculo bruto.

    Composição (todos com nota nas cinco áreas):
      R2 (Q006 = C, D): 300 elegíveis, notas aleatórias com empates
      R3 (Q006 = E):     99 elegíveis + 1 treineiro       -> abaixo do piso
      R4 (Q006 = G, H): exatamente 100 elegíveis          -> no limite do piso
      R6 privada (TP_ESCOLA = 3, Q006 = N..Q): 140        -> contraste
      R6 sem escola declarada (TP_ESCOLA = 1, Q006 = Q): 30 -> só na faixa R6
      R6 pública (TP_ESCOLA = 2, Q006 = O): 10            -> só na faixa R6
      Q006 vazia: 40; Q006 inválida ("Z"): 5              -> fora do módulo
    """

    AREAS = {"cn": "NU_NOTA_CN", "ch": "NU_NOTA_CH", "lc": "NU_NOTA_LC",
             "mt": "NU_NOTA_MT", "redacao": "NU_NOTA_REDACAO"}

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        rng = random.Random(1106)
        cls.registros: list[dict] = []
        linhas = []

        def pessoa(q006, escola, media, elegivel=True):
            linha = linha_base()
            linha["NU_INSCRICAO"] = str(220000000000 + len(linhas))
            linha["Q006"], linha["TP_ESCOLA"] = q006, str(escola)
            if not elegivel:
                linha["IN_TREINEIRO"] = "1"
            notas = {}
            for area, coluna in cls.AREAS.items():
                nota = round(min(max(rng.gauss(media, 70), 0.0), 1000.0), 1)
                if area == "redacao":
                    nota = float(round(nota / 40) * 40)
                else:
                    nota = round(nota / 5, 0) * 5  # passos de 5 pontos: muitos empates
                linha[coluna] = f"{nota}"
                notas[area] = nota
            linhas.append(linha)
            cls.registros.append({"q006": q006, "escola": escola, "elegivel": elegivel, **notas})

        for i in range(300):
            pessoa("CD"[i % 2], 2, 500)
        for _ in range(99):
            pessoa("E", 2, 540)
        pessoa("E", 2, 540, elegivel=False)
        for i in range(100):
            pessoa("GH"[i % 2], 2, 580)
        for i in range(140):
            pessoa("NOPQ"[i % 4], 3, 680)
        for _ in range(30):
            pessoa("Q", 1, 640)
        for _ in range(10):
            pessoa("O", 2, 620)
        for _ in range(40):
            pessoa("", 2, 520)
        for _ in range(5):
            pessoa("Z", 2, 520)

        csv = cls.tmp / "microdados.csv"
        escrever_csv(csv, linhas)
        con = duckdb.connect()
        etl.gerar_trusted(con, csv, ANO, cls.tmp / "trusted")
        con.close()
        cls.destino = cls.tmp / "analytics" / "dist_equidade.parquet"
        cls.manifesto = cls.tmp / "analytics" / "_manifesto_equidade.json"
        cls.resultado = eq.etapa_equidade(cls.tmp / "trusted", cls.destino, cls.manifesto)
        cls.cdfs = eq.carregar(cls.destino)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def notas(self, area: str, grupo: str) -> list[float]:
        """Notas do grupo pela definição da DL-03, direto dos registros."""
        def pertence(r):
            if not r["elegivel"] or r["q006"] not in eq.FAIXA_DA_ALTERNATIVA:
                return False
            if grupo == eq.CONTRASTE:
                return eq.FAIXA_DA_ALTERNATIVA[r["q006"]] == "R6" and r["escola"] == 3
            return eq.FAIXA_DA_ALTERNATIVA[r["q006"]] == grupo
        return [r[area] for r in self.registros if pertence(r)]

    def test_grupos_publicados_e_suprimidos(self):
        grupos = {g for (_, area, g) in self.cdfs if area == "mt"}
        self.assertEqual(grupos, {"R2", "R4", "R6", eq.CONTRASTE})
        self.assertIn(f"{ANO}/mt/R3", self.resultado["grupos"]["suprimidos_abaixo_do_piso"])

    def test_piso_no_limite(self):
        # 100 participantes: exatamente o piso, então o grupo é publicado.
        self.assertEqual(sum(n for _, n, _ in self.cdfs[(ANO, "mt", "R4")]), PISO_GRUPO)

    def test_tamanhos_dos_grupos(self):
        total = lambda g: sum(n for _, n, _ in self.cdfs[(ANO, "mt", g)])  # noqa: E731
        self.assertEqual(total("R2"), 300)
        self.assertEqual(total("R6"), 180)  # privada + não declarou + pública
        self.assertEqual(total(eq.CONTRASTE), 140)  # só quem declarou escola privada

    def test_percentil_igual_ao_calculo_bruto(self):
        for (ano, area, grupo), distribuicao in self.cdfs.items():
            notas = self.notas(area, grupo)
            for nota in {min(notas), max(notas), 300.0, 500.0, 512.5, 640.0, 680.0, 1000.0}:
                with self.subTest(area=area, grupo=grupo, nota=nota):
                    obtido = eq._cenario(self.cdfs, ano, area, grupo, "", nota).percentil
                    self.assertAlmostEqual(obtido, percentil_bruto(notas, nota), places=9)

    def test_superioridade_igual_a_contagem_de_pares(self):
        for area in self.AREAS:
            a, b = self.notas(area, "R2"), self.notas(area, eq.CONTRASTE)
            esperado = sum((x > y) + 0.5 * (x == y) for x in a for y in b) / (len(a) * len(b))
            entrada = eq.validar_entrada(ANO, area, 500.0, "C", [ANO])
            with self.subTest(area=area):
                self.assertAlmostEqual(eq.comparar(self.cdfs, entrada).prob_superioridade, esperado, places=12)

    def test_auditoria_da_q006(self):
        q = self.resultado["q006"][str(ANO)]
        self.assertEqual(q["q006_ausente"], 40)
        self.assertEqual(q["q006_invalida"], 5)
        self.assertEqual(self.resultado["verificacao"]["maior_divergencia_pp"], 0.0)

    def test_sem_identificador_no_artefato(self):
        colunas = [c[0] for c in duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{self.destino}')").fetchall()]
        self.assertEqual(colunas, ["ano", "area", "recorte", "grupo", "nota", "n", "abaixo", "total"])

    def test_piso_inalcancavel_nao_publica_nada(self):
        destino = self.tmp / "vazio" / "dist_equidade.parquet"
        with self.assertRaises(ValueError):
            eq.etapa_equidade(self.tmp / "trusted", destino, self.tmp / "vazio" / "m.json", piso=10_000)
        self.assertFalse(destino.exists())


# ================================================== INTERFACE (STREAMLIT)


@unittest.skipIf(AppTest is None, "streamlit nao instalado")
class TestPagina(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        arquivo = Path(cls.tmp.name) / "dist_equidade.parquet"
        grupos = {
            "R2": cdf((400, 50), (500, 50), (600, 50)),
            eq.CONTRASTE: cdf((500, 50), (600, 50), (700, 50), (800, 50)),
        }
        linhas = [(2022, "mt", "renda", g, nota, n, abaixo, sum(m for _, m, _ in d))
                  for g, d in grupos.items() for nota, n, abaixo in d]
        con = duckdb.connect()
        con.execute("CREATE TABLE e (ano BIGINT, area VARCHAR, recorte VARCHAR, grupo VARCHAR,"
                    " nota DOUBLE, n BIGINT, abaixo BIGINT, total BIGINT)")
        con.executemany("INSERT INTO e VALUES (?, ?, ?, ?, ?, ?, ?, ?)", linhas)
        con.execute(f"COPY e TO '{arquivo}' (FORMAT parquet)")
        con.close()
        os.environ["RADAR_DIST_EQUIDADE"] = str(arquivo)

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("RADAR_DIST_EQUIDADE", None)
        cls.tmp.cleanup()

    def abrir(self) -> AppTest:
        at = AppTest.from_file(str(PAGINA), default_timeout=30)
        at.run()
        self.assertFalse(at.exception)
        return at

    @staticmethod
    def campo(at, rotulo):
        return next(c for c in at.number_input if c.label == rotulo)

    def renda(self, at, codigo):
        next(s for s in at.selectbox if s.label.startswith("Qual é a renda")).set_value(codigo)

    def test_dois_cenarios_na_tela(self):
        at = self.abrir()
        self.renda(at, "C")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual([m.value for m in at.metric], ["50,0%", "12,5%"])
        self.assertTrue(any("37,5 pontos percentuais abaixo" in m.value for m in at.markdown))

    def test_sem_renda_pede_a_renda(self):
        at = self.abrir()
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertIn("renda familiar", at.warning[0].value)

    def test_sem_nota_pede_ao_menos_uma(self):
        at = self.abrir()
        self.renda(at, "C")
        at.button[0].click().run()
        self.assertIn("ao menos uma nota", at.warning[0].value)

    def test_faixa_abaixo_do_piso_vira_grupo_insuficiente(self):
        at = self.abrir()
        self.renda(at, "K")  # R5 não foi publicada no artefato
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("grupo insuficiente" in i.value for i in at.info))

    def test_redacao_invalida_mostra_erro_sem_quebrar(self):
        at = self.abrir()
        self.renda(at, "C")
        self.campo(at, "Redação").set_value(610.0)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertIn("múltipla de 20", at.error[0].value)

    def test_dados_digitados_nao_vao_para_a_url(self):
        at = self.abrir()
        self.renda(at, "C")
        self.campo(at, "Matemática").set_value(500.0)
        at.button[0].click().run()
        self.assertEqual(dict(at.query_params), {})

    def test_artefato_ausente(self):
        anterior = os.environ["RADAR_DIST_EQUIDADE"]
        os.environ["RADAR_DIST_EQUIDADE"] = str(Path(self.tmp.name) / "nao_existe.parquet")
        try:
            at = AppTest.from_file(str(PAGINA), default_timeout=30)
            at.run()
            self.assertIn("Artefato do módulo ausente", at.error[0].value)
        finally:
            os.environ["RADAR_DIST_EQUIDADE"] = anterior


if __name__ == "__main__":
    unittest.main()
