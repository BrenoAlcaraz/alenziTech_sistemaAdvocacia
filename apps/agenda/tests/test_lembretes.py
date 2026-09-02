"""
Testes do lembrete automático de Agenda (PDR-0016, parte Agenda):
comando `enviar_lembretes_agenda` notifica o responsável quando o
compromisso está por volta de 15 minutos antes do início; concluído,
cancelado ou sem responsável nunca notifica; reagendar reabre o
lembrete; execuções repetidas na mesma janela não duplicam; job com
dados em dois tenants nunca cria notificação cruzada entre eles.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context, tenant_context

from apps.agenda.models import Compromisso
from apps.notificacoes.models import Notificacao
from apps.saas_tenants.models import Escritorio


class LembretesAgendaBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_lembretes_agenda"

    def setUp(self):
        super().setUp()
        self.responsavel = User.objects.create_user("responsavel", password="testpass")

    def _compromisso(self, *, minutos_para_inicio, **kwargs):
        defaults = {
            "titulo": "Audiência de instrução",
            "data_hora_inicio": timezone.now() + timedelta(minutes=minutos_para_inicio),
            "status": "agendado",
            "responsavel": self.responsavel,
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(**defaults)

    def _rodar_comando(self):
        call_command("enviar_lembretes_agenda")


class TestLembreteDentroDaJanela(LembretesAgendaBase):
    def test_compromisso_a_10_minutos_gera_notificacao(self):
        compromisso = self._compromisso(minutos_para_inicio=10)
        self._rodar_comando()
        notificacao = Notificacao.objects.get(destinatario=self.responsavel)
        self.assertIn(compromisso.titulo, notificacao.mensagem)
        self.assertFalse(notificacao.lida)
        compromisso.refresh_from_db()
        self.assertTrue(compromisso.lembrete_enviado)

    def test_compromisso_ja_iniciado_ainda_agendado_gera_notificacao(self):
        self._compromisso(minutos_para_inicio=-5)
        self._rodar_comando()
        self.assertTrue(Notificacao.objects.filter(destinatario=self.responsavel).exists())


class TestLembreteForaDaJanela(LembretesAgendaBase):
    def test_compromisso_a_30_minutos_nao_gera_notificacao_ainda(self):
        compromisso = self._compromisso(minutos_para_inicio=30)
        self._rodar_comando()
        self.assertFalse(Notificacao.objects.exists())
        compromisso.refresh_from_db()
        self.assertFalse(compromisso.lembrete_enviado)

    def test_compromisso_vencido_ha_muito_tempo_nao_gera_lembrete_tardio(self):
        compromisso = self._compromisso(minutos_para_inicio=-20)
        self._rodar_comando()
        self.assertFalse(Notificacao.objects.exists())
        compromisso.refresh_from_db()
        self.assertFalse(compromisso.lembrete_enviado)


class TestLembreteNaoGeradoQuandoNaoElegivel(LembretesAgendaBase):
    def test_compromisso_concluido_nao_gera_notificacao(self):
        self._compromisso(minutos_para_inicio=10, status="concluido")
        self._rodar_comando()
        self.assertFalse(Notificacao.objects.exists())

    def test_compromisso_cancelado_nao_gera_notificacao(self):
        self._compromisso(minutos_para_inicio=10, status="cancelado")
        self._rodar_comando()
        self.assertFalse(Notificacao.objects.exists())

    def test_compromisso_sem_responsavel_nao_gera_notificacao(self):
        self._compromisso(minutos_para_inicio=10, responsavel=None)
        self._rodar_comando()
        self.assertFalse(Notificacao.objects.exists())


class TestLembreteReagendamento(LembretesAgendaBase):
    def test_reagendar_apos_lembrete_enviado_permite_novo_lembrete(self):
        compromisso = self._compromisso(minutos_para_inicio=10)
        self._rodar_comando()
        compromisso.refresh_from_db()
        self.assertTrue(compromisso.lembrete_enviado)

        compromisso.data_hora_inicio = timezone.now() + timedelta(minutes=12)
        compromisso.save()
        compromisso.refresh_from_db()
        self.assertFalse(compromisso.lembrete_enviado)

        self._rodar_comando()
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.responsavel).count(), 2
        )

    def test_reagendar_para_fora_da_janela_nao_reenvia_ainda(self):
        compromisso = self._compromisso(minutos_para_inicio=10)
        self._rodar_comando()

        compromisso.data_hora_inicio = timezone.now() + timedelta(minutes=45)
        compromisso.save()

        self._rodar_comando()
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.responsavel).count(), 1
        )


class TestLembreteSemDuplicacao(LembretesAgendaBase):
    def test_execucoes_repetidas_na_mesma_janela_nao_duplicam(self):
        self._compromisso(minutos_para_inicio=10)
        self._rodar_comando()
        self._rodar_comando()
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.responsavel).count(), 1
        )


class TestLembreteIsolamentoMultiTenant(LembretesAgendaBase):
    """
    Teste negativo obrigatório (dado multi-tenant): o job roda com
    compromisso elegível em dois tenants na mesma execução e nunca cria
    `Notificacao` num tenant a partir do `Compromisso` do outro — falha
    se o comando deixar de trocar de schema por tenant (ex.: reutilizar
    o schema de um tenant anterior para todos).
    """

    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "wi_lembretes_iso_a"

    def test_job_nao_cria_notificacao_em_tenant_a_partir_de_compromisso_de_outro(self):
        self._compromisso(minutos_para_inicio=10, titulo="Compromisso tenant A")

        outro_tenant = Escritorio(
            schema_name="wi_lembretes_iso_b",
            nome="Tenant B lembretes",
            slug="wi-lembretes-iso-b",
        )
        with schema_context("public"):
            outro_tenant.save()
        try:
            with tenant_context(outro_tenant):
                responsavel_b = User.objects.create_user("responsavel_b", password="testpass")
                Compromisso.objects.create(
                    titulo="Compromisso tenant B",
                    data_hora_inicio=timezone.now() + timedelta(minutes=10),
                    status="agendado",
                    responsavel=responsavel_b,
                )

            self._rodar_comando()

            notificacoes_a = Notificacao.objects.all()
            self.assertEqual(notificacoes_a.count(), 1)
            self.assertEqual(notificacoes_a.first().destinatario, self.responsavel)
            self.assertNotIn("tenant B", notificacoes_a.first().mensagem)

            with tenant_context(outro_tenant):
                notificacoes_b = Notificacao.objects.all()
                self.assertEqual(notificacoes_b.count(), 1)
                self.assertEqual(notificacoes_b.first().destinatario, responsavel_b)
                self.assertNotIn("tenant A", notificacoes_b.first().mensagem)
        finally:
            with schema_context("public"):
                outro_tenant.delete(force_drop=True)
