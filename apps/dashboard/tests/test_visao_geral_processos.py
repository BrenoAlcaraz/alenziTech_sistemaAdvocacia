"""
Painéis derivados de Processos na Visão geral do Dashboard (Movimentação
processual, Processos paralisados), Prazos a vencer (itens Prazo da
Agenda Jurídica) e card "Usuários ativos" —
specs/dashboard-abas-visao-geral-analise-dados.md.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_GERIR_CRIAR_USUARIO,
    MODULO_AGENDA,
    MODULO_GERIR,
    MODULO_PAINEL,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.models import ItemAgenda
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
            titulo=titulo, criado_por=self.usuario, status=status, **extra
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
    """Prazos a vencer lê os itens Prazo da Agenda Jurídica (PDR-0034),
    no escopo de leitura da agenda do usuário."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_prazos"

    def setUp(self):
        super().setUp()
        PermissaoPapel.objects.create(
            papel=self.papel, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_SOMENTE_SEUS
        )
        self.processo = self._processo("Processo com prazos")

    def _prazo(self, titulo, dias, **extra):
        dados = {"responsavel": self.usuario, "processo": self.processo}
        dados.update(extra)
        return ItemAgenda.objects.create(
            tipo="prazo", titulo=titulo, data_fatal=timezone.localdate() + timedelta(days=dias), **dados,
        )

    def test_grupos_excludentes_por_data_fatal(self):
        p_hoje = self._prazo("Prazo hoje", 0)
        p_amanha = self._prazo("Prazo amanhã", 1)
        p_2d = self._prazo("Prazo em 2 dias", 2)
        p_3d = self._prazo("Prazo em 3 dias", 3)
        p_5d = self._prazo("Prazo em 5 dias", 5)
        self._prazo("Prazo em 10 dias", 10)
        self._prazo("Prazo vencido", -1)

        resposta = self._get()
        prazos = resposta.context["prazos"]

        self.assertEqual(prazos["hoje"]["itens"], [p_hoje])
        self.assertEqual(prazos["amanha"]["itens"], [p_amanha])
        self.assertEqual(prazos["3dias"]["itens"], [p_2d, p_3d])
        self.assertEqual(prazos["5dias"]["itens"], [p_5d])
        self.assertContains(resposta, f"/agenda/{p_hoje.pk}/editar/")

    def test_faixa_hoje_e_o_primeiro_bloco_com_prazo_de_hoje(self):
        self._prazo("Prazo fatal de hoje", 0)

        html = self._get().content.decode()

        inicio_faixa = html.index('id="titulo-hoje"')
        self.assertLess(inicio_faixa, html.index("Prazo: Prazo fatal de hoje"))
        self.assertLess(html.index("Prazo: Prazo fatal de hoje"), html.index("Prazos a vencer"))
        self.assertLess(html.index("Prazos a vencer"), html.index("Processos ativos"))

    def test_faixa_hoje_vazia_mostra_estado_positivo(self):
        self._prazo("Prazo em 10 dias", 10)

        self.assertContains(self._get(), "Tudo em dia")

    def test_afazeres_pendentes_nao_recontam_prazos_da_janela(self):
        self._prazo("Prazo hoje", 0)
        self._prazo("Prazo em 5 dias", 5)
        self._prazo("Prazo em 10 dias", 10)
        ItemAgenda.objects.create(tipo="tarefa", titulo="Tarefa", responsavel=self.usuario)

        resposta = self._get()

        self.assertEqual(resposta.context["resumo"]["tarefas_pendentes"], 2)

    def test_so_prazos_abertos_do_escopo_e_nunca_outro_tipo(self):
        outro = User.objects.create_user("outro_prazos", password="testpass")
        self._prazo("Prazo alheio", 0, responsavel=outro)
        self._prazo("Prazo concluído", 0, status="concluido")
        ItemAgenda.objects.create(
            tipo="tarefa", titulo="Tarefa com fatal", data_fatal=timezone.localdate(), responsavel=self.usuario,
        )

        prazos = self._get().context["prazos"]

        self.assertEqual(prazos["5dias"]["total"], 0)

    def test_sem_modulo_agenda_nao_ha_bloco_de_prazos(self):
        PermissaoPapel.objects.filter(papel=self.papel, modulo=MODULO_AGENDA).delete()
        self._prazo("Prazo hoje", 0)

        resposta = self._get()

        self.assertIsNone(resposta.context["prazos"])
        self.assertNotContains(resposta, "Prazos a vencer")
        self.assertNotContains(resposta, "Prazo: Prazo hoje")


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
