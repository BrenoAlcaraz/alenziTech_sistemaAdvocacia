"""
Testes da Issue #7 (spec `specs/gerir-papeis-e-habilitacoes-granulares.md`,
seção "4. Overrides individuais (`PermissaoUsuario`, `HabilitacaoUsuario`)"),
atualizados por `specs/configuracoes-perfil-e-habilitacoes.md`: a tela
deixou de expor "herdado"/"herdar" como conceito separado — mostra
direto o estado efetivo (toggle único `ativo_<slug>`/`hab_<slug>_<item>`,
mesmo padrão de `_permissoes_form.html`) e qualquer alteração grava um
override individual explícito (nunca mais "restaura herança" por um
valor de campo — o mecanismo de override em si continua existindo).

Cobre `usuario_overrides`: autorização (`gerir_habilitar_terceiros`),
criação de override individual de módulo/nível e de habilitação
granular a partir do estado efetivo exibido, e o valor herdado usado
como padrão inicial (via papel de acesso)
quando não há override. A validação de efeito é sempre feita
consultando o kernel (`tem_permissao_modulo`/`tem_habilitacao`
/`nivel_acesso_modulo`) diretamente, não só a UI.

Segue o mesmo padrão de fixtures de test_autorizacao.py/test_papeis.py.
"""

from django.contrib.auth.models import User
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
            papel=papel, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        HabilitacaoPapel.objects.create(
            papel=papel,
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
            {"ativo_clientes": "on", "nivel_clientes": "todos"},
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

    def test_ligar_modulo_efeito_no_kernel(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"ativo_clientes": "on", "nivel_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        override = PermissaoUsuario.objects.get(usuario=self.alvo, modulo=MODULO_CLIENTES)
        self.assertTrue(override.ativo)
        self.assertEqual(override.nivel, "todos")
        self.assertTrue(tem_permissao_modulo(self.alvo, MODULO_CLIENTES))
        self.assertEqual(nivel_acesso_modulo(self.alvo, MODULO_CLIENTES), "todos")

    def test_desligar_modulo_efeito_no_kernel(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"nivel_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(
            PermissaoUsuario.objects.get(usuario=self.alvo, modulo=MODULO_CLIENTES).ativo
        )
        self.assertFalse(tem_permissao_modulo(self.alvo, MODULO_CLIENTES))

    def test_ligar_habilitacao_granular_efeito_no_kernel(self):
        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {
                "ativo_clientes": "on",
                "nivel_clientes": "todos",
                f"hab_{MODULO_CLIENTES}_{HAB_CLIENTES_CRIAR}": "on",
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

    def test_salvar_sempre_grava_override_explicito_mesmo_igual_ao_herdado(self):
        """Não existe mais opção de "herdar" na tela — qualquer submissão
        grava um override individual, mesmo quando o valor enviado
        coincide com o herdado (o mecanismo de override continua
        existindo tecnicamente por baixo)."""
        papel = PapelAcesso.objects.create(nome="Papel do Alvo Explicito", ativo=True)
        UsuarioPapel.objects.create(usuario=self.alvo, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_CLIENTES, ativo=True, nivel="todos"
        )
        self.assertFalse(PermissaoUsuario.objects.filter(usuario=self.alvo, modulo=MODULO_CLIENTES).exists())

        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"ativo_clientes": "on", "nivel_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        override = PermissaoUsuario.objects.get(usuario=self.alvo, modulo=MODULO_CLIENTES)
        self.assertTrue(override.ativo)
        self.assertEqual(override.nivel, "todos")

    def test_estado_efetivo_reflete_papel_dinamico_do_alvo_sem_override(self):
        papel = PapelAcesso.objects.create(nome="Papel do Alvo", ativo=True)
        UsuarioPapel.objects.create(usuario=self.alvo, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_CLIENTES, ativo=True, nivel="somente_seus"
        )

        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        modulos = {m["slug"]: m for m in r.context["modulos_contexto"]}
        self.assertTrue(modulos[MODULO_CLIENTES]["ativo"])
        self.assertEqual(modulos[MODULO_CLIENTES]["nivel_atual"], "somente_seus")

    def test_perder_acesso_processos_via_override_reatribui_responsavel(self):
        administrador = self._admin("administrador_reatribuicao")

        papel = PapelAcesso.objects.create(nome="Papel Processos Alvo", ativo=True)
        UsuarioPapel.objects.create(usuario=self.alvo, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel="todos"
        )
        self.assertTrue(tem_permissao_modulo(self.alvo, MODULO_PROCESSOS))

        processo = Processo.objects.create(
            responsavel=self.alvo, titulo="Processo do Alvo"
        )

        r = self.client.post(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/",
            {"nivel_processos": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(tem_permissao_modulo(self.alvo, MODULO_PROCESSOS))

        processo.refresh_from_db()
        self.assertEqual(processo.responsavel_id, administrador.pk)

    def test_estado_efetivo_de_usuario_sem_papel_e_tudo_desligado(self):
        r = self.client.get(
            f"/configuracoes/usuarios/{self.alvo.pk}/permissoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        modulos = r.context["modulos_contexto"]
        self.assertFalse(any(m["ativo"] for m in modulos))
        self.assertFalse(any(i["ativo"] for m in modulos for i in m["itens"]))


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
            {"ativo_clientes": "on", "nivel_clientes": "todos"},
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
