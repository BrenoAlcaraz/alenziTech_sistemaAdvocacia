"""Comando `criar_escritorio`: onboarding tudo-ou-nada de um escritório."""

import re
from io import StringIO
from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context, schema_exists

from apps.saas_tenants.models import ConfiguracaoVisual, Dominio, Escritorio

ARGS = {
    "nome": "Silva Advogados",
    "slug": "silva",
    "admin_usuario": "joao",
    "admin_email": "joao@silva.adv.br",
    "admin_nome": "João Silva",
}


def _criar(**extra):
    saida = StringIO()
    call_command("criar_escritorio", **{**ARGS, **extra}, stdout=saida)
    return saida.getvalue()


def _nada_criado(testcase, slug="silva"):
    testcase.assertFalse(Escritorio.objects.filter(slug=slug).exists())
    testcase.assertFalse(Dominio.objects.filter(domain__startswith=f"{slug}.").exists())
    testcase.assertFalse(ConfiguracaoVisual.objects.filter(escritorio__slug=slug).exists())
    testcase.assertFalse(schema_exists(slug))


class TestCriarEscritorio(TenantTestCase):
    """O tenant do TenantTestCase faz o papel de outro escritório já existente."""

    @classmethod
    def get_test_schema_name(cls):
        return "onboardingoutro"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Outro Escritório"
        tenant.slug = "onboardingoutro"

    def setUp(self):
        # TenantTestCase.setUpClass não chama o de SimpleTestCase, então
        # override_settings no nível da classe não seria aplicado.
        self.enterContext(override_settings(DOMINIO_BASE="localhost"))
        connection.set_schema_to_public()

    @override_settings(DEBUG=True)
    def test_cria_escritorio_pronto_para_o_dono(self):
        saida = _criar()
        senha = re.search(r"Senha:\s+(\S+)", saida).group(1)
        self.assertIn("http://silva.localhost:8000", saida)

        escritorio = Escritorio.objects.get(slug="silva")
        self.assertEqual(escritorio.schema_name, "silva")
        self.assertEqual(escritorio.get_primary_domain().domain, "silva.localhost")
        visual = escritorio.configuracao_visual
        self.assertEqual((visual.cor_primaria, visual.cor_secundaria), ("#1a1a1a", "#8B7355"))

        with schema_context("silva"):
            dono = User.objects.get(username="joao")
            self.assertFalse(dono.is_superuser)
            self.assertFalse(dono.is_staff)
            self.assertTrue(dono.perfil.is_admin_escritorio)
            self.assertEqual(dono.perfil.codigo, "ADM")
            self.assertEqual(dono.perfil.nome_completo, "João Silva")

        cliente = TenantClient(escritorio)
        login = cliente.post("/login/", {"username": "joao", "password": senha})
        self.assertRedirects(login, "/", fetch_redirect_response=False)
        self.assertEqual(cliente.get("/").status_code, 200)
        self.assertEqual(cliente.get("/configuracoes/").status_code, 200)
        self.assertEqual(cliente.get("/admin/").status_code, 404)

        # Isolamento: as credenciais do dono não valem no outro escritório.
        outro = TenantClient(self.tenant)
        outro.post("/login/", {"username": "joao", "password": senha})
        self.assertNotIn("_auth_user_id", outro.session)

    def test_falha_no_meio_nao_deixa_resto(self):
        with mock.patch(
            "apps.saas_tenants.onboarding._criar_dono", side_effect=RuntimeError("boom")
        ):
            with self.assertRaisesMessage(CommandError, "boom"):
                _criar()
        _nada_criado(self)

    def test_slug_existente_recusado(self):
        with self.assertRaisesMessage(CommandError, "Já existe"):
            _criar(slug="onboardingoutro")


@override_settings(DOMINIO_BASE="localhost")
class TestValidacaoAntesDeCriar(TestCase):
    def test_slug_reservado(self):
        for slug in ("admin", "www", "public", "mail"):
            with self.subTest(slug=slug), self.assertRaisesMessage(CommandError, "reservado"):
                _criar(slug=slug)
        _nada_criado(self, "admin")

    def test_slug_invalido(self):
        for slug in ("Silva", "1silva", "silva-adv", "silva_adv", "a" * 31, ""):
            with self.subTest(slug=slug), self.assertRaisesMessage(CommandError, "Slug inválido"):
                _criar(slug=slug)

    def test_email_invalido(self):
        with self.assertRaisesMessage(CommandError, "E-mail"):
            _criar(admin_email="nao-e-email")
        _nada_criado(self)

    @override_settings(DOMINIO_BASE="")
    def test_sem_dominio_base(self):
        with self.assertRaisesMessage(CommandError, "DOMINIO_BASE"):
            _criar()
        _nada_criado(self)


class TestSlugPermanenteNoAdmin(SimpleTestCase):
    def test_slug_e_schema_somente_leitura_na_edicao(self):
        modelo_admin = admin.site._registry[Escritorio]
        existente = Escritorio(slug="silva", schema_name="silva")
        self.assertTrue(
            {"slug", "schema_name"} <= set(modelo_admin.get_readonly_fields(None, existente))
        )
