"""
Testes formais do contrato de Tenant Admin.

Fixam o comportamento de:
  - usuario_admin_escritorio()
  - requer_admin_escritorio()
  - tipo_conta_usuario() — ausência de retorno 'administrador_escritorio'

Classe: TenantTestCase (django_tenants.test.cases)
  - cria schema isolado por classe
  - cada método de teste é envolto em transação com rollback automático
  - GroupS e seeds de PermissaoPapel/HabilitacaoPapel são criados pelas migrations
    e persistem entre métodos (são dados de migração, não de teste)

Testes marcados como FALHA_ESPERADA falharão no kernel atual (pré-2.1C1B).
Os demais devem PASSAR mesmo antes da implementação.
"""

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser, Group, User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.decorators import requer_admin_escritorio, usuario_admin_escritorio
from apps.accounts.models import PerfilUsuario
from apps.accounts.permissoes import tipo_conta_usuario


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------

def _view_ok(request):
    return HttpResponse("OK", status=200)


_decorated_view = requer_admin_escritorio(_view_ok)


class AdminTenantBase(TenantTestCase):
    """
    Base com helpers para testes de Tenant Admin.
    Schema: 'test_admin' — criado uma vez por classe, dropped no teardown.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Escritório Teste Admin"
        tenant.slug = "test-admin-kernel"

    @classmethod
    def get_test_schema_name(cls):
        return "test_admin"

    # ── helpers de fixtures ─────────────────────────────────────────────────

    def _user(self, username, *, is_active=True, is_superuser=False, is_staff=False):
        """Cria User. Signal cria PerfilUsuario com is_admin_escritorio=False automaticamente."""
        return User.objects.create_user(
            username=username,
            password="testpass",
            is_active=is_active,
            is_superuser=is_superuser,
            is_staff=is_staff,
        )

    def _set_admin_flag(self, user, value=True):
        """Seta is_admin_escritorio no PerfilUsuario do usuário."""
        # Usa update() + limpeza de cache para garantir que usuario_admin_escritorio()
        # leia o valor atualizado do banco.
        # Django 5.x armazena o reverse OneToOneField em _state.fields_cache (não __dict__).
        n = PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=value)
        if n != 1:
            raise AssertionError(f"_set_admin_flag: esperado 1 row atualizado, got {n}")
        user._state.fields_cache.pop("perfil", None)

    def _del_perfil(self, user):
        """Remove o PerfilUsuario do usuário (para testar ausência de perfil)."""
        PerfilUsuario.objects.filter(user=user).delete()
        # limpa cache do reverse OneToOneField (Django 5.x: armazenado em __dict__)
        user._state.fields_cache.pop("perfil", None)

    def _add_group(self, user, nome):
        grp = Group.objects.get(name=nome)
        user.groups.add(grp)

    def _request_for(self, user):
        factory = RequestFactory()
        req = factory.get("/")
        req.user = user
        return req

    def _call_decorator(self, user):
        """Chama a view decorada. Retorna (response, exception_or_None)."""
        req = self._request_for(user)
        try:
            response = _decorated_view(req)
            return response, None
        except PermissionDenied as exc:
            return None, exc

    # ── marcador de falha esperada ──────────────────────────────────────────

    FALHA_ESPERADA = "FALHA ESPERADA NO KERNEL ATUAL (pré-2.1C1B)"

    def assertFuturo(self, condicao, motivo=""):
        """
        Registra um assert que falha no kernel atual e passará em 2.1C1B.
        Não usa self.assertTrue diretamente para não interromper o test runner.
        A falha É o resultado esperado neste estágio.
        """
        if not condicao:
            raise AssertionError(f"{self.FALHA_ESPERADA}: {motivo}")


# ===========================================================================
# 7. TESTES DE TENANT ADMIN
# ===========================================================================

class TestUsuarioAdminEscritorio(AdminTenantBase):
    """Testes de usuario_admin_escritorio()."""

    # ── PASSA no kernel atual ───────────────────────────────────────────────

    def test_usuario_anonimo_nao_e_tenant_admin(self):
        """AnonymousUser: função não lida com anônimos — espera AttributeError seguro."""
        anon = AnonymousUser()
        # AnonymousUser não tem .pk nem .is_active no mesmo sentido
        # O kernel atual checa user.is_superuser → AttributeError ou False
        # _usuario_valido() verifica user.pk → None → retorna False
        # usuario_admin_escritorio() verifica is_superuser → False em AnonymousUser
        # Vamos verificar que não concede True
        result = usuario_admin_escritorio(anon)
        self.assertFalse(result)

    def test_usuario_sem_perfil_nao_e_tenant_admin(self):
        """Usuário sem PerfilUsuario retorna False."""
        u = self._user("sem_perfil")
        self._del_perfil(u)
        # Sem perfil → perfil=None → is_admin_escritorio False
        # Sem Group administrador_escritorio → False
        result = usuario_admin_escritorio(u)
        self.assertFalse(result)

    def test_tenant_admin_ativo_e_reconhecido(self):
        """is_active=True + is_admin_escritorio=True → True."""
        u = self._user("admin_ativo")
        self._set_admin_flag(u, True)
        result = usuario_admin_escritorio(u)
        self.assertTrue(result)

    def test_staff_sem_flag_nao_e_tenant_admin(self):
        """is_staff=True sem is_admin_escritorio e sem Group → False."""
        u = self._user("staff_user", is_staff=True)
        # PerfilUsuario criado automaticamente com is_admin_escritorio=False
        result = usuario_admin_escritorio(u)
        self.assertFalse(result)

    # ── FALHA no kernel atual (pré-2.1C1B) ─────────────────────────────────

    def test_superuser_sem_flag_nao_e_tenant_admin(self):
        """
        FALHA ESPERADA: is_superuser=True, is_admin_escritorio=False → deve retornar False.
        Kernel atual: is_superuser short-circuits e retorna True.
        """
        u = self._user("superuser_sem_flag", is_superuser=True)
        # is_admin_escritorio=False (PerfilUsuario criado pelo signal com valor padrão)
        result = usuario_admin_escritorio(u)
        self.assertFuturo(
            not result,
            "is_superuser sozinho não deve conceder Tenant Admin",
        )

    def test_usuario_inativo_com_flag_nao_e_tenant_admin(self):
        """
        FALHA ESPERADA: is_active=False + is_admin_escritorio=True → deve retornar False.
        Kernel atual: verifica is_admin_escritorio sem checar is_active → retorna True.
        """
        u = self._user("admin_inativo", is_active=False)
        self._set_admin_flag(u, True)
        result = usuario_admin_escritorio(u)
        self.assertFuturo(
            not result,
            "Usuário inativo não deve ser Tenant Admin mesmo com flag ativa",
        )

    def test_grupo_admin_sem_flag_nao_e_tenant_admin(self):
        """
        FALHA ESPERADA: Group='administrador_escritorio' sem is_admin_escritorio → deve ser False.
        Kernel atual: Group membership retorna True.
        """
        u = self._user("group_admin")
        self._add_group(u, "administrador_escritorio")
        result = usuario_admin_escritorio(u)
        self.assertFuturo(
            not result,
            "Group administrador_escritorio sem flag is_admin_escritorio não deve conceder",
        )


class TestTipoContaUsuario(AdminTenantBase):
    """Testes de tipo_conta_usuario() — não deve retornar 'administrador_escritorio'."""

    @classmethod
    def get_test_schema_name(cls):
        return "test_admin_tc"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Escritório Teste TipoConta"
        tenant.slug = "test-tipoconta"

    # ── FALHA no kernel atual ────────────────────────────────────────────────

    def test_tipo_conta_usuario_nao_retorna_admin(self):
        """
        FALHA ESPERADA: tipo_conta_usuario() com admin atual retorna 'administrador_escritorio'.
        Futuro: deve retornar None (admin não entra na resolução de tipo_conta).
        """
        u = self._user("admin_tc")
        self._set_admin_flag(u, True)
        result = tipo_conta_usuario(u)
        self.assertFuturo(
            result != "administrador_escritorio",
            "tipo_conta_usuario não deve retornar 'administrador_escritorio'; admin é tratado antes",
        )

    # ── PASSA no kernel atual ────────────────────────────────────────────────

    def test_tipo_conta_usuario_retorna_limitado(self):
        u = self._user("user_limitado")
        self._add_group(u, "limitado")
        result = tipo_conta_usuario(u)
        self.assertEqual(result, "limitado")

    def test_tipo_conta_usuario_retorna_financeiro(self):
        u = self._user("user_financeiro")
        self._add_group(u, "financeiro")
        result = tipo_conta_usuario(u)
        self.assertEqual(result, "financeiro")

    def test_tipo_conta_usuario_retorna_none_sem_grupo(self):
        u = self._user("sem_grupo")
        result = tipo_conta_usuario(u)
        self.assertIsNone(result)

    def test_tipo_conta_usuario_retorna_none_com_dois_grupos(self):
        u = self._user("dois_grupos")
        self._add_group(u, "limitado")
        self._add_group(u, "financeiro")
        result = tipo_conta_usuario(u)
        self.assertIsNone(result)

    def test_tipo_conta_usuario_retorna_none_inativo(self):
        u = self._user("inativo_tc", is_active=False)
        self._add_group(u, "limitado")
        result = tipo_conta_usuario(u)
        self.assertIsNone(result)


class TestRequerAdminEscritorio(AdminTenantBase):
    """Testes do decorator @requer_admin_escritorio."""

    @classmethod
    def get_test_schema_name(cls):
        return "test_admin_dec"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Escritório Teste Decorator"
        tenant.slug = "test-decorator"

    def _resp(self, user):
        """Invoca o decorator e retorna (status_code_ou_None, exc_ou_None)."""
        resp, exc = self._call_decorator(user)
        return resp.status_code if resp else None, exc

    # ── PASSA no kernel atual ────────────────────────────────────────────────

    def test_requer_admin_permite_tenant_admin_ativo(self):
        """Admin ativo (flag) recebe 200."""
        u = self._user("dec_admin")
        self._set_admin_flag(u, True)
        code, exc = self._resp(u)
        self.assertIsNone(exc)
        self.assertEqual(code, 200)

    def test_requer_admin_nega_usuario_comum(self):
        """Usuário sem papel técnico recebe PermissionDenied."""
        u = self._user("dec_comum")
        _, exc = self._resp(u)
        self.assertIsInstance(exc, PermissionDenied)

    def test_requer_admin_redireciona_anonimo(self):
        """AnonymousUser recebe redirect (302)."""
        req = self._request_for(AnonymousUser())
        resp = _decorated_view(req)
        self.assertEqual(resp.status_code, 302)

    # ── FALHA no kernel atual (pré-2.1C1B) ─────────────────────────────────

    def test_requer_admin_nega_superuser_sem_flag(self):
        """
        FALHA ESPERADA: is_superuser sem flag → deve ser PermissionDenied.
        Kernel atual: is_superuser → True → permite.
        """
        u = self._user("dec_super", is_superuser=True)
        _, exc = self._resp(u)
        self.assertFuturo(
            exc is not None and isinstance(exc, PermissionDenied),
            "superuser sem flag não deve ser permitido pelo decorator",
        )

    def test_requer_admin_nega_group_admin_sem_flag(self):
        """
        FALHA ESPERADA: Group administrador_escritorio sem flag → deve ser PermissionDenied.
        Kernel atual: Group → True → permite.
        """
        u = self._user("dec_grp")
        self._add_group(u, "administrador_escritorio")
        _, exc = self._resp(u)
        self.assertFuturo(
            exc is not None and isinstance(exc, PermissionDenied),
            "Group administrador_escritorio sem flag não deve ser permitido pelo decorator",
        )

    def test_requer_admin_nega_tenant_admin_inativo(self):
        """
        FALHA ESPERADA: is_active=False + is_admin_escritorio=True → deve ser PermissionDenied.
        Kernel atual: is_admin_escritorio=True short-circuits sem checar is_active → permite.

        Nota: requer_admin_escritorio verifica is_authenticated mas NÃO is_active.
        Usuário inativo mantendo sessão → gap de segurança atual.
        """
        u = self._user("dec_inativo", is_active=False)
        self._set_admin_flag(u, True)
        _, exc = self._resp(u)
        self.assertFuturo(
            exc is not None and isinstance(exc, PermissionDenied),
            "Tenant Admin inativo não deve ser permitido pelo decorator",
        )
