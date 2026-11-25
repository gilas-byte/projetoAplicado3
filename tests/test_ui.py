"""Testes das pecas visuais de app/ui.py (so apresentacao, sem dados reais)."""

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "app"))

try:
    import ui
except ImportError:  # pragma: no cover
    ui = None


@unittest.skipIf(ui is None, "streamlit/plotly nao instalados")
class TestUi(unittest.TestCase):
    def anel(self, texto):
        with mock.patch.object(ui, "_iframe") as frame:
            ui.anel(texto, "Matematica | nota 640,0", "descricao")
        return frame.call_args[0][0]

    def test_anel_anima_so_o_valor_do_texto(self):
        html = self.anel("58,3%")
        self.assertIn("const ALVO=58.3,FINAL=\"58,3%\",ANIMA=true", html)
        self.assertIn("<small>percentil</small>", html)
        self.assertNotIn("acima de", html)

    def test_anel_em_limite_mostra_prefixo_no_rotulo_e_numero_no_centro(self):
        html = self.anel("abaixo de 0,1%")
        self.assertIn("<small>abaixo de</small>", html)
        self.assertIn("const ALVO=0.1,FINAL=\"0,1%\",ANIMA=true", html)

    def test_anel_texto_fora_do_formato_fica_parado(self):
        html = self.anel("sem formato")
        self.assertIn("ANIMA=false", html)
        self.assertIn("FINAL=\"sem formato\"", html)

    def test_anel_escapa_titulo_e_descricao(self):
        with mock.patch.object(ui, "_iframe") as frame:
            ui.anel("50,0%", "<script>x</script>", "<b>y</b>")
        html = frame.call_args[0][0]
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;x", html)
        self.assertIn("&lt;b&gt;y", html)

    def test_grupos_sem_pct_nao_desenha_barra(self):
        with mock.patch.object(ui.st, "html") as html:
            ui.grupos("t", [dict(rotulo="a", valor="acima de 99,9%", cor=ui.COR_PROPRIO, pct=None),
                            dict(rotulo="b", valor="50,0%", cor=ui.COR_BRASIL, pct=50.0)])
        corpo = html.call_args[0][0]
        self.assertEqual(corpo.count('class="r-bar"'), 1)
        self.assertIn("--w:50.0%", corpo)

    def test_grupos_escapa_texto(self):
        with mock.patch.object(ui.st, "html") as html:
            ui.grupos("<i>t</i>", [dict(rotulo="<b>a</b>", valor="1", cor="#fff", pct=None)])
        self.assertNotIn("<b>a</b>", html.call_args[0][0])

    def test_paletas_tem_as_mesmas_chaves(self):
        self.assertEqual(set(ui._PALETAS["dark"]), set(ui._PALETAS["light"]))

    def test_tema_padrao_e_claro_fora_de_uma_sessao(self):
        self.assertEqual(ui.tema_atual(), "light")

    def test_tema_escuro_troca_as_cores_do_anel_e_do_grafico(self):
        with mock.patch.object(ui, "tema_atual", return_value="dark"):
            escuro = self.anel("58,3%")
            fig = ui.estilo_grafico(ui.go.Figure())
        self.assertIn(ui._PALETAS["dark"]["tx"], escuro)
        self.assertNotIn(ui._PALETAS["light"]["bg"], escuro)
        self.assertEqual(fig.layout.font.color, ui._PALETAS["dark"]["tx"])  # eixos em tom forte (16/11/2026)
        self.assertNotIn("text-shadow:none", escuro)
        claro = self.anel("58,3%")  # sem tema informado, o padrao e o claro
        self.assertIn("text-shadow:none", claro)

    def test_estilo_grafico_preserva_cor_de_anotacao_ja_definida(self):
        fig = ui.go.Figure()
        fig.add_annotation(text="sem cor", x=0, y=0)
        fig.add_annotation(text="com cor", x=1, y=1, font={"color": ui.COR_NOTA})
        ui.estilo_grafico(fig)
        sem_cor, com_cor = fig.layout.annotations
        self.assertEqual(sem_cor.font.color, ui._PALETAS["light"]["tx"])
        self.assertEqual(com_cor.font.color, ui.COR_NOTA)

    def test_alternador_so_troca_quando_o_usuario_mexe(self):
        ui.st.session_state.pop("_r_troca", None)
        with mock.patch.object(ui, "_iframe") as frame, mock.patch.object(ui.st, "toggle", return_value=True), \
                mock.patch.object(ui.st, "sidebar"):
            ui._alternador()  # tema ainda escuro no servidor, toggle recem criado: nao pode forcar nada
        self.assertIn("const forcar = null;", frame.call_args[0][0])
        ui._pedir_troca()
        with mock.patch.object(ui, "_iframe") as frame, mock.patch.object(ui.st, "toggle", return_value=True), \
                mock.patch.object(ui.st, "sidebar"):
            ui._alternador()
        self.assertIn('const forcar = "Dark";', frame.call_args[0][0])
        self.assertNotIn("_r_troca", ui.st.session_state)



