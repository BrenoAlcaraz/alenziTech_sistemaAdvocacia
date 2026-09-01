"""
Testes de autorização de módulo para apps/chat/views.py.

Cobre o enforcement de tem_permissao_modulo(user, MODULO_CHAT) nas três
rotas existentes (lista, detalhe, global). MODULO_CHAT não tem níveis
(NIVEIS_POR_MODULO[MODULO_CHAT] == [""]) — é checagem binária pura, sem
escopo de leitura a resolver (ver specs/autorizacao-modulo-chat-modelos-painel.md).

Segue o mesmo padrão de fixtures de apps/clientes/tests/test_autorizacao.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_CHAT


class ChatAutorizacaoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=""):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=ativo, nivel=nivel
        )


class TestChatAutorizacaoModuloNegado(ChatAutorizacaoBase):
    """Usuário sem autorização do módulo `chat` — as três rotas negam."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_chat_negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_chat")
        self.client.force_login(self.user)

    def test_lista_negada(self):
        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_detalhe_negado(self):
        r = self.client.get("/chat/1/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_global_get_negado(self):
        r = self.client.get("/chat/global/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_global_post_negado(self):
        r = self.client.post(
            "/chat/global/", {"conteudo": "oi"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)


class TestChatAutorizacaoModuloConcedido(ChatAutorizacaoBase):
    """Usuário com autorização do módulo `chat` — as três rotas operam normalmente."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_chat_concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_chat")
        papel = self._new_papel("Papel Chat")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_CHAT)
        self.client.force_login(self.user)

    def test_lista_redireciona_para_global(self):
        r = self.client.get("/chat/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)

    def test_detalhe_redireciona_para_global(self):
        r = self.client.get("/chat/1/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)

    def test_global_get_ok(self):
        r = self.client.get("/chat/global/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_global_post_envia_mensagem(self):
        r = self.client.post(
            "/chat/global/", {"conteudo": "oi"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
