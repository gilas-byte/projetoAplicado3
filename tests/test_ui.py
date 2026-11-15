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
        self.assertIn("<small>acima de</small>", html)

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


if __name__ == "__main__":
    unittest.main()
