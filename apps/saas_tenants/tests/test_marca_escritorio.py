"""Marca do escritório no layout: título da aba e logo padrão por iniciais."""

from django.contrib.auth.models import User
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PerfilUsuario
from apps.saas_tenants.context_processors import iniciais
from apps.saas_tenants.models import ConfiguracaoVisual, Dominio

# Trecho do desenho da balança da justiça, antigo logo padrão.
BALANCA = "M3 6l3 1m0 0l-3 9"


class TestIniciais(SimpleTestCase):
    def test_duas_primeiras_palavras_significativas(self):
        self.assertEqual(iniciais("Silva & Souza Advogados"), "SS")
        self.assertEqual(iniciais("Escritório de Advocacia Lima"), "EL")
        self.assertEqual(iniciais("mendes"), "M")

    def test_nome_so_com_conectivos_usa_o_proprio_nome(self):
        self.assertEqual(iniciais("Advocacia"), "A")

    def test_nome_vazio(self):
        self.assertEqual(iniciais(""), "")


class TestMarcaDoEscritorioNoLayout(TenantTestCase):
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Silva & Souza Advogados"
        tenant.slug = "marca-escritorio"

    @classmethod
    def get_test_schema_name(cls):
        return "ui04_marca_escritorio"

    def setUp(self):
        super().setUp()
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        user = User.objects.create_user(username="admin_marca", password="x")
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        self.client.force_login(user)

    def test_aba_do_navegador_mostra_pagina_e_nome_do_escritorio(self):
        conteudo = self.client.get("/processos/", HTTP_HOST=self.http_host).content.decode()
        self.assertIn("<title>Processos · Silva &amp; Souza Advogados</title>", conteudo)
        self.assertNotIn("Jurídico SaaS", conteudo)

    def test_nome_de_exibicao_tem_precedencia(self):
        ConfiguracaoVisual.objects.update_or_create(
            escritorio=self.tenant, defaults={"nome_exibicao": "Lima Advocacia"},
        )
        conteudo = self.client.get("/processos/", HTTP_HOST=self.http_host).content.decode()
        self.assertIn("<title>Processos · Lima Advocacia</title>", conteudo)

    def test_sem_logo_mostra_iniciais_e_nao_a_balanca(self):
        conteudo = self.client.get("/processos/", HTTP_HOST=self.http_host).content.decode()
        self.assertNotIn(BALANCA, conteudo)
        self.assertRegex(conteudo, r'class="[^"]*text-primaria[^"]*">\s*SS\s*<')
