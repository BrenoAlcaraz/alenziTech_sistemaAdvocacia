"""
Testes do editor visual na criação de modelo de peça (`modelos:novo`):
a tela passa a mostrar a folha com o padrão de "Meu Estilo" (contexto
`config_documento`/`imagens_estilo_urls`), mas o conteúdo salvo em
`ModeloPeca.conteudo` continua vindo do campo real do form — o teste
simula o que o JS do editor faz (sincronizar o HTML editado no campo
oculto antes do POST), sem depender de JS/navegador.

Reaproveita as fixtures de apps/modelos/tests/test_autorizacao.py.
"""

from apps.accounts.permissoes_constants import HAB_MODELOS_CRIAR, MODULO_MODELOS
from apps.modelos.models import ModeloPeca
from apps.modelos.tests.test_autorizacao import ModelosAutorizacaoBase


class TestNovoModeloEditorVisual(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_novo_editor"

    def setUp(self):
        super().setUp()
        self.user = self._user("cria_modelo_editor")
        papel = self._new_papel("Papel Cria Modelo")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        self.client.force_login(self.user)

    def test_get_novo_expoe_padrao_de_estilo_no_contexto(self):
        r = self.client.get("/modelos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertIn("config_documento", r.context)
        self.assertIn("geral", r.context["config_documento"])
        self.assertIn("imagens_estilo_urls", r.context)

    def test_post_salva_html_editado_no_corpo(self):
        payload = {
            "titulo": "Petição com editor visual",
            "categoria": self._categoria().pk,
            "area_direito": "civil",
            "conteudo": "<p>Texto <b>em negrito</b> editado na folha.</p>",
        }
        r = self.client.post("/modelos/novo/", payload, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)

        modelo = ModeloPeca.objects.get(titulo="Petição com editor visual")
        self.assertEqual(modelo.conteudo, "<p>Texto <b>em negrito</b> editado na folha.</p>")
        self.assertEqual(modelo.criado_por, self.user)
