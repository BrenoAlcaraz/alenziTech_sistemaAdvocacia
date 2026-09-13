"""
Login bem-sucedido gera um LogAtividade —
specs/dashboard-painel-do-gestor.md (fase 1 do log de atividade).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.atividade.models import LogAtividade


class TestLoginRegistraAtividade(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_atividade_login"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("login_teste", password="testpass")

    def test_login_bem_sucedido_gera_log(self):
        # client.login() dispara user_logged_in (diferente de force_login,
        # que pula autenticação e não emite o signal).
        logado = self.client.login(
            username="login_teste", password="testpass", HTTP_HOST=self.http_host
        )
        self.assertTrue(logado)
        self.assertEqual(
            LogAtividade.objects.filter(usuario=self.usuario, tipo="login").count(), 1
        )

    def test_login_falho_nao_gera_log(self):
        logado = self.client.login(
            username="login_teste", password="senha_errada", HTTP_HOST=self.http_host
        )
        self.assertFalse(logado)
        self.assertEqual(LogAtividade.objects.filter(usuario=self.usuario).count(), 0)
