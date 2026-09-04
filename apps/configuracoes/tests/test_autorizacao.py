"""
Testes de PDR-0019 — autorização do módulo `gerir` aplicada às views
administrativas de apps/configuracoes (novo_usuario, equipes e
sub-rotas, permissoes), no lugar do antigo `@requer_admin_escritorio`
fixo.

`editar_escritorio`, `index`, `editar_perfil` e `alterar_senha` não
mudam (fora do escopo da spec) e não são recobertos aqui além de um
smoke check de não-regressão.

Segue o mesmo padrão de fixtures de apps/processos/tests/test_integrantes.py.
"""

from django.contrib.auth.models import Group, User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    Equipe,
    HabilitacaoPapel,
    MembroEquipe,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_GERIR_CRIAR_EQUIPE,
    HAB_GERIR_CRIAR_USUARIO,
    HAB_GERIR_HABILITAR_TERCEIROS,
    MODULO_GERIR,
)


class ConfiguracoesGerirBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _admin(self, username="admin_gerir"):
        user = self._user(username)
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        return user

    def _conceder_gerir(self, user, item=None):
        papel = PapelAcesso.objects.create(nome=f"Papel Gerir {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        if item:
            HabilitacaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=MODULO_GERIR, item=item, ativo=True
            )
        return papel

    def _equipe(self, nome="Equipe Teste"):
        return Equipe.objects.create(nome=nome, ativo=True)

    def _membro(self, equipe, usuario, eh_gerente=False):
        return MembroEquipe.objects.create(
            equipe=equipe, usuario=usuario, eh_gerente=eh_gerente, ativo=True
        )


