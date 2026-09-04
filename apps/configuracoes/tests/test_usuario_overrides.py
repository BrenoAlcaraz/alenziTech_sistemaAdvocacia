"""
Testes da Issue #7 (spec `specs/gerir-papeis-e-habilitacoes-granulares.md`,
seção "4. Overrides individuais (`PermissaoUsuario`, `HabilitacaoUsuario`)").

Cobre `usuario_overrides`: autorização (`gerir_habilitar_terceiros`),
criação/remoção de override individual de módulo/nível e de
habilitação granular, e o valor herdado exibido (via papel dinâmico ou
tipo de conta legado). A validação de efeito é sempre feita
consultando o kernel (`tem_permissao_modulo`/`tem_habilitacao`
/`nivel_acesso_modulo`) diretamente, não só a UI.

Segue o mesmo padrão de fixtures de test_autorizacao.py/test_papeis.py.
"""

from django.contrib.auth.models import Group, User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    HabilitacaoUsuario,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    PermissaoUsuario,
    UsuarioPapel,
)
from apps.accounts.permissoes import nivel_acesso_modulo, tem_habilitacao, tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_GERIR_HABILITAR_TERCEIROS,
    MODULO_CLIENTES,
    MODULO_GERIR,
    MODULO_PROCESSOS,
)
from apps.processos.models import Processo


class UsuarioOverridesBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _admin(self, username="admin_overrides"):
        user = self._user(username)
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        return user

    def _conceder_gerir(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel Gerir {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        HabilitacaoPapel.objects.create(
            papel=papel,
            tipo_conta=None,
            modulo=MODULO_GERIR,
            item=HAB_GERIR_HABILITAR_TERCEIROS,
            ativo=True,
        )
        return papel


class TestUsuarioOverridesNegado(UsuarioOverridesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "overrides_negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_gerir_overrides")
        self.alvo = self._user("alvo_negado")
        self.client.force_login(self.user)

    def test_get_negado(self):
        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_post_negado_nao_cria(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"override_clientes": "ligado", "nivel_override_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(PermissaoUsuario.objects.filter(usuario=self.alvo).exists())


class TestUsuarioOverridesAutorizado(UsuarioOverridesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "overrides_autorizado"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_habilitar_terceiros_overrides")
        self._conceder_gerir(self.user)
        self.client.force_login(self.user)
        self.alvo = self._user("alvo_overrides")

    def test_get_autorizado(self):
        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_criar_override_modulo_ativo_efeito_no_kernel(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"override_clientes": "ligado", "nivel_override_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        override = PermissaoUsuario.objects.get(usuario=self.alvo, modulo=MODULO_CLIENTES)
        self.assertTrue(override.ativo)
        self.assertEqual(override.nivel, "todos")
        self.assertTrue(tem_permissao_modulo(self.alvo, MODULO_CLIENTES))
        self.assertEqual(nivel_acesso_modulo(self.alvo, MODULO_CLIENTES), "todos")

    def test_criar_override_modulo_desativado_efeito_no_kernel(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"override_clientes": "desligado", "nivel_override_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(
            PermissaoUsuario.objects.get(usuario=self.alvo, modulo=MODULO_CLIENTES).ativo
        )
        self.assertFalse(tem_permissao_modulo(self.alvo, MODULO_CLIENTES))

    def test_criar_override_habilitacao_granular_efeito_no_kernel(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {
                "override_clientes": "ligado",
                "nivel_override_clientes": "todos",
                f"hab_override_{MODULO_CLIENTES}_{HAB_CLIENTES_CRIAR}": "ligado",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            HabilitacaoUsuario.objects.get(
                usuario=self.alvo, modulo=MODULO_CLIENTES, item=HAB_CLIENTES_CRIAR
            ).ativo
        )
        self.assertTrue(tem_habilitacao(self.alvo, MODULO_CLIENTES, HAB_CLIENTES_CRIAR))

    def test_remover_override_restaura_heranca(self):
        PermissaoUsuario.objects.create(
            usuario=self.alvo, modulo=MODULO_CLIENTES, ativo=True, nivel="todos"
        )
        HabilitacaoUsuario.objects.create(
            usuario=self.alvo, modulo=MODULO_CLIENTES, item=HAB_CLIENTES_CRIAR, ativo=True
        )
        self.assertTrue(tem_permissao_modulo(self.alvo, MODULO_CLIENTES))

        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {
                "override_clientes": "herdar",
                f"hab_override_{MODULO_CLIENTES}_{HAB_CLIENTES_CRIAR}": "herdar",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(PermissaoUsuario.objects.filter(usuario=self.alvo, modulo=MODULO_CLIENTES).exists())
        self.assertFalse(
            HabilitacaoUsuario.objects.filter(
                usuario=self.alvo, modulo=MODULO_CLIENTES, item=HAB_CLIENTES_CRIAR
            ).exists()
        )
        # Sem papel/tipo de conta, herança é "sem acesso" — restaurada corretamente.
        self.assertFalse(tem_permissao_modulo(self.alvo, MODULO_CLIENTES))

    def test_herdado_reflete_papel_dinamico_do_alvo(self):
        papel = PapelAcesso.objects.create(nome="Papel do Alvo", ativo=True)
        UsuarioPapel.objects.create(usuario=self.alvo, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_CLIENTES, ativo=True, nivel="somente_seus"
        )

        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        modulos = {m["slug"]: m for m in r.context["modulos_contexto"]}
        self.assertTrue(modulos[MODULO_CLIENTES]["herdado"]["ativo"])
        self.assertEqual(modulos[MODULO_CLIENTES]["herdado"]["nivel"], "somente_seus")

    def test_perder_acesso_processos_via_override_reatribui_responsavel(self):
        administrador = self._admin("administrador_reatribuicao")

        papel = PapelAcesso.objects.create(nome="Papel Processos Alvo", ativo=True)
        UsuarioPapel.objects.create(usuario=self.alvo, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PROCESSOS, ativo=True, nivel="todos"
        )
        self.assertTrue(tem_permissao_modulo(self.alvo, MODULO_PROCESSOS))

        processo = Processo.objects.create(
            responsavel=self.alvo, cliente=None, titulo="Processo do Alvo"
        )

        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"override_processos": "desligado", "nivel_override_processos": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(tem_permissao_modulo(self.alvo, MODULO_PROCESSOS))

        processo.refresh_from_db()
        self.assertEqual(processo.responsavel_id, administrador.pk)

    def test_herdado_reflete_tipo_conta_legado_sem_papel(self):
        grupo_limitado = Group.objects.get(name="limitado")
        self.alvo.groups.add(grupo_limitado)
        PermissaoPapel.objects.update_or_create(
            tipo_conta="limitado",
            modulo=MODULO_CLIENTES,
            defaults={"ativo": True, "nivel": "todos"},
        )

        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        modulos = {m["slug"]: m for m in r.context["modulos_contexto"]}
        self.assertTrue(modulos[MODULO_CLIENTES]["herdado"]["ativo"])
        self.assertEqual(modulos[MODULO_CLIENTES]["herdado"]["nivel"], "todos")


class TestUsuarioOverridesAlvoAdministrador(UsuarioOverridesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "overrides_alvo_admin"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_habilitar_terceiros_alvo_admin")
        self._conceder_gerir(self.user)
        self.client.force_login(self.user)
        self.alvo_admin = self._admin("alvo_admin")

    def test_get_mostra_aviso_sem_formulario(self):
        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo_admin.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["is_admin_alvo"])

    def test_post_nao_cria_override_para_admin(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo_admin.pk}/permissoes/",
            {"override_clientes": "ligado", "nivel_override_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(PermissaoUsuario.objects.filter(usuario=self.alvo_admin).exists())


class TestUsuarioOverridesAdminBypass(UsuarioOverridesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "overrides_admin_bypass"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.client.force_login(self.admin)
        self.alvo = self._user("alvo_bypass")

    def test_admin_acessa_sem_habilitacao(self):
        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
