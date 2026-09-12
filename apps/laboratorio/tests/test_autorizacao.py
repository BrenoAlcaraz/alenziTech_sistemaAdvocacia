"""
Testes de autorização de apps/laboratorio/views.py::index.

Até aqui o shell usava só @login_required — qualquer usuário autenticado
do tenant acessava a rota, independente de ter o módulo `processos` ou a
habilitação `processos_usar_laboratorio` (já definida no kernel desde
PDR-0010/PDR-0008, mas sem nenhum ponto de aplicação — ver
docs/STATUS.md e docs/modules/processos.md). Este arquivo cobre a
aplicação do padrão de duas camadas já usado no restante de Processos
(módulo autorizado + habilitação granular).

Segue o mesmo padrão de fixtures de
apps/processos/tests/test_autorizacao.py sobre
django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_PROCESSOS_USAR_LABORATORIO,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)


class LaboratorioAutorizacaoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _set_admin_flag(self, user, value=True):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=value)

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=ativo, nivel=nivel
        )

    def _hp(self, papel, modulo, item, *, ativo=True):
        return HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, item=item, ativo=ativo
        )


class TestLaboratorioModuloNegado(LaboratorioAutorizacaoBase):
    """Sem módulo `processos` autorizado — nega, mesmo autenticado."""

    @classmethod
    def get_test_schema_name(cls):
        return "laboratorio_modulo_negado"

    def test_index_negado(self):
        user = self._user("sem_modulo_processos")
        self.client.force_login(user)
        r = self.client.get("/laboratorio/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestLaboratorioHabilitacaoAusente(LaboratorioAutorizacaoBase):
    """Módulo `processos` autorizado, mas sem `processos_usar_laboratorio`
    — módulo aberto não equivale a poder usar o Laboratório."""

    @classmethod
    def get_test_schema_name(cls):
        return "laboratorio_sem_habilitacao"

    def test_index_negado(self):
        user = self._user("sem_habilitacao_laboratorio")
        papel = self._new_papel("Papel Sem Laboratorio")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_PROCESSOS)
        self.client.force_login(user)
        r = self.client.get("/laboratorio/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestLaboratorioAutorizado(LaboratorioAutorizacaoBase):
    """Módulo `processos` autorizado e `processos_usar_laboratorio`
    concedida — caminho autorizado completo."""

    @classmethod
    def get_test_schema_name(cls):
        return "laboratorio_autorizado"

    def test_index_autorizado(self):
        user = self._user("com_habilitacao_laboratorio")
        papel = self._new_papel("Papel Com Laboratorio")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_PROCESSOS)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_USAR_LABORATORIO)
        self.client.force_login(user)
        r = self.client.get("/laboratorio/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "laboratorio/index.html")


class TestLaboratorioAdministrador(LaboratorioAutorizacaoBase):
    """Administrador do escritório sempre acessa, sem depender de
    UsuarioPapel/PermissaoPapel/HabilitacaoPapel — mesmo bypass interno
    do kernel já usado no restante do sistema."""

    @classmethod
    def get_test_schema_name(cls):
        return "laboratorio_admin"

    def test_index_autorizado_para_admin(self):
        admin = self._user("admin_laboratorio")
        self._set_admin_flag(admin)
        self.client.force_login(admin)
        r = self.client.get("/laboratorio/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
