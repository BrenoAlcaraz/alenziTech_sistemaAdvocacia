"""
Testes da UI de administração de papéis dinâmicos e atribuição a
usuários (Issue #5, spec `specs/gerir-papeis-e-habilitacoes-granulares.md`).

Cobre `papeis`, `novo_papel`, `editar_papel`, `papel_usuarios` e
`remover_usuario_papel` — todas atrás de `gerir_habilitar_terceiros`
(mesma habilitação já usada em `permissoes`, PDR-0019).

Segue o mesmo padrão de fixtures de
`apps/configuracoes/tests/test_autorizacao.py`.
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    CODIGO_PRESET_LIMITADO,
    HAB_GERIR_HABILITAR_TERCEIROS,
    MODULO_GERIR,
    MODULO_PROCESSOS,
)
from apps.processos.models import Processo


class PapeisGerirBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _admin(self, username="admin_papeis"):
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

    def _papel_alvo(self, nome="Papel Alvo", protegido=False, codigo_preset=None):
        return PapelAcesso.objects.create(
            nome=nome, protegido_sistema=protegido, codigo_preset=codigo_preset
        )


class TestPapeisNegado(PapeisGerirBase):
    """Usuário sem `gerir_habilitar_terceiros` (e sem ser Administrador)
    — todas as rotas negam com 403, inclusive POST direto."""

    @classmethod
    def get_test_schema_name(cls):
        return "papeis_negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_gerir_papeis")
        self.client.force_login(self.user)
        self.papel = self._papel_alvo()

    def test_papeis_get_negado(self):
        r = self.client.get("/configuracoes/papeis/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_papel_post_negado_nao_cria(self):
        antes = PapelAcesso.objects.count()
        r = self.client.post(
            "/configuracoes/papeis/novo/", {"nome": "Tentativa"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(PapelAcesso.objects.count(), antes)

    def test_editar_papel_negado(self):
        r = self.client.get(
            f"/configuracoes/papeis/{self.papel.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_papel_usuarios_negado(self):
        r = self.client.get(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_remover_usuario_papel_negado_nao_altera(self):
        alvo = self._user("alvo_remover")
        vinculo = UsuarioPapel.objects.create(usuario=alvo, papel=self.papel, ativo=True)
        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/{vinculo.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        vinculo.refresh_from_db()
        self.assertTrue(vinculo.ativo)


class TestPapeisAutorizado(PapeisGerirBase):
    """`gerir_habilitar_terceiros` autoriza listar/criar/editar papel e
    atribuir/remover usuário do papel."""

    @classmethod
    def get_test_schema_name(cls):
        return "papeis_autorizado"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_habilitar_terceiros")
        self._conceder_gerir(self.user)
        self.client.force_login(self.user)
        self.papel = self._papel_alvo()

    def test_papeis_autorizado(self):
        r = self.client.get("/configuracoes/papeis/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_novo_papel_post_autorizado_cria(self):
        r = self.client.post(
            "/configuracoes/papeis/novo/",
            {"nome": "Papel Novo", "descricao": "", "ativo": "on"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/configuracoes/papeis/", fetch_redirect_response=False)
        self.assertTrue(PapelAcesso.objects.filter(nome="Papel Novo").exists())

    def test_editar_papel_autorizado(self):
        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/editar/",
            {"nome": "Papel Alvo Editado", "descricao": "atualizado", "ativo": "on"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/configuracoes/papeis/", fetch_redirect_response=False)
        self.papel.refresh_from_db()
        self.assertEqual(self.papel.nome, "Papel Alvo Editado")

    def test_desativar_papel_nao_exclui(self):
        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/editar/",
            {"nome": self.papel.nome, "descricao": "", "ativo": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.papel.refresh_from_db()
        self.assertFalse(self.papel.ativo)
        self.assertTrue(PapelAcesso.objects.filter(pk=self.papel.pk).exists())

    def test_atribuir_usuario_ao_papel(self):
        alvo = self._user("alvo_atribuir")
        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/",
            {"usuario": alvo.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r,
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/",
            fetch_redirect_response=False,
        )
        self.assertTrue(
            UsuarioPapel.objects.filter(usuario=alvo, papel=self.papel, ativo=True).exists()
        )

    def test_remover_usuario_do_papel_desativa_sem_excluir(self):
        alvo = self._user("alvo_remover_ok")
        vinculo = UsuarioPapel.objects.create(usuario=alvo, papel=self.papel, ativo=True)
        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/{vinculo.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        vinculo.refresh_from_db()
        self.assertFalse(vinculo.ativo)
        self.assertTrue(UsuarioPapel.objects.filter(pk=vinculo.pk).exists())
        ativo = UsuarioPapel.objects.get(usuario=alvo, ativo=True)
        self.assertEqual(ativo.papel.codigo_preset, CODIGO_PRESET_LIMITADO)

    def test_remover_do_limitado_nao_tem_efeito(self):
        alvo = self._user("alvo_no_limitado")
        limitado = PapelAcesso.objects.get(codigo_preset=CODIGO_PRESET_LIMITADO)
        vinculo = UsuarioPapel.objects.create(usuario=alvo, papel=limitado, ativo=True)
        r = self.client.post(
            f"/configuracoes/papeis/{limitado.pk}/usuarios/{vinculo.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        vinculo.refresh_from_db()
        self.assertTrue(vinculo.ativo)

    def test_atribuir_papel_substitui_o_anterior(self):
        alvo = self._user("alvo_troca_papel")
        anterior = self._papel_alvo(nome="Papel Anterior")
        UsuarioPapel.objects.create(usuario=alvo, papel=anterior, ativo=True)
        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/",
            {"usuario": alvo.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        ativos = UsuarioPapel.objects.filter(usuario=alvo, ativo=True)
        self.assertEqual([v.papel_id for v in ativos], [self.papel.pk])
        self.assertTrue(
            UsuarioPapel.objects.filter(usuario=alvo, papel=anterior, ativo=False).exists()
        )

    def test_trocar_para_papel_sem_processos_transfere_processos(self):
        administrador = self._admin("admin_recebe_processos")
        alvo = self._user("alvo_perde_processos")
        anterior = self._papel_alvo(nome="Papel Com Processos")
        PermissaoPapel.objects.create(
            papel=anterior, modulo=MODULO_PROCESSOS, ativo=True, nivel="todos"
        )
        UsuarioPapel.objects.create(usuario=alvo, papel=anterior, ativo=True)
        processo = Processo.objects.create(criado_por=alvo, titulo="Processo do alvo")
        processo.responsaveis.add(alvo)

        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/",
            {"usuario": alvo.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        processo.refresh_from_db()
        self.assertEqual(list(processo.responsaveis.values_list("pk", flat=True)), [administrador.pk])

    def test_reatribuir_usuario_removido_reativa_mesmo_vinculo(self):
        alvo = self._user("alvo_reatribuir")
        vinculo = UsuarioPapel.objects.create(usuario=alvo, papel=self.papel, ativo=False)
        r = self.client.post(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/",
            {"usuario": alvo.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            UsuarioPapel.objects.filter(usuario=alvo, papel=self.papel).count(), 1
        )
        vinculo.refresh_from_db()
        self.assertTrue(vinculo.ativo)

    def test_usuario_ja_vinculado_nao_aparece_no_formulario(self):
        alvo = self._user("alvo_ja_vinculado")
        UsuarioPapel.objects.create(usuario=alvo, papel=self.papel, ativo=True)
        r = self.client.get(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/", HTTP_HOST=self.http_host
        )
        self.assertNotIn(alvo, r.context["form"].fields["usuario"].queryset)

    def test_preset_codigo_nao_alterado_por_post_direto(self):
        preset = self._papel_alvo(
            nome="Preset Fábrica", protegido=True, codigo_preset="preset-fixo"
        )
        r = self.client.post(
            f"/configuracoes/papeis/{preset.pk}/editar/",
            {
                "nome": "Preset Fábrica Renomeado",
                "descricao": "",
                "ativo": "on",
                "codigo_preset": "tentativa-hack",
                "protegido_sistema": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        preset.refresh_from_db()
        self.assertEqual(preset.codigo_preset, "preset-fixo")
        self.assertTrue(preset.protegido_sistema)
        self.assertEqual(preset.nome, "Preset Fábrica Renomeado")

    def _editar(self, papel, **dados):
        base = {"nome": papel.nome, "descricao": "", "ativo": "on"}
        base.update(dados)
        return self.client.post(
            f"/configuracoes/papeis/{papel.pk}/editar/", base, HTTP_HOST=self.http_host
        )

    def test_de_fabrica_so_existe_o_limitado_sem_nenhuma_permissao(self):
        de_fabrica = PapelAcesso.objects.filter(protegido_sistema=True)
        self.assertEqual([p.codigo_preset for p in de_fabrica], ["limitado"])
        limitado = de_fabrica.get()
        self.assertEqual(limitado.nome, "Limitado")
        self.assertTrue(limitado.ativo)
        self.assertFalse(PermissaoPapel.objects.filter(papel=limitado, ativo=True).exists())
        self.assertFalse(HabilitacaoPapel.objects.filter(papel=limitado, ativo=True).exists())

    def test_limitado_e_editavel(self):
        limitado = PapelAcesso.objects.get(codigo_preset="limitado")
        r = self._editar(limitado, nome="Acesso mínimo", descricao="renomeado")
        self.assertEqual(r.status_code, 302)
        limitado.refresh_from_db()
        self.assertEqual(limitado.nome, "Acesso mínimo")
        self.assertEqual(limitado.codigo_preset, "limitado")

    def test_limitado_nao_pode_ser_desativado(self):
        limitado = PapelAcesso.objects.get(codigo_preset="limitado")
        r = self._editar(limitado, ativo="")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "O papel Limitado não pode ser desativado.")
        limitado.refresh_from_db()
        self.assertTrue(limitado.ativo)

    def test_limitado_nao_pode_ser_excluido(self):
        limitado = PapelAcesso.objects.get(codigo_preset="limitado")
        with self.assertRaises(ValidationError):
            limitado.delete()
        self.assertTrue(PapelAcesso.objects.filter(pk=limitado.pk).exists())

    def test_papel_com_usuarios_nao_pode_ser_desativado(self):
        for nome in ("um_usuario", "dois_usuario"):
            UsuarioPapel.objects.create(usuario=self._user(nome), papel=self.papel, ativo=True)
        r = self._editar(self.papel, ativo="")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Reatribua os 2 usuários deste papel antes de desativá-lo.")
        self.papel.refresh_from_db()
        self.assertTrue(self.papel.ativo)

    def test_usuario_inativo_ou_vinculo_removido_nao_bloqueia_desativacao(self):
        excluido = self._user("ja_excluido")
        excluido.is_active = False
        excluido.save()
        UsuarioPapel.objects.create(usuario=excluido, papel=self.papel, ativo=True)
        UsuarioPapel.objects.create(usuario=self._user("desvinculado"), papel=self.papel, ativo=False)
        r = self._editar(self.papel, ativo="")
        self.assertEqual(r.status_code, 302)
        self.papel.refresh_from_db()
        self.assertFalse(self.papel.ativo)


class TestPapeisAdminBypass(PapeisGerirBase):
    """Administrador do escritório acessa todas as rotas sem depender
    de `gerir_habilitar_terceiros`."""

    @classmethod
    def get_test_schema_name(cls):
        return "papeis_admin_bypass"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.client.force_login(self.admin)
        self.papel = self._papel_alvo()

    def test_papeis_autorizado(self):
        r = self.client.get("/configuracoes/papeis/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_papel_usuarios_autorizado(self):
        r = self.client.get(
            f"/configuracoes/papeis/{self.papel.pk}/usuarios/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
