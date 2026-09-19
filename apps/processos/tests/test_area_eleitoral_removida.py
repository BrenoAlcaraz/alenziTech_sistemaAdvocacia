"""
"Eleitoral" saiu do catálogo de área do direito (specs/remover-area-eleitoral.md):
o catálogo único (`Processo.AREAS_CHOICES`, reusado por Modelos) não a oferece
e a migration de dados converte os registros existentes para "Outro".
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase
from django_tenants.test.cases import TenantTestCase

from apps.modelos.forms import AREAS_DIREITO
from apps.processos.forms import ProcessoForm
from apps.processos.models import Processo

from ._migration_targets import targets_seguros_para_rollback


PROCESSOS_ANTES = ("processos", "0022_processo_fase_andamento_atual")
PROCESSOS_DEPOIS = ("processos", "0023_remover_area_eleitoral")
MODELOS_ANTES = ("modelos", "0009_modelopeca_cliente")
MODELOS_DEPOIS = ("modelos", "0010_converter_area_eleitoral_para_outro")


class TestCatalogoSemEleitoral(SimpleTestCase):
    def test_catalogo_de_processo_nao_tem_eleitoral(self):
        self.assertNotIn("ELEITORAL", dict(Processo.AREAS_CHOICES))

    def test_catalogo_de_modelos_nao_tem_eleitoral(self):
        self.assertNotIn("ELEITORAL", dict(AREAS_DIREITO))

    def test_form_de_processo_rejeita_eleitoral(self):
        form = ProcessoForm(data={
            "titulo": "Processo", "area_direito": "ELEITORAL", "fase": "conhecimento",
            "instancia": "1ª Instância", "gratuidade_justica_status": "nao_requerida",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("area_direito", form.errors)


class TestMigracaoEleitoralParaOutro(TenantTestCase):
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
        return "area_eleitoral_migrations"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Migration Area Eleitoral"
        tenant.slug = "migration-area-eleitoral"

    def _migrar(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate(targets_seguros_para_rollback(executor.loader.graph, target))
        executor = MigrationExecutor(connection)
        return executor.loader.project_state(
            targets_seguros_para_rollback(executor.loader.graph, target)
        ).apps

    def test_processos_eleitorais_viram_outro_e_demais_areas_ficam(self):
        apps_antes = self._migrar(PROCESSOS_ANTES)
        User = apps_antes.get_model("auth", "User")
        Processo = apps_antes.get_model("processos", "Processo")
        responsavel = User.objects.create(username="resp_eleitoral", password="!", is_active=True)
        eleitoral = Processo.objects.create(
            titulo="Eleitoral", area_direito="ELEITORAL", responsavel_id=responsavel.pk
        )
        civel = Processo.objects.create(
            titulo="Cível", area_direito="CÍVEL", responsavel_id=responsavel.pk
        )

        apps_depois = self._migrar(PROCESSOS_DEPOIS)
        Processo = apps_depois.get_model("processos", "Processo")
        self.assertEqual(Processo.objects.get(pk=eleitoral.pk).area_direito, "OUTRO")
        self.assertEqual(Processo.objects.get(pk=civel.pk).area_direito, "CÍVEL")

        # Reversa é no-op: reverter e reaplicar não perde nem quebra registros.
        apps_rollback = self._migrar(PROCESSOS_ANTES)
        self.assertEqual(
            apps_rollback.get_model("processos", "Processo").objects.get(pk=eleitoral.pk).area_direito,
            "OUTRO",
        )
        apps_reaplicado = self._migrar(PROCESSOS_DEPOIS)
        self.assertEqual(apps_reaplicado.get_model("processos", "Processo").objects.count(), 2)

    def test_modelos_e_versoes_eleitorais_viram_outro(self):
        apps_antes = self._migrar(MODELOS_ANTES)
        Categoria = apps_antes.get_model("modelos", "CategoriaModeloPeca")
        ModeloPeca = apps_antes.get_model("modelos", "ModeloPeca")
        Versao = apps_antes.get_model("modelos", "VersaoModeloPeca")
        categoria = Categoria.objects.create(nome="Categoria migration eleitoral")
        modelo_eleitoral = ModeloPeca.objects.create(
            titulo="Modelo eleitoral", categoria_id=categoria.pk,
            area_direito="ELEITORAL", conteudo="x",
        )
        modelo_civel = ModeloPeca.objects.create(
            titulo="Modelo cível", categoria_id=categoria.pk,
            area_direito="CÍVEL", conteudo="x",
        )
        versao = Versao.objects.create(
            modelo_id=modelo_eleitoral.pk, titulo="v1", categoria_id=categoria.pk,
            area_direito="ELEITORAL", conteudo="x",
        )

        apps_depois = self._migrar(MODELOS_DEPOIS)
        ModeloPeca = apps_depois.get_model("modelos", "ModeloPeca")
        Versao = apps_depois.get_model("modelos", "VersaoModeloPeca")
        self.assertEqual(ModeloPeca.objects.get(pk=modelo_eleitoral.pk).area_direito, "OUTRO")
        self.assertEqual(ModeloPeca.objects.get(pk=modelo_civel.pk).area_direito, "CÍVEL")
        self.assertEqual(Versao.objects.get(pk=versao.pk).area_direito, "OUTRO")
