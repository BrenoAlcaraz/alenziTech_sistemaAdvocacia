from datetime import datetime, timezone as dt_timezone

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase

from ._migration_targets import targets_seguros_para_rollback


PROCESSOS_ANTES = ("processos", "0017_remove_processo_cliente_processo_clientes")
PROCESSOS_SCHEMA = ("processos", "0018_movimentacao_prazo_como_atributo")
PROCESSOS_DADOS = ("processos", "0019_migrar_tipo_prazo_para_data_prazo")


class TestMigrationPrazoComoAtributo(TenantTestCase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    @classmethod
    def get_test_schema_name(cls):
        return "wi0018_processos_migrations"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0018 Migration Prazo"
        tenant.slug = "wi0018-migration-prazo"

    def _targets(self, executor, target):
        return targets_seguros_para_rollback(executor.loader.graph, target)

    def _migrar(self, target):
        executor = MigrationExecutor(connection)
        targets = self._targets(executor, target)
        executor.migrate(targets)
        executor = MigrationExecutor(connection)
        targets = self._targets(executor, target)
        return executor.loader.project_state(targets).apps

    def _usuario(self, apps, username):
        User = apps.get_model("auth", "User")
        return User.objects.create(username=username, password="!", is_active=True)

    def test_prazo_vira_data_prazo_reclassifica_outro_e_preserva_legados(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.assertEqual(connection.schema_name, self.get_test_schema_name())

        apps_antes = self._migrar(PROCESSOS_ANTES)
        Processo = apps_antes.get_model("processos", "Processo")
        Movimentacao = apps_antes.get_model("processos", "MovimentacaoProcessual")

        responsavel = self._usuario(apps_antes, "responsavel_wi0018")
        processo = Processo.objects.create(
            titulo="Processo histórico WI-0018",
            responsavel_id=responsavel.pk,
        )

        data_prazo_legado = datetime(2026, 3, 5, 14, 30, tzinfo=dt_timezone.utc)
        mov_prazo = Movimentacao.objects.create(
            processo_id=processo.pk,
            descricao="Prazo lançado como tipo antigo",
            data=data_prazo_legado,
            tipo="prazo",
        )
        mov_andamento = Movimentacao.objects.create(
            processo_id=processo.pk,
            descricao="Andamento comum",
            data=datetime(2026, 2, 1, tzinfo=dt_timezone.utc),
            tipo="andamento",
        )
        mov_decisao = Movimentacao.objects.create(
            processo_id=processo.pk,
            descricao="Decisão legada",
            data=datetime(2026, 2, 2, tzinfo=dt_timezone.utc),
            tipo="decisao",
        )
        mov_audiencia = Movimentacao.objects.create(
            processo_id=processo.pk,
            descricao="Audiência legada",
            data=datetime(2026, 2, 3, tzinfo=dt_timezone.utc),
            tipo="audiencia",
        )
        mov_outro_preexistente = Movimentacao.objects.create(
            processo_id=processo.pk,
            descricao="Outro que já era outro antes da migration",
            data=datetime(2026, 2, 4, tzinfo=dt_timezone.utc),
            tipo="outro",
        )

        apps_schema = self._migrar(PROCESSOS_SCHEMA)
        MovimentacaoSchema = apps_schema.get_model("processos", "MovimentacaoProcessual")
        self.assertIsNone(
            MovimentacaoSchema.objects.get(pk=mov_prazo.pk).data_prazo
        )
        self.assertEqual(
            MovimentacaoSchema.objects.get(pk=mov_prazo.pk).tipo, "prazo"
        )

        apps_dados = self._migrar(PROCESSOS_DADOS)
        MovimentacaoDados = apps_dados.get_model("processos", "MovimentacaoProcessual")

        migrado = MovimentacaoDados.objects.get(pk=mov_prazo.pk)
        self.assertEqual(migrado.tipo, "outro")
        self.assertEqual(migrado.data_prazo, data_prazo_legado.date())

        self.assertEqual(
            MovimentacaoDados.objects.get(pk=mov_andamento.pk).tipo, "andamento"
        )
        self.assertIsNone(
            MovimentacaoDados.objects.get(pk=mov_andamento.pk).data_prazo
        )
        self.assertEqual(
            MovimentacaoDados.objects.get(pk=mov_decisao.pk).tipo, "decisao"
        )
        self.assertEqual(
            MovimentacaoDados.objects.get(pk=mov_audiencia.pk).tipo, "audiencia"
        )
        preexistente = MovimentacaoDados.objects.get(pk=mov_outro_preexistente.pk)
        self.assertEqual(preexistente.tipo, "outro")
        self.assertIsNone(preexistente.data_prazo)

        apps_rollback = self._migrar(PROCESSOS_ANTES)
        MovimentacaoRollback = apps_rollback.get_model("processos", "MovimentacaoProcessual")
        self.assertEqual(
            MovimentacaoRollback.objects.get(pk=mov_prazo.pk).tipo, "prazo"
        )
        self.assertEqual(
            MovimentacaoRollback.objects.get(pk=mov_outro_preexistente.pk).tipo,
            "outro",
        )
        self.assertEqual(MovimentacaoRollback.objects.count(), 5)

        apps_reaplicado = self._migrar(PROCESSOS_DADOS)
        MovimentacaoReaplicada = apps_reaplicado.get_model(
            "processos", "MovimentacaoProcessual"
        )
        reaplicado = MovimentacaoReaplicada.objects.get(pk=mov_prazo.pk)
        self.assertEqual(reaplicado.tipo, "outro")
        self.assertEqual(reaplicado.data_prazo, data_prazo_legado.date())
