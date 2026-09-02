from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase

from ._migration_targets import targets_seguros_para_rollback


PROCESSOS_ANTES = ("processos", "0004_rename_departamento_equipe")
PROCESSOS_BACKFILL = ("processos", "0005_normalizar_responsavel")
PROCESSOS_DEPOIS = ("processos", "0006_responsavel_obrigatorio")


class TestMigrationResponsavelProcesso(TenantTestCase):
    # Migration 0005 atualiza FKs e 0006 executa ALTER TABLE em seguida. O
    # TestCase atômico usado por TenantTestCase manteria as fixtures históricas
    # com eventos de trigger pendentes até o fim do método, uma condição que não
    # existe na execução real entre migrations. Esta classe usa o isolamento de
    # TransactionTestCase e preserva apenas o lifecycle de schema do tenant.
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "wi0005_processos_migrations"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0005 Migration Processos"
        tenant.slug = "wi0005-migration-processos"

    def _targets_com_processos_em(self, executor, target):
        return targets_seguros_para_rollback(executor.loader.graph, target)

    def _migrar_processos_para(self, target):
        executor = MigrationExecutor(connection)
        targets = self._targets_com_processos_em(executor, target)
        executor.migrate(targets)

        executor = MigrationExecutor(connection)
        targets = self._targets_com_processos_em(executor, target)
        return executor.loader.project_state(targets).apps

    def _coluna_responsavel_aceita_nulo(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'processos_processo'
                  AND column_name = 'responsavel_id'
                """,
                [connection.schema_name],
            )
            resultado = cursor.fetchone()
        self.assertIsNotNone(resultado)
        return resultado[0] == "YES"

    def _migration_aplicada(self, target):
        return MigrationRecorder(connection).migration_qs.filter(
            app=target[0],
            name=target[1],
        ).exists()

    def _criar_usuario(self, apps, username, *, is_active=True):
        User = apps.get_model("auth", "User")
        return User.objects.create(
            username=username,
            password="!",
            is_active=is_active,
        )

    def _criar_admin(self, apps, username="admin_migration"):
        admin = self._criar_usuario(apps, username)
        PerfilUsuario = apps.get_model("accounts", "PerfilUsuario")
        PerfilUsuario.objects.create(
            user_id=admin.pk,
            is_admin_escritorio=True,
        )
        return admin

    def _autorizar_processos(self, apps, user):
        PermissaoUsuario = apps.get_model("accounts", "PermissaoUsuario")
        PermissaoUsuario.objects.create(
            usuario_id=user.pk,
            modulo="processos",
            ativo=True,
            nivel="somente_seus",
        )

    def _assert_infraestrutura_real_do_tenant(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.assertEqual(
            connection.settings_dict["ENGINE"],
            "django_tenants.postgresql_backend",
        )
        self.assertEqual(connection.schema_name, self.get_test_schema_name())

    def test_backfill_rollback_e_reaplicacao_preservam_processos(self):
        self._assert_infraestrutura_real_do_tenant()
        apps_antes = self._migrar_processos_para(PROCESSOS_ANTES)
        ProcessoAntes = apps_antes.get_model("processos", "Processo")

        admin = self._criar_admin(apps_antes)
        responsavel_valido = self._criar_usuario(
            apps_antes, "responsavel_valido_migration"
        )
        self._autorizar_processos(apps_antes, responsavel_valido)
        responsavel_inelegivel = self._criar_usuario(
            apps_antes, "responsavel_inelegivel_migration"
        )

        processo_valido = ProcessoAntes.objects.create(
            titulo="Processo com responsável válido",
            responsavel_id=responsavel_valido.pk,
        )
        processo_nulo = ProcessoAntes.objects.create(
            titulo="Processo com responsável nulo",
            responsavel_id=None,
        )
        processo_inelegivel = ProcessoAntes.objects.create(
            titulo="Processo com responsável inelegível",
            responsavel_id=responsavel_inelegivel.pk,
        )
        ids_originais = {
            processo_valido.pk,
            processo_nulo.pk,
            processo_inelegivel.pk,
        }

        self.assertTrue(self._coluna_responsavel_aceita_nulo())
        self.assertFalse(self._migration_aplicada(PROCESSOS_BACKFILL))
        self.assertFalse(self._migration_aplicada(PROCESSOS_DEPOIS))

        apps_depois = self._migrar_processos_para(PROCESSOS_DEPOIS)
        ProcessoDepois = apps_depois.get_model("processos", "Processo")
        responsaveis_depois = dict(
            ProcessoDepois.objects.filter(pk__in=ids_originais).values_list(
                "pk", "responsavel_id"
            )
        )

        self.assertEqual(set(responsaveis_depois), ids_originais)
        self.assertEqual(responsaveis_depois[processo_valido.pk], responsavel_valido.pk)
        self.assertEqual(responsaveis_depois[processo_nulo.pk], admin.pk)
        self.assertEqual(responsaveis_depois[processo_inelegivel.pk], admin.pk)
        self.assertFalse(self._coluna_responsavel_aceita_nulo())
        self.assertFalse(
            ProcessoDepois._meta.get_field("responsavel").null,
        )
        self.assertTrue(self._migration_aplicada(PROCESSOS_BACKFILL))
        self.assertTrue(self._migration_aplicada(PROCESSOS_DEPOIS))

        apps_rollback = self._migrar_processos_para(PROCESSOS_ANTES)
        ProcessoRollback = apps_rollback.get_model("processos", "Processo")
        self.assertEqual(
            set(
                ProcessoRollback.objects.filter(pk__in=ids_originais).values_list(
                    "pk", flat=True
                )
            ),
            ids_originais,
        )
        self.assertTrue(self._coluna_responsavel_aceita_nulo())
        self.assertFalse(self._migration_aplicada(PROCESSOS_BACKFILL))
        self.assertFalse(self._migration_aplicada(PROCESSOS_DEPOIS))

        apps_reaplicado = self._migrar_processos_para(PROCESSOS_DEPOIS)
        ProcessoReaplicado = apps_reaplicado.get_model("processos", "Processo")
        responsaveis_reaplicados = dict(
            ProcessoReaplicado.objects.filter(pk__in=ids_originais).values_list(
                "pk", "responsavel_id"
            )
        )
        self.assertEqual(set(responsaveis_reaplicados), ids_originais)
        self.assertEqual(
            responsaveis_reaplicados[processo_valido.pk], responsavel_valido.pk
        )
        self.assertEqual(responsaveis_reaplicados[processo_nulo.pk], admin.pk)
        self.assertEqual(responsaveis_reaplicados[processo_inelegivel.pk], admin.pk)
        self.assertFalse(self._coluna_responsavel_aceita_nulo())
        self.assertTrue(self._migration_aplicada(PROCESSOS_BACKFILL))
        self.assertTrue(self._migration_aplicada(PROCESSOS_DEPOIS))

    def test_sem_admin_falha_sem_aplicar_backfill_nem_perder_dados(self):
        self._assert_infraestrutura_real_do_tenant()
        apps_antes = self._migrar_processos_para(PROCESSOS_ANTES)
        ProcessoAntes = apps_antes.get_model("processos", "Processo")
        processo = ProcessoAntes.objects.create(
            titulo="Processo sem Admin para backfill",
            responsavel_id=None,
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "é necessário exatamente um Administrador ativo",
        ):
            self._migrar_processos_para(PROCESSOS_DEPOIS)

        executor = MigrationExecutor(connection)
        targets_apos_falha = self._targets_com_processos_em(
            executor, PROCESSOS_ANTES
        )
        apps_apos_falha = executor.loader.project_state(targets_apos_falha).apps
        ProcessoAposFalha = apps_apos_falha.get_model("processos", "Processo")
        processo_preservado = ProcessoAposFalha.objects.get(pk=processo.pk)
        self.assertIsNone(processo_preservado.responsavel_id)
        self.assertEqual(ProcessoAposFalha.objects.count(), 1)
        self.assertTrue(self._coluna_responsavel_aceita_nulo())

        self.assertFalse(self._migration_aplicada(PROCESSOS_BACKFILL))
        self.assertFalse(self._migration_aplicada(PROCESSOS_DEPOIS))

        admin = self._criar_admin(apps_apos_falha, "admin_apos_falha")
        apps_recuperado = self._migrar_processos_para(PROCESSOS_DEPOIS)
        ProcessoRecuperado = apps_recuperado.get_model("processos", "Processo")
        processo_recuperado = ProcessoRecuperado.objects.get(pk=processo.pk)
        self.assertEqual(processo_recuperado.responsavel_id, admin.pk)
        self.assertFalse(self._coluna_responsavel_aceita_nulo())
