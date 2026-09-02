"""
Regressão: escopo de responsável aplicado aos blocos do Dashboard
(specs/dashboard-escopo-responsavel.md, apagada após promoção do
conhecimento durável para docs/STATUS.md).

Segue o mesmo padrão de fixtures de apps/tarefas/tests/test_escopo.py
sobre django_tenants.test.cases.TenantTestCase.
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
    NIVEL_DADOS,
    NIVEL_SOLICITACOES,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.models import Compromisso
from apps.clientes.models import Cliente
from apps.financeiro.models import LancamentoFinanceiro
from apps.processos.models import Processo
from apps.tarefas.models import Tarefa


class DashboardEscopoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _papel_com_niveis(self, nome, niveis):
        papel = PapelAcesso.objects.create(nome=nome, ativo=True)
        for modulo, nivel in niveis.items():
            PermissaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=modulo, ativo=True, nivel=nivel
            )
        return papel

    def _get_painel(self):
        return self.client.get("/", HTTP_HOST=self.http_host)


class TestPainelEscopoSomenteSeus(DashboardEscopoBase):
    """
    Usuário com nível somente_seus em Clientes/Processos/Tarefas/Agenda
    só vê, no Dashboard, contagem e lista dos registros onde é
    responsável — mesmo existindo registros de outro responsável no
    tenant.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_escopo_somente_seus"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("dashboard_somente_seus")
        self.outro = self._user("dashboard_outro_responsavel")
        papel = self._papel_com_niveis(
            "Papel Dashboard Somente Seus",
            {
                MODULO_CLIENTES: NIVEL_SOMENTE_SEUS,
                MODULO_PROCESSOS: NIVEL_SOMENTE_SEUS,
                MODULO_TAREFAS: NIVEL_SOMENTE_SEUS,
                MODULO_AGENDA: NIVEL_SOMENTE_SEUS,
            },
        )
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        self.client.force_login(self.usuario)

        Cliente.objects.create(
            nome_razao_social="Cliente Próprio", ativo=True, responsavel=self.usuario
        )
        Cliente.objects.create(
            nome_razao_social="Cliente Alheio", ativo=True, responsavel=self.outro
        )

        Processo.objects.create(
            titulo="Processo Próprio",
            numero="0000001-00.2026.8.26.0100",
            status="ativo",
            responsavel=self.usuario,
        )
        Processo.objects.create(
            titulo="Processo Alheio",
            numero="0000002-00.2026.8.26.0100",
            status="ativo",
            responsavel=self.outro,
        )

        Tarefa.objects.create(
            titulo="Tarefa Própria",
            criador=self.usuario,
            atribuidor=self.usuario,
            responsavel=self.usuario,
            status="a_fazer",
        )
        Tarefa.objects.create(
            titulo="Tarefa Alheia",
            criador=self.outro,
            atribuidor=self.outro,
            responsavel=self.outro,
            status="a_fazer",
        )

        from django.utils import timezone

        daqui_2_dias = timezone.now() + timezone.timedelta(days=2)
        Compromisso.objects.create(
            titulo="Compromisso Próprio",
            status="agendado",
            data_hora_inicio=daqui_2_dias,
            responsavel=self.usuario,
        )
        Compromisso.objects.create(
            titulo="Compromisso Alheio",
            status="agendado",
            data_hora_inicio=daqui_2_dias,
            responsavel=self.outro,
        )

    def test_contagens_e_listas_restritas_ao_proprio_responsavel(self):
        resposta = self._get_painel()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["resumo"]["clientes_ativos"], 1)
        self.assertEqual(resposta.context["resumo"]["processos_ativos"], 1)
        self.assertEqual(resposta.context["resumo"]["tarefas_pendentes"], 1)
        self.assertEqual(resposta.context["resumo"]["compromissos_proximos"], 1)

        titulos_tarefas = [t.titulo for t in resposta.context["tarefas_dashboard"]]
        self.assertIn("Tarefa Própria", titulos_tarefas)
        self.assertNotIn("Tarefa Alheia", titulos_tarefas)

        titulos_compromissos = [
            c.titulo for c in resposta.context["compromissos_dashboard"]
        ]
        self.assertIn("Compromisso Próprio", titulos_compromissos)
        self.assertNotIn("Compromisso Alheio", titulos_compromissos)


class TestPainelEscopoTodosVeTudo(DashboardEscopoBase):
    """Nível todos continua sem filtro adicional — sem regressão."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_escopo_todos"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("dashboard_nivel_todos")
        self.outro = self._user("dashboard_outro_nivel_todos")
        papel = self._papel_com_niveis(
            "Papel Dashboard Todos", {MODULO_TAREFAS: NIVEL_TODOS}
        )
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        self.client.force_login(self.usuario)

        Tarefa.objects.create(
            titulo="Tarefa Própria",
            criador=self.usuario,
            atribuidor=self.usuario,
            responsavel=self.usuario,
            status="a_fazer",
        )
        Tarefa.objects.create(
            titulo="Tarefa Alheia",
            criador=self.outro,
            atribuidor=self.outro,
            responsavel=self.outro,
            status="a_fazer",
        )

    def test_todos_ve_tarefas_de_qualquer_responsavel(self):
        resposta = self._get_painel()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["resumo"]["tarefas_pendentes"], 2)
        titulos = [t.titulo for t in resposta.context["tarefas_dashboard"]]
        self.assertIn("Tarefa Própria", titulos)
        self.assertIn("Tarefa Alheia", titulos)


class TestPainelFinanceiroNivelSolicitacoes(DashboardEscopoBase):
    """
    Nível `solicitacoes` em Financeiro autoriza o módulo, mas não o
    bloco de dados consolidados do Dashboard.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_financeiro_nivel_solicitacoes"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("dashboard_financeiro_solicitacoes")
        papel = self._papel_com_niveis(
            "Papel Dashboard Financeiro Solicitacoes",
            {MODULO_FINANCEIRO: NIVEL_SOLICITACOES},
        )
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        self.client.force_login(self.usuario)
        LancamentoFinanceiro.objects.create(
            tipo="receita",
            descricao="Honorário Pendente",
            valor="1000.00",
            data_vencimento="2026-09-30",
            status="pendente",
        )

    def test_bloco_financeiro_oculto_para_nivel_solicitacoes(self):
        resposta = self._get_painel()

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.context["acesso_financeiro"])
        self.assertNotIn("a_receber", resposta.context["resumo"])
        self.assertNotIn("a_pagar", resposta.context["resumo"])
        self.assertEqual(list(resposta.context["financeiro_dashboard"]), [])
        self.assertNotContains(resposta, "Honorário Pendente")


class TestPainelFinanceiroNivelDados(DashboardEscopoBase):
    """Nível `dados` continua vendo o bloco financeiro, sem regressão."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_financeiro_nivel_dados"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("dashboard_financeiro_dados")
        papel = self._papel_com_niveis(
            "Papel Dashboard Financeiro Dados", {MODULO_FINANCEIRO: NIVEL_DADOS}
        )
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        self.client.force_login(self.usuario)
        LancamentoFinanceiro.objects.create(
            tipo="receita",
            descricao="Honorário Pendente",
            valor="1000.00",
            data_vencimento="2026-09-30",
            status="pendente",
        )

    def test_bloco_financeiro_visivel_para_nivel_dados(self):
        resposta = self._get_painel()

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context["acesso_financeiro"])
        self.assertIn("a_receber", resposta.context["resumo"])
        self.assertContains(resposta, "Honorário Pendente")