def _luminancia(cor: str) -> float:
    r, g, b = (int(cor.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contraste(a: str, b: str) -> float:
    """Razão de contraste da WCAG 2.1 entre duas cores hexadecimais."""
    claro, escuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


@unittest.skipIf(ui is None, "streamlit/plotly nao instalados")
class TestContraste(unittest.TestCase):
    """Acessibilidade das cores nos dois temas (WCAG 2.1, criterios 1.4.3 e 1.4.11)."""

    def test_cores_de_papel_passam_de_3_para_1_nos_dois_temas(self):
        for nome in ("COR_PROPRIO", "COR_VIZINHO", "COR_BRASIL", "COR_NOTA"):
            for tema, paleta in ui._PALETAS.items():
                for fundo in ("bg", "surf"):
                    with self.subTest(cor=nome, tema=tema, fundo=fundo):
                        self.assertGreaterEqual(contraste(getattr(ui, nome), paleta[fundo]), 3.0)

    def test_nenhuma_cor_de_dado_e_cinza(self):
        """Pedido do PO (16/11/2026): graficos sem tons de cinza. Saturacao HSL de pelo menos 40%."""
        import colorsys

        def saturacao(cor):
            r, g, b = (int(cor.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
            return colorsys.rgb_to_hls(r, g, b)[2]

        cores = {nome: getattr(ui, nome) for nome in ("COR_PROPRIO", "COR_VIZINHO", "COR_BRASIL", "COR_NOTA")}
        cores.update({f"fraco1 ({tema})": paleta["fraco1"] for tema, paleta in ui._PALETAS.items()})
        for nome, cor in cores.items():
            with self.subTest(cor=nome):
                self.assertGreaterEqual(saturacao(cor), 0.4)

    def test_textos_principal_e_secundario_em_tom_forte(self):
        """Texto principal e secundario com pelo menos 7:1 (nivel AAA) nos dois temas."""
        for tema, paleta in ui._PALETAS.items():
            for cor in ("tx", "mu"):
                for fundo in ("bg", "surf"):
                    with self.subTest(tema=tema, cor=cor, fundo=fundo):
                        self.assertGreaterEqual(contraste(paleta[cor], paleta[fundo]), 7.0)

    def test_texto_ciano_passa_de_4_e_meio_para_1(self):
        for tema, paleta in ui._PALETAS.items():
            for fundo in ("bg", "surf"):
                with self.subTest(tema=tema, fundo=fundo):
                    self.assertGreaterEqual(contraste(paleta["ciano"], paleta[fundo]), 4.5)

    def test_trilho_e_tom_claro_da_propria_cor(self):
        with mock.patch.object(ui, "tema_atual", return_value="light"):
            self.assertEqual(ui.clarear("#000000", 1.0), ui._PALETAS["light"]["bg"])
            self.assertEqual(ui.clarear("#1375ff", 0.0), "#1375ff")

    def test_texto_branco_do_botao(self):
        for tema, paleta in ui._PALETAS.items():
            for fundo in ("azul", "btn_hover"):
                with self.subTest(tema=tema, fundo=fundo):
                    self.assertGreaterEqual(contraste("#ffffff", paleta[fundo]), 4.5)


@unittest.skipIf(ui is None, "streamlit/plotly nao instalados")
class TestRodape(unittest.TestCase):
    def setUp(self):
        ui._ler_manifesto.cache_clear()

    def tearDown(self):
        ui._ler_manifesto.cache_clear()

    def test_le_data_e_commit_do_manifesto(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "_manifesto_publicacao.json"
            caminho.write_text(json.dumps({"auditado_em_utc": "2026-11-16T17:30:00+00:00",
                                           "versao_codigo_git": "abcdef1234567"}), encoding="utf-8")
            self.assertEqual(ui._versao_dos_dados(caminho), ("16/11/2026", "abcdef1"))

    def test_nova_auditoria_troca_o_rodape_sem_reiniciar(self):
        import json
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "_manifesto_publicacao.json"
            caminho.write_text(json.dumps({"auditado_em_utc": "2026-11-16T17:30:00+00:00",
                                           "versao_codigo_git": "abcdef1"}), encoding="utf-8")
            self.assertEqual(ui._versao_dos_dados(caminho), ("16/11/2026", "abcdef1"))
            caminho.write_text(json.dumps({"auditado_em_utc": "2026-11-18T09:00:00+00:00",
                                           "versao_codigo_git": "1234567"}), encoding="utf-8")
            antes = caminho.stat().st_mtime_ns
            os.utime(caminho, ns=(antes + 10**9, antes + 10**9))
            self.assertEqual(ui._versao_dos_dados(caminho), ("18/11/2026", "1234567"))

    def test_sem_arquivo_devolve_none(self):
        self.assertIsNone(ui._versao_dos_dados(Path("/caminho/que/nao/existe.json")))

    def test_parar_mostra_rodape_antes_de_interromper(self):
        ordem = []
        with mock.patch.object(ui, "rodape", side_effect=lambda: ordem.append("rodape")), \
                mock.patch.object(ui.st, "stop", side_effect=lambda: ordem.append("stop")):
            ui.parar()
        self.assertEqual(ordem, ["rodape", "stop"])

    def test_sem_manifesto_mostra_so_a_fonte(self):
        with mock.patch.object(ui, "_versao_dos_dados", return_value=None), \
                mock.patch.object(ui.st, "html") as html:
            ui.rodape()
        texto = html.call_args[0][0]
        self.assertIn("Fonte: Microdados do ENEM 2019 a 2022, INEP", texto)
        self.assertNotIn("conferidos em", texto)

    def test_com_manifesto_mostra_data_e_commit(self):
        with mock.patch.object(ui, "_versao_dos_dados", return_value=("16/11/2026", "abcdef1")), \
                mock.patch.object(ui.st, "html") as html:
            ui.rodape()
        self.assertIn("conferidos em 16/11/2026 (código abcdef1).", html.call_args[0][0])


@unittest.skipIf(ui is None, "streamlit/plotly nao instalados")
class TestVisaoSimples(unittest.TestCase):
    def test_frase_no_meio_da_distribuicao(self):
        self.assertEqual(ui.frase_posicao("73,0%"),
                         "Sua nota foi maior que a de 73,0% dos participantes: cerca de 73 em cada 100.")

    def test_frase_perto_das_pontas_nao_arredonda_para_100(self):
        self.assertEqual(ui.frase_posicao("99,6%"), "Sua nota foi maior que a de 99,6% dos participantes.")
        self.assertEqual(ui.frase_posicao("0,4%"), "Sua nota foi maior que a de 0,4% dos participantes.")

    def test_frase_em_limite_usa_so_o_texto_exibido(self):
        self.assertEqual(ui.frase_posicao("acima de 99,9%"),
                         "Sua nota está no topo do grupo, entre os 0,1% de notas mais altas.")
        self.assertEqual(ui.frase_posicao("abaixo de 0,3%"),
                         "Sua nota está na base do grupo, entre os 0,3% de notas mais baixas.")

    def test_texto_fora_do_formato_nao_vira_frase_nem_barra(self):
        self.assertIsNone(ui.frase_posicao("—"))
        self.assertIsNone(ui.posicao_simples([("A", "—", "#000000")]))

    def test_barras_vao_de_0_a_100_e_mostram_o_texto_exibido(self):
        fig = ui.posicao_simples([("UF", "73,0%", ui.COR_PROPRIO), ("Brasil", "acima de 99,9%", ui.COR_BRASIL)])
        trilho, menor = fig.data
        self.assertEqual(list(trilho.x), [100, 100])
        self.assertEqual(list(menor.x), [73.0, 99.9])
        self.assertEqual([a.text for a in fig.layout.annotations],
                         ["<b>UF</b>  73,0%", "<b>Brasil</b>  acima de 99,9%"])
        self.assertEqual(fig.layout.barmode, "overlay")
        self.assertEqual(fig.layout.xaxis.range, (0, 100))




class TestIdentidadeVisual(unittest.TestCase):
    """Logotipos e bordas/arcos em azul neon (PO, 24/11/2026)."""

    def test_logotipos_existem_e_sao_leves(self):
        for arquivo in (ui.LOGO_APP, ui.MARCA):
            self.assertTrue(arquivo.exists(), arquivo)
            self.assertLess(arquivo.stat().st_size, 100_000, arquivo)  # reduzidos para a sidebar
            self.assertNotIn("static", arquivo.parts)  # app/static/ continua so com as fontes (DL-09)

    def test_css_neon_nao_carrega_recurso_externo(self):
        for tema, paleta in ui._PALETAS.items():
            with self.subTest(tema=tema):
                css = ui._css_neon(paleta, tema)
                urls = re.findall(r'url\("([^"]+)"\)', css)
                self.assertTrue(urls)
                for u in urls:
                    self.assertTrue(u.startswith("data:image/svg+xml,"), u)  # R6: nada sai do navegador

    def test_neon_do_claro_e_azul_forte(self):
        self.assertEqual(ui._PALETAS["light"]["neon"], "#1d4ed8")
        self.assertEqual(ui._PALETAS["dark"]["neon"], "#22d3ee")

    def test_arcos_so_no_fundo_da_pagina(self):
        # Os arcos ficam so fora dos cards (PO, 24/11/2026): toda imagem do CSS neon tem de
        # estar numa regra do fundo da pagina, nunca no formulario nem nos cartoes.
        for tema, paleta in ui._PALETAS.items():
            css = ui._css_neon(paleta, tema)
            regras = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
            com_imagem = [sel.replace("<style>", "").strip() for sel, corpo in regras if "url(" in corpo]
            with self.subTest(tema=tema):
                self.assertTrue(com_imagem)
                for sel in com_imagem:
                    self.assertEqual(sel, '[data-testid="stApp"]')
                for sel, corpo in regras:
                    if "stForm" in sel or "stMetric" in sel:
                        self.assertNotIn("background", corpo)



class TestLogotiposAcessiveis(unittest.TestCase):
    """Os dois logotipos tem texto alternativo (WCAG 1.1.1; achado do axe no pente fino)."""

    def test_st_image_dos_logotipos_recebe_alt(self):
        fonte = Path(ui.__file__).read_text(encoding="utf-8")
        self.assertRegex(fonte, r'st\.image\(str\(LOGO_APP\)[^)]*alt="Radar ENEM"\)')
        self.assertRegex(fonte, r'st\.image\(str\(MARCA\)[^)]*alt="KiraSapiens Neurotech"\)')


class TestCacheSemCopia(unittest.TestCase):
    """Artefatos em st.cache_resource, so leitura (otimizacao do pente fino da AV6, 24/11/2026)."""

    def test_congelar_devolve_mapeamento_so_leitura(self):
        dados = ui.congelar({("2022", "mt"): [(400.0, 1, 0), (500.0, 2, 1)]})
        self.assertEqual(dados[("2022", "mt")], ((400.0, 1, 0), (500.0, 2, 1)))
        with self.assertRaises(TypeError):
            dados[("2022", "lc")] = ()
        with self.assertRaises(AttributeError):
            dados[("2022", "mt")].append((600.0, 1, 3))

    def test_congelar_protege_todos_os_niveis(self):
        # Revisao do #39: o formato real e lista de tuplas (nota, n, abaixo); o congelamento
        # e recursivo, entao nenhum nivel pode ser alterado por dentro.
        dados = ui.congelar({("2022", "mt", "BR"): [(400.0, 1, 0), [500.0, 2, 1]],
                             "aninhado": {"faixas": [[1, 2], [3]], "grupos": {"R1", "R2"}}})
        with self.assertRaises(TypeError):
            dados[("2022", "mt", "BR")][0][1] = 99
        with self.assertRaises(TypeError):
            dados[("2022", "mt", "BR")][1][1] = 99          # a lista interna virou tupla
        with self.assertRaises(TypeError):
            dados["aninhado"]["faixas"] = ()                  # dicionario interno so leitura
        with self.assertRaises(TypeError):
            dados["aninhado"]["faixas"][0][0] = 0
        with self.assertRaises(AttributeError):
            dados["aninhado"]["grupos"].add("R3")             # conjunto virou frozenset

    def test_congelar_recusa_tipo_mutavel_desconhecido(self):
        with self.assertRaises(TypeError):
            ui.congelar({"a": [bytearray(b"x")]})

        class Registro:
            pass

        with self.assertRaises(TypeError):
            ui.congelar({"a": Registro()})

    def test_artefatos_grandes_nao_usam_cache_data(self):
        # cache_data copiaria o artefato a cada execucao da pagina (37 MB no territorial).
        app = Path(ui.__file__).resolve().parent
        for arquivo in [app / "app.py", *sorted((app / "pages").glob("*.py"))]:
            fonte = arquivo.read_text(encoding="utf-8")
            with self.subTest(pagina=arquivo.name):
                self.assertNotRegex(fonte, r"@st\.cache_data\s*\ndef (_cdfs|carregar|carregar_exatas)\(")
                self.assertIn("@st.cache_resource", fonte)


if __name__ == "__main__":
    unittest.main()
