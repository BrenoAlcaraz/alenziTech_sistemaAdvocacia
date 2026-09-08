"""
Testes do job de expurgo automático de compromissos cancelados
(`expurgar_compromissos_cancelados`, ticket "Agenda: cancelamento
consultável e indicadores de confirmação no Dashboard" — spec
`specs/agenda-participantes-confirmacao.md`): exclui definitivamente
compromisso cancelado há mais de 7 dias, contados da data do
cancelamento (não da data original do compromisso); preserva cancelado
recente e qualquer compromisso não cancelado; isolamento multi-tenant.

Segue o mesmo padrão de fixtures de
apps/agenda/tests/test_lembretes.py sobre
django_tenants.test.cases.TenantTestCase.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context, tenant_context

from apps.agenda.models import Compromisso
from apps.saas_tenants.models import Escritorio


class PurgaCanceladosBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_purga_cancelados"

    def setUp(self):
        super().setUp()
        self.responsavel = User.objects.create_user("responsavel", password="testpass")

    def _compromisso(self, *, status="cancelado", cancelado_em=None, **kwargs):
        defaults = {
            "titulo": "Audiência cancelada",
            "data_hora_inicio": timezone.now() + timedelta(days=1),
            "status": status,
            "responsavel": self.responsavel,
            "cancelado_em": cancelado_em,
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(**defaults)

    def _rodar_comando(self):
        call_command("expurgar_compromissos_cancelados")


class TestExpurgoDeCanceladosAntigos(PurgaCanceladosBase):
    def test_cancelado_ha_mais_de_7_dias_e_excluido(self):
        compromisso = self._compromisso(
            cancelado_em=timezone.now() - timedelta(days=8)
        )
        self._rodar_comando()
        self.assertFalse(Compromisso.objects.filter(pk=compromisso.pk).exists())

    def test_cancelado_exatamente_no_limite_e_excluido(self):
        compromisso = self._compromisso(
            cancelado_em=timezone.now() - timedelta(days=7, seconds=1)
        )
        self._rodar_comando()
        self.assertFalse(Compromisso.objects.filter(pk=compromisso.pk).exists())


class TestExpurgoPreservaOQueNaoDeveSerExcluido(PurgaCanceladosBase):
    def test_cancelado_ha_menos_de_7_dias_nao_e_excluido(self):
        compromisso = self._compromisso(
            cancelado_em=timezone.now() - timedelta(days=2)
        )
        self._rodar_comando()
        self.assertTrue(Compromisso.objects.filter(pk=compromisso.pk).exists())

    def test_agendado_com_data_original_antiga_nao_e_excluido(self):
        compromisso = self._compromisso(
            status="agendado",
            cancelado_em=None,
            data_hora_inicio=timezone.now() - timedelta(days=30),
        )
        self._rodar_comando()
        self.assertTrue(Compromisso.objects.filter(pk=compromisso.pk).exists())

    def test_concluido_nao_e_excluido_mesmo_sem_cancelado_em(self):
        compromisso = self._compromisso(status="concluido", cancelado_em=None)
        self._rodar_comando()
        self.assertTrue(Compromisso.objects.filter(pk=compromisso.pk).exists())


class TestExpurgoIsolamentoMultiTenant(PurgaCanceladosBase):
    """
    Teste negativo obrigatório (dado multi-tenant): o job roda com
    compromisso cancelado elegível em dois tenants na mesma execução e
    nunca exclui/preserva compromisso de um tenant a partir do estado do
    outro — falha se o comando deixar de trocar de schema por tenant.
    """

    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "wi_purga_iso_a"

    def test_job_nao_afeta_tenant_a_partir_do_estado_de_outro(self):
        elegivel_a = self._compromisso(
            titulo="Cancelado tenant A", cancelado_em=timezone.now() - timedelta(days=10)
        )

        outro_tenant = Escritorio(
            schema_name="wi_purga_iso_b",
            nome="Tenant B purga",
            slug="wi-purga-iso-b",
        )
        with schema_context("public"):
            outro_tenant.save()
        try:
            with tenant_context(outro_tenant):
                responsavel_b = User.objects.create_user("responsavel_b", password="testpass")
                preservado_b = Compromisso.objects.create(
                    titulo="Ainda agendado tenant B",
                    data_hora_inicio=timezone.now() + timedelta(days=1),
                    status="agendado",
                    responsavel=responsavel_b,
                )

            self._rodar_comando()

            self.assertFalse(Compromisso.objects.filter(pk=elegivel_a.pk).exists())

            with tenant_context(outro_tenant):
                self.assertTrue(Compromisso.objects.filter(pk=preservado_b.pk).exists())
        finally:
            with schema_context("public"):
                outro_tenant.delete(force_drop=True)
