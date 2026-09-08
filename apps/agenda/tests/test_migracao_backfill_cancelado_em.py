"""
Teste da migration de dados `0006_backfill_cancelado_em` — regressão do
review final da spec `specs/agenda-participantes-confirmacao.md`:
compromisso cancelado antes da migration `0005` (sem `cancelado_em`)
precisa ganhar um valor, ou o job `expurgar_compromissos_cancelados`
nunca o expurga.

Chama a função da migration diretamente (mesmo padrão de simplicidade
usado no resto da suíte — sem introduzir dependência nova de teste de
migration): a função só usa `apps.get_model` e `QuerySet.update`, sem
comportamento dependente de estado histórico do model.
"""

import importlib

from django.apps import apps as app_registry
from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.agenda.models import Compromisso

_migration = importlib.import_module(
    "apps.agenda.migrations.0006_backfill_cancelado_em"
)


class TestBackfillCanceladoEm(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_backfill_cancelado_em"

    def setUp(self):
        super().setUp()
        self.responsavel = User.objects.create_user("responsavel", password="testpass")

    def _rodar_backfill(self):
        _migration.backfill_cancelado_em(app_registry, schema_editor=None)

    def test_preenche_cancelado_em_de_cancelado_legado(self):
        legado = Compromisso.objects.create(
            titulo="Cancelado Legado",
            data_hora_inicio=timezone.now(),
            status="cancelado",
            cancelado_em=None,
            responsavel=self.responsavel,
        )
        self._rodar_backfill()
        legado.refresh_from_db()
        self.assertIsNotNone(legado.cancelado_em)

    def test_nao_sobrescreve_cancelado_em_ja_preenchido(self):
        original = timezone.now() - timezone.timedelta(days=3)
        compromisso = Compromisso.objects.create(
            titulo="Cancelado Recente",
            data_hora_inicio=timezone.now(),
            status="cancelado",
            cancelado_em=original,
            responsavel=self.responsavel,
        )
        self._rodar_backfill()
        compromisso.refresh_from_db()
        self.assertEqual(compromisso.cancelado_em, original)

    def test_nao_afeta_compromisso_nao_cancelado(self):
        agendado = Compromisso.objects.create(
            titulo="Ainda Agendado",
            data_hora_inicio=timezone.now(),
            status="agendado",
            cancelado_em=None,
            responsavel=self.responsavel,
        )
        self._rodar_backfill()
        agendado.refresh_from_db()
        self.assertIsNone(agendado.cancelado_em)
