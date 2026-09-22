"""
Logout gera um LogAtividade — specs/atividade-ampliar-catalogo.md.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.atividade.models import LogAtividade


class TestLogoutRegistraAtividade(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_atividade_logout"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("logout_teste", password="testpass")

    def test_logout_gera_log(self):
        self.client.login(
            username="logout_teste", password="testpass", HTTP_HOST=self.http_host
        )
        self.client.get("/logout/", HTTP_HOST=self.http_host)
        self.assertEqual(
            LogAtividade.objects.filter(usuario=self.usuario, tipo="logout").count(), 1
        )
