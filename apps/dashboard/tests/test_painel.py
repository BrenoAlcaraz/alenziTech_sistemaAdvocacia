"""
Regressão: o status "cancelada" de Tarefa (apps/tarefas, delegação de
tarefas) não deve ser contado como pendente no painel.

Também cobre a autorização de módulo aplicada ao painel: usuário sem
acesso a um módulo não recebe totais/listas correspondentes no
contexto do painel (financeiro: specs/autorizacao-modulo-financeiro.md;
clientes/processos/tarefas/agenda:
specs/autorizacao-modulo-chat-modelos-painel.md).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    MODULO_CLIENTES,
    MODULO_FINANCEIRO,
    MODULO_PROCESSOS,
    MODULO_TAREFAS,
    NIVEL_DADOS_TODOS,
    NIVEL_TODOS,
)
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
        papel = PapelAcesso.objects.create(nome="Papel Tarefas Painel", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_TAREFAS, ativo=True, nivel=NIVEL_TODOS
        )
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
            papel=papel, tipo_conta=None, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS
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


class TestPainelClientesProcessosAgendaSemAcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_cpa_sem_acesso"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("sem_cpa", password="testpass")
        self.client.force_login(self.usuario)

    def test_painel_sem_blocos_de_clientes_processos_tarefas_agenda(self):
        resposta = self.client.get("/", HTTP_HOST=self.http_host)

        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("clientes_ativos", resposta.context["resumo"])
        self.assertNotIn("processos_ativos", resposta.context["resumo"])
        self.assertNotIn("tarefas_pendentes", resposta.context["resumo"])
        self.assertNotIn("compromissos_proximos", resposta.context["resumo"])
        self.assertEqual(list(resposta.context["tarefas_dashboard"]), [])
        self.assertEqual(list(resposta.context["compromissos_dashboard"]), [])


class TestPainelClientesProcessosAgendaComAcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_cpa_com_acesso"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("com_cpa", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel CPA Painel", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        for modulo in (MODULO_CLIENTES, MODULO_PROCESSOS, MODULO_AGENDA):
            PermissaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=modulo, ativo=True, nivel=NIVEL_TODOS
            )
        self.client.force_login(self.usuario)

    def test_painel_com_blocos_de_clientes_processos_agenda(self):
        resposta = self.client.get("/", HTTP_HOST=self.http_host)

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("clientes_ativos", resposta.context["resumo"])
        self.assertIn("processos_ativos", resposta.context["resumo"])
        self.assertIn("compromissos_proximos", resposta.context["resumo"])
        self.assertNotIn("tarefas_pendentes", resposta.context["resumo"])
