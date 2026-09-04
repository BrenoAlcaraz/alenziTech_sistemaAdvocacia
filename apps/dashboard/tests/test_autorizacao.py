"""
Teste de autorização de módulo para apps/dashboard/views.py (`painel`).

Cobre o enforcement de tem_permissao_modulo(user, MODULO_PAINEL) na rota
`dashboard:painel` (ver specs/autorizacao-modulo-painel.md). Os blocos
internos do painel (clientes/processos/tarefas/agenda/financeiro)
continuam gated pelo módulo de origem — já cobertos por
apps/dashboard/tests/test_painel.py e test_escopo.py.

Segue o mesmo padrão de fixtures de apps/clientes/tests/test_autorizacao.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_PAINEL, NIVEL_TODOS


class PainelAutorizacaoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=ativo, nivel=nivel
        )

    def _admin(self, username="admin_painel"):
        admin = self._user(username)
        PerfilUsuario.objects.filter(user=admin).update(is_admin_escritorio=True)
        return admin


class TestPainelAutorizacaoModuloNegado(PainelAutorizacaoBase):
    """Usuário sem autorização do módulo `painel` — a rota nega."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_painel_negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_painel")
        self.client.force_login(self.user)

    def test_painel_negado(self):
        r = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestPainelAutorizacaoModuloConcedido(PainelAutorizacaoBase):
    """Usuário autorizado ao módulo `painel` (via papel dinâmico) acessa normalmente."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_painel_concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_painel")
        papel = self._new_papel("Papel Painel Concedido")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_PAINEL)
        self.client.force_login(self.user)

    def test_painel_autorizado(self):
        r = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "dashboard/painel.html")


class TestPainelAutorizacaoAdminIndependeDoModulo(PainelAutorizacaoBase):
    """Administrador do escritório acessa o painel sem nenhum PermissaoPapel."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_painel_admin"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.client.force_login(self.admin)

    def test_painel_autorizado_para_admin(self):
        r = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "dashboard/painel.html")
