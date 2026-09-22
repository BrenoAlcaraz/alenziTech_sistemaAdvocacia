"""
Histórico de atividade do próprio usuário — qualquer usuário
autenticado, mesmo sem o módulo `gerir`/Painel — specs/atividade-ampliar-catalogo.md.
"""

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.atividade.models import LogAtividade


class TestMinhaAtividade(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_minha_atividade"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

        self.usuario = User.objects.create_user("sem_gerir", password="testpass")
        self.outro = User.objects.create_user("outro_usuario", password="testpass")
        self.client.force_login(self.usuario)

        LogAtividade.objects.create(
            usuario=self.usuario, tipo="tarefa_criada", descricao="Criou a tarefa própria"
        )
        LogAtividade.objects.create(
            usuario=self.outro, tipo="tarefa_criada", descricao="Criou a tarefa do outro"
        )

    def test_usuario_sem_gerir_acessa_a_propria_timeline(self):
        resposta = self.client.get("/minha-atividade/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        descricoes = [a.descricao for a in resposta.context["atividades"]]
        self.assertIn("Criou a tarefa própria", descricoes)

    def test_timeline_nao_mostra_atividade_de_terceiros(self):
        resposta = self.client.get("/minha-atividade/", HTTP_HOST=self.http_host)
        descricoes = [a.descricao for a in resposta.context["atividades"]]
        self.assertNotIn("Criou a tarefa do outro", descricoes)

    def test_exige_login(self):
        self.client.logout()
        resposta = self.client.get("/minha-atividade/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 302)
