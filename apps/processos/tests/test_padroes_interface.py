"""Padrões de interface de Processos: barra de filtros, visão Ativos/Arquivados,
uma ação primária por tela e badge de status próprio."""

import re

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PerfilUsuario
from apps.processos.models import Processo
from apps.saas_tenants.models import Dominio


class TestPadroesDeInterfaceProcessos(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "ui04_processos_interface"

    def setUp(self):
        super().setUp()
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.user = User.objects.create_user(username="admin_ui", password="x")
        PerfilUsuario.objects.filter(user=self.user).update(is_admin_escritorio=True)
        self.client.force_login(self.user)
        self.processo = Processo.objects.create(
            titulo="Ação de cobrança", responsavel=self.user, status="suspenso",
        )

    def _html(self, url):
        resposta = self.client.get(url, HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        return resposta.content.decode()

    def test_lista_usa_barra_de_filtros_unica_sem_botao_primario(self):
        conteudo = self._html("/processos/")
        self.assertIn("data-filtros", conteudo)
        self.assertIn('<noscript><button type="submit" class="btn-secondary">Filtrar</button></noscript>', conteudo)
        self.assertNotIn("Limpar filtros", conteudo)
        self.assertEqual(conteudo.count("btn-primary"), 1)

    def test_limpar_filtros_aparece_com_filtro_ativo_e_preserva_escopo(self):
        conteudo = self._html("/processos/?busca=cobran&escopo=todos")
        self.assertIn('href="/processos/?escopo=todos" class="barra-filtros-limpar"', conteudo)

    def test_visao_ativos_arquivados_e_controle_visivel(self):
        lista = self._html("/processos/?escopo=todos")
        self.assertIn('href="/processos/arquivados/?escopo=todos" class="visao-alternar-item"', lista)
        self.assertNotIn("Ver processos arquivados", lista)
        arquivados = self._html("/processos/arquivados/?escopo=todos")
        self.assertRegex(arquivados, r'class="visao-alternar-item" aria-current="page">Arquivados<')

    def test_detalhe_tem_uma_primaria_e_acoes_raras_no_menu(self):
        conteudo = self._html(f"/processos/{self.processo.pk}/")
        self.assertEqual(conteudo.count("btn-primary"), 1)
        menu = conteudo[conteudo.index("Mais ações"):]
        self.assertIn("Arquivar processo", menu)
        self.assertIn("Excluir processo", menu)

    def test_status_usa_badge_proprio(self):
        conteudo = self._html(f"/processos/{self.processo.pk}/")
        self.assertIn('class="badge-status badge-status-suspenso">Suspenso<', conteudo)
        self.assertIsNone(re.search(r'badge-area">\s*Suspenso', conteudo))
