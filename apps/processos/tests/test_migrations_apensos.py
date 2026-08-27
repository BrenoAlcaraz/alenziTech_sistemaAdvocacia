from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase


PROCESSOS_ANTES = ("processos", "0009_participantes_campos_obrigatorios")
PROCESSOS_DEPOIS = ("processos", "0010_vinculoprocessoapenso")


class TestMigrationApensosProcesso(TenantTestCase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "wi0007_apensos_migration"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0007 Migration Apensos"
        tenant.slug = "wi0007-migration-apensos"

    def _targets(self, executor, target):
        return [
            *[node for node in executor.loader.graph.leaf_nodes() if node[0] != "processos"],
            target,
        ]

    def _migrar(self, target):
        executor = MigrationExecutor(connection)
        targets = self._targets(executor, target)
        executor.migrate(targets)
        executor = MigrationExecutor(connection)
        targets = self._targets(executor, target)
        return executor.loader.project_state(targets).apps

    def test_rollback_reaplicacao_preservam_processos_e_recriam_tabela(self):
        self.assertEqual(connection.vendor, "postgresql")
        apps_antes = self._migrar(PROCESSOS_ANTES)
        User = apps_antes.get_model("auth", "User")
        Cliente = apps_antes.get_model("clientes", "Cliente")
        Processo = apps_antes.get_model("processos", "Processo")
        responsavel = User.objects.create(username="responsavel_migration_apensos")
        cliente = Cliente.objects.create(
            nome_razao_social="Cliente migration apensos",
            tipo="PF",
            responsavel_id=responsavel.pk,
        )
        processo_a = Processo.objects.create(
            titulo="Processo migration A",
            cliente_id=cliente.pk,
            responsavel_id=responsavel.pk,
        )
        processo_b = Processo.objects.create(
            titulo="Processo migration B",
            cliente_id=cliente.pk,
            responsavel_id=responsavel.pk,
        )

        apps_depois = self._migrar(PROCESSOS_DEPOIS)
        Vinculo = apps_depois.get_model("processos", "VinculoProcessoApenso")
        Vinculo.objects.create(
            processo_menor_id=min(processo_a.pk, processo_b.pk),
            processo_maior_id=max(processo_a.pk, processo_b.pk),
        )
        self.assertEqual(Vinculo.objects.count(), 1)
        self.assertIn("processos_vinculoprocessoapenso", connection.introspection.table_names())

        apps_rollback = self._migrar(PROCESSOS_ANTES)
        ProcessoRollback = apps_rollback.get_model("processos", "Processo")
        self.assertEqual(
            set(ProcessoRollback.objects.filter(pk__in=[processo_a.pk, processo_b.pk]).values_list("pk", flat=True)),
            {processo_a.pk, processo_b.pk},
        )
        self.assertNotIn("processos_vinculoprocessoapenso", connection.introspection.table_names())

        apps_reaplicado = self._migrar(PROCESSOS_DEPOIS)
        ProcessoReaplicado = apps_reaplicado.get_model("processos", "Processo")
        VinculoReaplicado = apps_reaplicado.get_model("processos", "VinculoProcessoApenso")
        self.assertEqual(
            set(ProcessoReaplicado.objects.filter(pk__in=[processo_a.pk, processo_b.pk]).values_list("pk", flat=True)),
            {processo_a.pk, processo_b.pk},
        )
        self.assertEqual(VinculoReaplicado.objects.count(), 0)
        self.assertIn("processos_vinculoprocessoapenso", connection.introspection.table_names())