class TestConfiguracoesGerirNegado(ConfiguracoesGerirBase):
    """Usuário autenticado sem módulo `gerir` (nenhum UsuarioPapel) —
    todas as rotas administrativas negam com 403, inclusive POST direto."""

    @classmethod
    def get_test_schema_name(cls):
        return "configuracoes_gerir_negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_gerir")
        self.client.force_login(self.user)
        self.equipe = self._equipe()
        self.membro = self._membro(self.equipe, self._user("membro_alvo"))

    def test_novo_usuario_get_negado(self):
        r = self.client.get("/configuracoes/usuarios/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_usuario_post_negado_nao_cria(self):
        antes = User.objects.count()
        r = self.client.post(
            "/configuracoes/usuarios/novo/",
            {"username": "tentativa", "email": "t@t.com", "password1": "x", "password2": "x"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(User.objects.count(), antes)

    def test_equipes_negado(self):
        r = self.client.get("/configuracoes/equipes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_nova_equipe_post_negado_nao_cria(self):
        antes = Equipe.objects.count()
        r = self.client.post(
            "/configuracoes/equipes/novo/", {"nome": "Tentativa"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Equipe.objects.count(), antes)

    def test_editar_equipe_negado(self):
        r = self.client.get(
            f"/configuracoes/equipes/{self.equipe.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_equipe_membros_negado(self):
        r = self.client.get(
            f"/configuracoes/equipes/{self.equipe.pk}/membros/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_remover_membro_negado_nao_apaga(self):
        r = self.client.post(
            f"/configuracoes/equipes/{self.equipe.pk}/membros/{self.membro.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(MembroEquipe.objects.filter(pk=self.membro.pk).exists())

    def test_alternar_gerente_negado_nao_altera(self):
        r = self.client.post(
            f"/configuracoes/equipes/{self.equipe.pk}/membros/{self.membro.pk}/alternar-gerente/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.membro.refresh_from_db()
        self.assertFalse(self.membro.eh_gerente)

    def test_permissoes_get_negado(self):
        r = self.client.get("/configuracoes/permissoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_permissoes_post_negado(self):
        r = self.client.post(
            "/configuracoes/permissoes/",
            {"tipo_conta": "limitado", "ativo_processos": "on"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestConfiguracoesGerirCriarUsuario(ConfiguracoesGerirBase):
    """`gerir_criar_usuario` autoriza só novo_usuario — equipes e
    permissões continuam negadas para este usuário."""

    @classmethod
    def get_test_schema_name(cls):
        return "configuracoes_gerir_criar_usuario"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_criar_usuario")
        self._conceder_gerir(self.user, HAB_GERIR_CRIAR_USUARIO)
        self.client.force_login(self.user)
        self.grupo_limitado = Group.objects.get(name="limitado")

    def test_novo_usuario_get_autorizado(self):
        r = self.client.get("/configuracoes/usuarios/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_novo_usuario_post_autorizado_cria(self):
        r = self.client.post(
            "/configuracoes/usuarios/novo/",
            {
                "username": "novo.usuario",
                "email": "novo.usuario@escritorio.com",
                "grupo": self.grupo_limitado.pk,
                "password1": "SenhaForte123!",
                "password2": "SenhaForte123!",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/configuracoes/", fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username="novo.usuario").exists())

    def test_equipes_continua_negado(self):
        r = self.client.get("/configuracoes/equipes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_permissoes_continua_negado(self):
        r = self.client.get("/configuracoes/permissoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestConfiguracoesGerirCriarEquipe(ConfiguracoesGerirBase):
    """`gerir_criar_equipe` autoriza listar/criar/editar equipe e
    gerenciar membros/gerente — novo_usuario e permissões continuam
    negadas para este usuário."""

    @classmethod
    def get_test_schema_name(cls):
        return "configuracoes_gerir_criar_equipe"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_criar_equipe")
        self._conceder_gerir(self.user, HAB_GERIR_CRIAR_EQUIPE)
        self.client.force_login(self.user)
        self.equipe = self._equipe()
        self.membro_usuario = self._user("membro_alvo_equipe")
        self.membro = self._membro(self.equipe, self.membro_usuario)

    def test_equipes_autorizado(self):
        r = self.client.get("/configuracoes/equipes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_nova_equipe_post_autorizado_cria(self):
        r = self.client.post(
            "/configuracoes/equipes/novo/", {"nome": "Equipe Nova"}, HTTP_HOST=self.http_host
        )
        self.assertRedirects(r, "/configuracoes/equipes/", fetch_redirect_response=False)
        self.assertTrue(Equipe.objects.filter(nome="Equipe Nova").exists())

    def test_editar_equipe_autorizado(self):
        r = self.client.get(
            f"/configuracoes/equipes/{self.equipe.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_equipe_membros_autorizado(self):
        r = self.client.get(
            f"/configuracoes/equipes/{self.equipe.pk}/membros/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_alternar_gerente_autorizado(self):
        r = self.client.post(
            f"/configuracoes/equipes/{self.equipe.pk}/membros/{self.membro.pk}/alternar-gerente/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.membro.refresh_from_db()
        self.assertTrue(self.membro.eh_gerente)

    def test_remover_membro_autorizado(self):
        r = self.client.post(
            f"/configuracoes/equipes/{self.equipe.pk}/membros/{self.membro.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(MembroEquipe.objects.filter(pk=self.membro.pk).exists())

    def test_novo_usuario_continua_negado(self):
        r = self.client.get("/configuracoes/usuarios/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_permissoes_continua_negado(self):
        r = self.client.get("/configuracoes/permissoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestConfiguracoesGerirHabilitarTerceiros(ConfiguracoesGerirBase):
    """`gerir_habilitar_terceiros` autoriza só permissoes — novo_usuario
    e equipes continuam negadas para este usuário."""

    @classmethod
    def get_test_schema_name(cls):
        return "configuracoes_gerir_habilitar_terceiros"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_habilitar_terceiros")
        self._conceder_gerir(self.user, HAB_GERIR_HABILITAR_TERCEIROS)
        self.client.force_login(self.user)

    def test_permissoes_get_autorizado(self):
        r = self.client.get("/configuracoes/permissoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_permissoes_post_autorizado(self):
        r = self.client.post(
            "/configuracoes/permissoes/",
            {"tipo_conta": "limitado", "ativo_processos": "on", "nivel_processos": "somente_seus"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            PermissaoPapel.objects.filter(
                tipo_conta="limitado", modulo="processos", ativo=True
            ).exists()
        )

    def test_novo_usuario_continua_negado(self):
        r = self.client.get("/configuracoes/usuarios/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_equipes_continua_negado(self):
        r = self.client.get("/configuracoes/equipes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestConfiguracoesGerirAdminBypass(ConfiguracoesGerirBase):
    """Administrador do escritório continua acessando todas as rotas
    administrativas — incluindo editar_escritorio, que não muda nesta
    feature — sem depender de nenhuma habilitação."""

    @classmethod
    def get_test_schema_name(cls):
        return "configuracoes_gerir_admin_bypass"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.client.force_login(self.admin)
        self.equipe = self._equipe()

    def test_novo_usuario_autorizado(self):
        r = self.client.get("/configuracoes/usuarios/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_equipes_autorizado(self):
        r = self.client.get("/configuracoes/equipes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_permissoes_autorizado(self):
        r = self.client.get("/configuracoes/permissoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_editar_escritorio_sem_regressao(self):
        r = self.client.get("/configuracoes/escritorio/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
