"""
Regressão: o status "cancelada" de Tarefa (apps/tarefas, delegação de
tarefas) não deve ser contado como pendente no painel.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.tarefas.models import Tarefa


class TestPainelTarefasPendentes(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_tarefas_pendentes"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("dashboard_user", password="testpass")
        self.client.force_login(self.usuario)

    def test_tarefa_cancelada_nao_conta_como_pendente(self):
        Tarefa.objects.create(
            titulo="Tarefa cancelada",
            criador=self.usuario,
            atribuidor=self.usuario,
            responsavel=self.usuario,
            status="cancelada",
        )
        Tarefa.objects.create(
            titulo="Tarefa a fazer",
            criador=self.usuario,
            atribuidor=self.usuario,
            responsavel=self.usuario,
            status="a_fazer",
        )

        resposta = self.client.get("/", HTTP_HOST=self.http_host)

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["resumo"]["tarefas_pendentes"], 1)
        titulos = [t.titulo for t in resposta.context["tarefas_dashboard"]]
        self.assertNotIn("Tarefa cancelada", titulos)
