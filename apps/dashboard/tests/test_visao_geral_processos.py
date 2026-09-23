"""
Painéis derivados de Processos na Visão geral do Dashboard (Movimentação
processual, Processos paralisados, Prazos a vencer) e card "Usuários
ativos" —
specs/dashboard-abas-visao-geral-analise-dados.md.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_GERIR_CRIAR_USUARIO,
    MODULO_GERIR,
    MODULO_PAINEL,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)
from apps.processos.models import MovimentacaoProcessual, Processo


class DashboardProcessosBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("gestor_painel", password="testpass")
        self.papel = PapelAcesso.objects.create(nome="Papel Painel Processos", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=self.papel, ativo=True)
        for modulo in (MODULO_PAINEL, MODULO_PROCESSOS):
            PermissaoPapel.objects.create(
                papel=self.papel, modulo=modulo, ativo=True, nivel=NIVEL_TODOS
            )
        self.client.force_login(self.usuario)

    def _processo(self, titulo, *, status="ativo", **extra):
        return Processo.objects.create(
            titulo=titulo, responsavel=self.usuario, status=status, **extra
        )

    def _get(self):
        return self.client.get("/", HTTP_HOST=self.http_host)


class TestMovimentacaoProcessual(DashboardProcessosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_movimentacao"

    def test_movimentacao_24h_e_7dias(self):
        agora = timezone.now()
        recente = self._processo("Movimentado há 2h")
        MovimentacaoProcessual.objects.create(processo=recente, data=agora - timedelta(hours=2))

        antigo = self._processo("Movimentado há 3 dias")
        MovimentacaoProcessual.objects.create(processo=antigo, data=agora - timedelta(days=3))

        fora_da_janela = self._processo("Movimentado há 10 dias")
        MovimentacaoProcessual.objects.create(processo=fora_da_janela, data=agora - timedelta(days=10))

        resposta = self._get()

        self.assertEqual(resposta.status_code, 200)
        movimentacao = resposta.context["movimentacao"]
        self.assertEqual(movimentacao["24h"]["total"], 1)
        self.assertEqual(movimentacao["7dias"]["total"], 2)
        titulos_7d = [item["processo"].titulo for item in movimentacao["7dias"]["processos"]]
        self.assertIn("Movimentado há 2h", titulos_7d)
        self.assertIn("Movimentado há 3 dias", titulos_7d)
        self.assertNotIn("Movimentado há 10 dias", titulos_7d)

    def test_processo_arquivado_nao_conta_em_movimentacao(self):
        arquivado = self._processo("Processo arquivado", status="arquivado")
        MovimentacaoProcessual.objects.create(processo=arquivado, data=timezone.now())

        resposta = self._get()

        self.assertEqual(resposta.context["movimentacao"]["24h"]["total"], 0)


class TestProcessosParalisados(DashboardProcessosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_paralisados"

    def test_grupos_cumulativos_por_ultima_movimentacao(self):
        agora = timezone.now()

        parado_35_dias = self._processo("Parado 35 dias")
        MovimentacaoProcessual.objects.create(processo=parado_35_dias, data=agora - timedelta(days=35))

        parado_100_dias = self._processo("Parado 100 dias")
        MovimentacaoProcessual.objects.create(processo=parado_100_dias, data=agora - timedelta(days=100))

        parado_200_dias = self._processo("Parado 200 dias")
        MovimentacaoProcessual.objects.create(processo=parado_200_dias, data=agora - timedelta(days=200))

        recente = self._processo("Recente")
        MovimentacaoProcessual.objects.create(processo=recente, data=agora - timedelta(days=1))

        resposta = self._get()
        paralisados = resposta.context["paralisados"]

        self.assertEqual(paralisados["1mes"]["total"], 3)
        self.assertEqual(paralisados["3meses"]["total"], 2)
        self.assertEqual(paralisados["6meses"]["total"], 1)

    def test_arquivado_excluido_e_fallback_para_data_distribuicao(self):
        arquivado = self._processo("Arquivado parado", status="arquivado")
        MovimentacaoProcessual.objects.create(
            processo=arquivado, data=timezone.now() - timedelta(days=400)
        )
        sem_movimentacao = self._processo(
            "Sem movimentação, só distribuição",
            data_distribuicao=timezone.localdate() - timedelta(days=40),
        )

        resposta = self._get()
        paralisados = resposta.context["paralisados"]

        titulos = [item["processo"].titulo for item in paralisados["1mes"]["processos"]]
        self.assertNotIn("Arquivado parado", titulos)
        self.assertIn("Sem movimentação, só distribuição", titulos)


class TestPrazosAVencer(DashboardProcessosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_prazos"

    def test_grupos_cumulativos_por_prazo_proximo(self):
        hoje = timezone.localdate()
        p_hoje = self._processo("Prazo hoje", prazo_proximo=hoje)
        p_amanha = self._processo("Prazo amanhã", prazo_proximo=hoje + timedelta(days=1))
        p_3d = self._processo("Prazo em 3 dias", prazo_proximo=hoje + timedelta(days=3))
        p_5d = self._processo("Prazo em 5 dias", prazo_proximo=hoje + timedelta(days=5))
        self._processo("Prazo em 10 dias", prazo_proximo=hoje + timedelta(days=10))
        self._processo("Prazo vencido", prazo_proximo=hoje - timedelta(days=1))
        self._processo("Sem prazo")

        resposta = self._get()
        prazos = resposta.context["prazos"]

        self.assertEqual(prazos["hoje"]["total"], 1)
        self.assertEqual(prazos["amanha"]["total"], 1)
        self.assertEqual(prazos["3dias"]["total"], 3)
        self.assertEqual(prazos["5dias"]["total"], 4)
        self.assertIn(p_hoje, prazos["hoje"]["processos"])
        self.assertIn(p_amanha, prazos["3dias"]["processos"])
        self.assertIn(p_3d, prazos["5dias"]["processos"])
        self.assertIn(p_5d, prazos["5dias"]["processos"])


class TestCardUsuariosAtivos(DashboardProcessosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_usuarios_ativos"

    def test_sem_habilitacao_gerir_nao_mostra_card(self):
        resposta = self._get()
        self.assertNotIn("usuarios_ativos", resposta.context["resumo"])
        self.assertFalse(resposta.context["acesso_usuarios_ativos"])

    def test_com_habilitacao_gerir_mostra_contagem(self):
        PermissaoPapel.objects.create(
            papel=self.papel, modulo=MODULO_GERIR, ativo=True, nivel="",
        )
        HabilitacaoPapel.objects.create(
            papel=self.papel, modulo=MODULO_GERIR,
            item=HAB_GERIR_CRIAR_USUARIO, ativo=True,
        )

        resposta = self._get()

        self.assertTrue(resposta.context["acesso_usuarios_ativos"])
        self.assertEqual(resposta.context["resumo"]["usuarios_ativos"], User.objects.filter(is_active=True).count())
