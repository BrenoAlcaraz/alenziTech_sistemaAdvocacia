from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase

from apps.accounts.forms import EquipeForm
from apps.accounts.models import (
    Equipe,
    HabilitacaoPapel,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import HAB_GERIR_CRIAR_EQUIPE, MODULO_GERIR
from apps.processos.tests._migration_targets import targets_seguros_para_rollback


class TestEquipeSemHierarquia(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_accounts_equipe_sem_hierarquia"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        gestor = User.objects.create_user("gestor_sem_hierarquia", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Equipes sem hierarquia")
        UsuarioPapel.objects.create(usuario=gestor, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR,
            item=HAB_GERIR_CRIAR_EQUIPE, ativo=True,
        )
        self.client.force_login(gestor)
        self.equipe = Equipe.objects.create(nome="Equipe Cível", ativo=True)

    def test_form_nao_expoe_equipe_pai(self):
        self.assertEqual(list(EquipeForm().fields), ["nome", "descricao", "ativo"])

    def test_lista_de_equipes_renderiza_sem_coluna_equipe_pai(self):
        resposta = self.client.get("/configuracoes/equipes/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Equipe Cível")
        self.assertNotContains(resposta, "Equipe pai")

    def test_telas_de_criar_e_editar_renderizam_sem_campo(self):
        for url in (
            "/configuracoes/equipes/novo/",
            f"/configuracoes/equipes/{self.equipe.pk}/editar/",
        ):
            resposta = self.client.get(url, HTTP_HOST=self.http_host)
            self.assertEqual(resposta.status_code, 200)
            self.assertNotContains(resposta, "Equipe pai")

    def test_criar_e_editar_equipe_persistem(self):
        resposta = self.client.post(
            "/configuracoes/equipes/novo/",
            {"nome": "Equipe Nova", "descricao": "", "ativo": "on"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Equipe.objects.filter(nome="Equipe Nova").exists())

        resposta = self.client.post(
            f"/configuracoes/equipes/{self.equipe.pk}/editar/",
            {"nome": "Equipe Cível 2", "descricao": "x", "ativo": "on"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.equipe.refresh_from_db()
        self.assertEqual(self.equipe.nome, "Equipe Cível 2")


ACCOUNTS_ANTES = ("accounts", "0030_equipevinculada_vinculointegrante")
ACCOUNTS_DEPOIS = ("accounts", "0031_remove_equipe_pai")


class TestMigrationRemoveEquipePai(TenantTestCase):
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
        return "wi_accounts_migration_equipe_pai"

    def _migrar(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate(targets_seguros_para_rollback(executor.loader.graph, target))
        executor = MigrationExecutor(connection)
        targets = targets_seguros_para_rollback(executor.loader.graph, target)
        return executor.loader.project_state(targets).apps

    def _colunas_equipe(self):
        with connection.cursor() as cursor:
            descricao = connection.introspection.get_table_description(cursor, "accounts_equipe")
        return {coluna.name for coluna in descricao}

    def test_remove_coluna_preservando_equipes_com_equipe_pai(self):
        self.assertEqual(connection.vendor, "postgresql")
        apps_antes = self._migrar(ACCOUNTS_ANTES)
        EquipeAntes = apps_antes.get_model("accounts", "Equipe")
        pai = EquipeAntes.objects.create(nome="Equipe Pai")
        filha = EquipeAntes.objects.create(nome="Equipe Filha", equipe_pai_id=pai.pk)
        self.assertIn("equipe_pai_id", self._colunas_equipe())

        apps_depois = self._migrar(ACCOUNTS_DEPOIS)
        EquipeDepois = apps_depois.get_model("accounts", "Equipe")
        self.assertNotIn("equipe_pai_id", self._colunas_equipe())
        self.assertEqual(
            set(EquipeDepois.objects.filter(pk__in=[pai.pk, filha.pk]).values_list("nome", flat=True)),
            {"Equipe Pai", "Equipe Filha"},
        )
