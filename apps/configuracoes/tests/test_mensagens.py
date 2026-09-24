"""
Mensagens de resultado (components/mensagens.html): anunciadas ao leitor de
tela — erro como alert, sucesso/aviso como status — com botão de fechar
rotulado e aviso no token de urgência do sistema.
"""

from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import SimpleTestCase


def _renderizar(nivel, texto):
    return render_to_string("components/mensagens.html", {"messages": [Message(nivel, texto)]})


class TestMensagens(SimpleTestCase):
    def test_sucesso_e_anunciado_como_status(self):
        html = _renderizar(constants.SUCCESS, "Usuário Ana excluído.")

        self.assertIn('role="status"', html)
        self.assertIn("Sucesso: </span>Usuário Ana excluído.", html)
        self.assertIn('aria-label="Fechar mensagem"', html)

    def test_erro_e_anunciado_como_alert(self):
        html = _renderizar(constants.ERROR, "Senha incorreta. Nenhum usuário foi excluído.")

        self.assertIn('role="alert"', html)
        self.assertNotIn('role="status"', html)
        self.assertIn("Erro: </span>Senha incorreta.", html)

    def test_aviso_usa_token_do_sistema(self):
        html = _renderizar(constants.WARNING, "Confira os dados.")

        self.assertIn('role="status"', html)
        self.assertIn("bg-juridico-urgente-bg text-juridico-urgente", html)
        self.assertNotIn("amber", html)
