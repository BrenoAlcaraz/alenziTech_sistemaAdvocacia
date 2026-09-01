"""
Regressão: o status "cancelada" de Tarefa (apps/tarefas, delegação de
tarefas) não deve ser contado como pendente no painel.

Também cobre a autorização de módulo em Financeiro aplicada ao painel:
usuário sem acesso ao módulo `financeiro` não recebe totais nem lista
financeira no contexto do painel (ver specs/autorizacao-modulo-financeiro.md).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS
from apps.financeiro.models import LancamentoFinanceiro
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


class TestPainelFinanceiroSemAcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_financeiro_sem_acesso"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("sem_financeiro", password="testpass")
        self.client.force_login(self.usuario)
        LancamentoFinanceiro.objects.create(
            tipo="receita",
            descricao="Honorário Pendente",
            valor="1000.00",
            data_vencimento="2026-09-30",
            status="pendente",
        )

    def test_painel_sem_totais_nem_lista_financeira(self):
        resposta = self.client.get("/", HTTP_HOST=self.http_host)

        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("a_receber", resposta.context["resumo"])
        self.assertNotIn("a_pagar", resposta.context["resumo"])
        self.assertEqual(list(resposta.context["financeiro_dashboard"]), [])
        self.assertNotContains(resposta, "Honorário Pendente")


class TestPainelFinanceiroComAcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_financeiro_com_acesso"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("com_financeiro", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro Painel", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS
        )
        self.client.force_login(self.usuario)
        LancamentoFinanceiro.objects.create(
            tipo="receita",
            descricao="Honorário Pendente",
            valor="1000.00",
            data_vencimento="2026-09-30",
            status="pendente",
        )

    def test_painel_com_totais_e_lista_financeira(self):
        resposta = self.client.get("/", HTTP_HOST=self.http_host)

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("a_receber", resposta.context["resumo"])
        self.assertEqual(len(resposta.context["financeiro_dashboard"]), 1)
        self.assertContains(resposta, "Honorário Pendente")
