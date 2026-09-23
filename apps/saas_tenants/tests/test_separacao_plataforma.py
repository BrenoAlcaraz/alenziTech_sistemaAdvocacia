"""Isolamento entre o domínio da plataforma (schema `public`, Django
Admin) e os domínios de escritório (telas do sistema)."""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.saas_tenants.models import Dominio, Escritorio

HOST_PLATAFORMA = "localhost"
APPS_SO_DE_ESCRITORIO = set(settings.TENANT_APPS) - set(settings.SHARED_APPS)


class TestDominioDaPlataforma(TestCase):
    @classmethod
    def setUpTestData(cls):
        plataforma = Escritorio(schema_name="public", nome="Plataforma", slug="plataforma")
        plataforma.save()
        Dominio.objects.create(tenant=plataforma, domain=HOST_PLATAFORMA, is_primary=True)

    def _get(self, caminho):
        return self.client.get(caminho, HTTP_HOST=HOST_PLATAFORMA)

    def test_raiz_redireciona_para_admin(self):
        resposta = self._get("/")
        self.assertRedirects(resposta, "/admin/", fetch_redirect_response=False)

    def test_telas_de_escritorio_nao_existem(self):
        for caminho in ("/login/", "/processos/", "/clientes/", "/financeiro/"):
            with self.subTest(caminho=caminho):
                self.assertEqual(self._get(caminho).status_code, 404)

    def test_superuser_faz_login_ve_plataforma_e_faz_logout(self):
        # Criar no public não pode tentar criar PerfilUsuario (tabela inexistente).
        User.objects.create_superuser("plataforma", "p@example.com", "senha-forte-123")

        login = self.client.post(
            "/admin/login/",
            {"username": "plataforma", "password": "senha-forte-123", "next": "/admin/"},
            HTTP_HOST=HOST_PLATAFORMA,
        )
        self.assertRedirects(login, "/admin/", fetch_redirect_response=False)

        indice = self._get("/admin/")
        self.assertEqual(indice.status_code, 200)
        for changelist in (
            "/admin/saas_tenants/escritorio/",
            "/admin/saas_tenants/dominio/",
            "/admin/saas_tenants/configuracaovisual/",
            "/admin/saas_billing/plano/",
            "/admin/saas_billing/assinatura/",
        ):
            with self.subTest(changelist=changelist):
                self.assertContains(indice, changelist)
                self.assertEqual(self._get(changelist).status_code, 200)

        logout = self.client.post("/admin/logout/", HTTP_HOST=HOST_PLATAFORMA)
        self.assertRedirects(logout, "/admin/login/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_da_plataforma_nao_pode_ser_excluido_so_desativado(self):
        admin_plataforma = User.objects.create_superuser("plataforma", "p@example.com", "senha-forte-123")
        outro = User.objects.create_user("suporte", "s@example.com", "senha-forte-123", is_staff=True)
        self.client.force_login(admin_plataforma)

        edicao = self._get(f"/admin/auth/user/{outro.pk}/change/")
        self.assertContains(edicao, 'name="is_active"')
        self.assertNotContains(edicao, f"/admin/auth/user/{outro.pk}/delete/")

        self.assertEqual(self._get(f"/admin/auth/user/{outro.pk}/delete/").status_code, 403)
        self.assertNotContains(self._get("/admin/auth/user/"), 'value="delete_selected"')

        self.client.post(
            "/admin/auth/user/",
            {"action": "delete_selected", "_selected_action": [outro.pk], "post": "yes"},
            HTTP_HOST=HOST_PLATAFORMA,
        )
        self.assertTrue(User.objects.filter(pk=outro.pk).exists())


class TestAdminSemModelsDeEscritorio(SimpleTestCase):
    def test_nenhum_model_de_escritorio_registrado(self):
        registrados = {
            model._meta.app_config.name
            for model in admin.site._registry
            if model._meta.app_config.name in APPS_SO_DE_ESCRITORIO
        }
        self.assertEqual(registrados, set())


class TestSessaoNaoCompartilhadaEntreSubdominios(SimpleTestCase):
    def test_session_cookie_domain_nao_definido(self):
        self.assertIsNone(settings.SESSION_COOKIE_DOMAIN)


class TestDominioDeEscritorioSemAdmin(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "sep_plataforma"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Escritório Separação"
        tenant.slug = "sep-plataforma"

    def setUp(self):
        self.client = TenantClient(self.tenant)

    def test_admin_responde_404(self):
        for caminho in ("/admin/", "/admin/login/"):
            with self.subTest(caminho=caminho):
                self.assertEqual(self.client.get(caminho).status_code, 404)

    def test_superuser_do_escritorio_nao_acessa_admin(self):
        User.objects.create_superuser("super", "s@example.com", "senha-forte-123")
        self.client.login(username="super", password="senha-forte-123")
        self.assertEqual(self.client.get("/admin/").status_code, 404)
