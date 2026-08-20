from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PerfilUsuario, PermissaoPapel
from apps.accounts.permissoes_constants import MODULO_PROCESSOS, NIVEL_TODOS
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.processos.services import AdministradorResponsavelIndisponivel


class TestPerdaAcessoProcessosNaConfiguracao(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0005_config_perda_acesso"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.admin = User.objects.create_user("admin_config", password="testpass")
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.limitado = User.objects.create_user("limitado_config", password="testpass")
        self.limitado.groups.add(Group.objects.get(name="limitado"))
        PermissaoPapel.objects.update_or_create(
            tipo_conta="limitado",
            modulo=MODULO_PROCESSOS,
            defaults={"ativo": True, "nivel": NIVEL_TODOS},
        )
        cliente = Cliente.objects.create(
            tipo="PF",
            nome_razao_social="Cliente Config",
            responsavel=self.admin,
        )
        self.processo = Processo.objects.create(
            titulo="Processo Config",
            cliente=cliente,
            responsavel=self.limitado,
        )
        self.client.force_login(self.admin)

    def _post_revogacao(self):
        return self.client.post(
            "/configuracoes/permissoes/",
            {"tipo_conta": "limitado", "nivel_processos": "somente_seus"},
            HTTP_HOST=self.http_host,
        )

    def test_revogacao_transfere_para_admin_e_reconcessao_nao_devolve(self):
        resposta = self._post_revogacao()
        self.assertEqual(resposta.status_code, 200)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.admin.pk)

        resposta = self.client.post(
            "/configuracoes/permissoes/",
            {
                "tipo_conta": "limitado",
                "ativo_processos": "on",
                "nivel_processos": "todos",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 200)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.admin.pk)

    def test_falha_na_transferencia_reverte_a_alteracao_de_permissao(self):
        with patch(
            "apps.processos.services._administrador_ativo",
            side_effect=AdministradorResponsavelIndisponivel("sem admin"),
        ):
            with self.assertRaises(AdministradorResponsavelIndisponivel):
                self._post_revogacao()

        permissao = PermissaoPapel.objects.get(
            tipo_conta="limitado", modulo=MODULO_PROCESSOS
        )
        self.assertTrue(permissao.ativo)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.limitado.pk)
