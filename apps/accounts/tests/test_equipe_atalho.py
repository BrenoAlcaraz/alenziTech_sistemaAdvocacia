"""
Equipe como atalho de seleção (PDR-0028): helper compartilhado
(`apps/accounts/equipe_atalho.py`) e migration que remove o vínculo
dinâmico de Equipe (EquipeVinculada/VinculoIntegrante).
"""

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase

from apps.accounts.equipe_atalho import SelecionarMembrosEquipeForm, dados_para_js
from apps.accounts.models import Equipe, MembroEquipe
from apps.processos.tests._migration_targets import targets_seguros_para_rollback


class TestHelperEquipeAtalho(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0028_accounts_helper"

    def setUp(self):
        super().setUp()
        self.ana = User.objects.create_user("ana_helper", password="x", first_name="Ana", last_name="Silva")
        self.beto = User.objects.create_user("beto_helper", password="x")
        self.inativo = User.objects.create_user("inativo_helper", password="x", is_active=False)
        self.equipe = Equipe.objects.create(nome="Contabilidade")
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.beto, equipe=self.equipe, ativo=False)
        MembroEquipe.objects.create(usuario=self.inativo, equipe=self.equipe, ativo=True)

    def test_dados_trazem_so_membros_ativos_e_elegiveis(self):
        dados = dados_para_js(User.objects.all(), presentes=[self.ana.pk])
        self.assertEqual(
            dados["equipes"],
            {str(self.equipe.pk): {"nome": "Contabilidade", "membros": [{"id": self.ana.pk, "nome": "Ana Silva"}]}},
        )
        self.assertEqual(dados["presentes"], [self.ana.pk])

    def test_dados_filtram_por_universo_elegivel(self):
        dados = dados_para_js(User.objects.filter(pk=self.beto.pk))
        self.assertEqual(dados["equipes"][str(self.equipe.pk)]["membros"], [])

    def test_equipe_inativa_fica_de_fora(self):
        self.equipe.ativo = False
        self.equipe.save()
        self.assertEqual(dados_para_js(User.objects.all())["equipes"], {})

    def test_form_aceita_membro_ativo_e_rejeita_quem_nao_e(self):
        universo = User.objects.filter(is_active=True)
        valido = SelecionarMembrosEquipeForm(
            {"equipe": self.equipe.pk, "usuarios": [self.ana.pk]}, usuarios_elegiveis=universo
        )
        self.assertTrue(valido.is_valid())
        for intruso in (self.beto, self.inativo):
            invalido = SelecionarMembrosEquipeForm(
                {"equipe": self.equipe.pk, "usuarios": [intruso.pk]},
                usuarios_elegiveis=User.objects.all(),
            )
            self.assertFalse(invalido.is_valid(), intruso.username)

    def test_form_rejeita_usuario_fora_do_universo_elegivel(self):
        form = SelecionarMembrosEquipeForm(
            {"equipe": self.equipe.pk, "usuarios": [self.ana.pk]},
            usuarios_elegiveis=User.objects.exclude(pk=self.ana.pk),
        )
        self.assertFalse(form.is_valid())

    def test_mecanismo_de_vinculo_dinamico_nao_existe_mais(self):
        nomes = {modelo.__name__ for modelo in django_apps.get_app_config("accounts").get_models()}
        self.assertNotIn("EquipeVinculada", nomes)
        self.assertNotIn("VinculoIntegrante", nomes)


ACCOUNTS_ANTES = ("accounts", "0031_remove_equipe_pai")
ACCOUNTS_DEPOIS = ("accounts", "0032_remove_equipe_vinculada_vinculo_integrante")


class TestMigrationRemoveVinculoEquipe(TenantTestCase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    def tearDown(self):
        # Recoloca o schema no HEAD antes do flush (ver test_migrations_apensos).
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    @classmethod
    def get_test_schema_name(cls):
        return "pdr0028_accounts_migration"

    def _migrar(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate(targets_seguros_para_rollback(executor.loader.graph, target))
        executor = MigrationExecutor(connection)
        targets = targets_seguros_para_rollback(executor.loader.graph, target)
        return executor.loader.project_state(targets).apps

    def _tabelas(self):
        with connection.cursor() as cursor:
            return set(connection.introspection.table_names(cursor))

    def test_apaga_vinculos_e_preserva_pessoas_ja_materializadas(self):
        self.assertEqual(connection.vendor, "postgresql")
        apps_antes = self._migrar(ACCOUNTS_ANTES)
        Usuario = apps_antes.get_model("auth", "User")
        EquipeAntes = apps_antes.get_model("accounts", "Equipe")
        EquipeVinculada = apps_antes.get_model("accounts", "EquipeVinculada")
        VinculoIntegrante = apps_antes.get_model("accounts", "VinculoIntegrante")
        ContentType = apps_antes.get_model("contenttypes", "ContentType")
        Processo = apps_antes.get_model("processos", "Processo")

        responsavel = Usuario.objects.create(username="responsavel_migracao")
        ana = Usuario.objects.create(username="ana_migracao")
        equipe = EquipeAntes.objects.create(nome="Equipe Migração")
        processo = Processo.objects.create(titulo="Processo Migração", responsavel_id=responsavel.pk)
        processo.integrantes_habilitados.add(ana)
        ct, _ = ContentType.objects.get_or_create(app_label="processos", model="processo")
        EquipeVinculada.objects.create(content_type=ct, object_id=processo.pk, equipe=equipe)
        VinculoIntegrante.objects.create(
            content_type=ct, object_id=processo.pk, usuario=ana, equipe=equipe
        )
        self.assertIn("accounts_equipevinculada", self._tabelas())

        apps_depois = self._migrar(ACCOUNTS_DEPOIS)

        tabelas = self._tabelas()
        self.assertNotIn("accounts_equipevinculada", tabelas)
        self.assertNotIn("accounts_vinculointegrante", tabelas)
        ProcessoDepois = apps_depois.get_model("processos", "Processo")
        self.assertEqual(
            list(
                ProcessoDepois.objects.get(pk=processo.pk)
                .integrantes_habilitados.values_list("username", flat=True)
            ),
            ["ana_migracao"],
        )
        self.assertTrue(apps_depois.get_model("accounts", "Equipe").objects.filter(pk=equipe.pk).exists())
