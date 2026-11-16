"""Testes das pecas visuais de app/ui.py (so apresentacao, sem dados reais)."""

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
        self.assertEqual(fig.layout.font.color, ui._PALETAS["dark"]["mu"])
        self.assertNotIn("text-shadow:none", escuro)
        claro = self.anel("58,3%")  # sem tema informado, o padrao e o claro
        self.assertIn("text-shadow:none", claro)

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

    def test_cores_de_contexto_passam_de_3_para_1_no_proprio_tema(self):
        for tema, paleta in ui._PALETAS.items():
            for cor in ("fraco1", "fraco2"):
                with self.subTest(tema=tema, cor=cor):
                    self.assertGreaterEqual(contraste(paleta[cor], paleta["bg"]), 3.0)

    def test_textos_passam_de_4_e_meio_para_1(self):
        for tema, paleta in ui._PALETAS.items():
            for cor in ("tx", "mu", "ciano"):
                for fundo in ("bg", "surf"):
                    with self.subTest(tema=tema, cor=cor, fundo=fundo):
                        self.assertGreaterEqual(contraste(paleta[cor], paleta[fundo]), 4.5)

    def test_texto_branco_do_botao(self):
        for tema, paleta in ui._PALETAS.items():
            for fundo in ("azul", "btn_hover"):
                with self.subTest(tema=tema, fundo=fundo):
                    self.assertGreaterEqual(contraste("#ffffff", paleta[fundo]), 4.5)


@unittest.skipIf(ui is None, "streamlit/plotly nao instalados")
class TestRodape(unittest.TestCase):
    def setUp(self):
        ui._versao_dos_dados.cache_clear()

    def tearDown(self):
        ui._versao_dos_dados.cache_clear()

    def test_le_data_e_commit_do_manifesto(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "_manifesto_publicacao.json"
            caminho.write_text(json.dumps({"auditado_em_utc": "2026-11-16T17:30:00+00:00",
                                           "versao_codigo_git": "abcdef1234567"}), encoding="utf-8")
            self.assertEqual(ui._versao_dos_dados(caminho), ("16/11/2026", "abcdef1"))

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


if __name__ == "__main__":
    unittest.main()
