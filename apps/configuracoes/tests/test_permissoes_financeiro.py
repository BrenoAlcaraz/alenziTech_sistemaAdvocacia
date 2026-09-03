"""
Regressão: a tela /configuracoes/permissoes/ grava PermissaoPapel.nivel
direto via update_or_create, sem full_clean() — quem valida o valor é
só a CheckConstraint do banco (chk_permissaopapel_nivel). Os valores de
_MODULOS_CONFIG (apps/configuracoes/views.py) precisam continuar
batendo com NIVEIS_POR_MODULO/a constraint; um desalinhamento aparece
como IntegrityError (500), não como erro de validação tratado.

Ver specs/escopo-financeiro-lancamentos.md (apagada após promoção do
conhecimento durável para docs/STATUS.md/ARCHITECTURE.md).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PerfilUsuario, PermissaoPapel
from apps.accounts.permissoes_constants import (
    MODULO_FINANCEIRO,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_DADOS_TODOS,
)


class TestPermissoesFinanceiroNiveis(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "config_permissoes_financeiro_niveis"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.admin = User.objects.create_user("admin_perm_financeiro", password="testpass")
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.client.force_login(self.admin)

    def _post_nivel_financeiro(self, nivel):
        return self.client.post(
            "/configuracoes/permissoes/",
            {"tipo_conta": "financeiro", "ativo_financeiro": "on", "nivel_financeiro": nivel},
            HTTP_HOST=self.http_host,
        )

    def test_salva_nivel_dados_proprios(self):
        resposta = self._post_nivel_financeiro(NIVEL_DADOS_PROPRIOS)
        self.assertEqual(resposta.status_code, 200)
        permissao = PermissaoPapel.objects.get(tipo_conta="financeiro", modulo=MODULO_FINANCEIRO)
        self.assertTrue(permissao.ativo)
        self.assertEqual(permissao.nivel, NIVEL_DADOS_PROPRIOS)

    def test_salva_nivel_dados_todos(self):
        resposta = self._post_nivel_financeiro(NIVEL_DADOS_TODOS)
        self.assertEqual(resposta.status_code, 200)
        permissao = PermissaoPapel.objects.get(tipo_conta="financeiro", modulo=MODULO_FINANCEIRO)
        self.assertTrue(permissao.ativo)
        self.assertEqual(permissao.nivel, NIVEL_DADOS_TODOS)

    def test_nivel_invalido_cai_para_primeira_opcao(self):
        """Consistente com o fallback já existente em _build_modulos/POST de configuracoes/views.py."""
        resposta = self._post_nivel_financeiro("dados")
        self.assertEqual(resposta.status_code, 200)
        permissao = PermissaoPapel.objects.get(tipo_conta="financeiro", modulo=MODULO_FINANCEIRO)
        self.assertEqual(permissao.nivel, "solicitacoes")
