"""
Testes de autorização de módulo (Camada 1) e de habilitação funcional
(Camada 2) para apps/tarefas/views.py.

Camada 1 cobre o enforcement de tem_permissao_modulo(user, "tarefas") nas
dez rotas existentes (quadro, lista, nova, editar, reatribuir, concluir,
reabrir, iniciar, cancelar, excluir). Camada 2 cobre o enforcement de
tarefas_atribuir_outros em `nova` e `reatribuir` — a única habilitação do
módulo hoje.

Segue o mesmo padrão de fixtures de apps/clientes/tests/test_autorizacao.py
sobre django_tenants.test.cases.TenantTestCase.
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
    HAB_TAREFAS_ATRIBUIR_OUTROS,
    MODULO_TAREFAS,
    NIVEL_TODOS,
)
from apps.tarefas.models import Tarefa


class TarefasAutorizacaoBase(TenantTestCase):
    """Helpers de fixture e de acesso HTTP compartilhados pelos testes deste módulo."""

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _set_admin(self, user, value=True):
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

    def _tarefa(self, *, responsavel, **kwargs):
        defaults = {"titulo": "Tarefa Teste", "criador": responsavel, "atribuidor": responsavel}
        defaults.update(kwargs)
        return Tarefa.objects.create(responsavel=responsavel, **defaults)


class TestTarefasAutorizacaoModuloNegado(TarefasAutorizacaoBase):
    """
    Usuário autenticado sem autorização do módulo `tarefas`
    (nenhum UsuarioPapel, nenhum Group técnico) — as dez rotas negam.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_autorizacao_negado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Autorizacao Negado"
        tenant.slug = "tarefas-autorizacao-negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_tarefas")
        self.client.force_login(self.user)
        self.tarefa = self._tarefa(responsavel=self.user)

    def test_quadro_negado(self):
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_lista_negada(self):
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_nova_get_negado(self):
        r = self.client.get("/tarefas/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_nova_post_negado_nao_cria_tarefa(self):
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            {"titulo": "Tentativa Negada", "prioridade": "media"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Tarefa.objects.count(), antes)

    def test_editar_get_negado(self):
        r = self.client.get(
            f"/tarefas/{self.tarefa.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_reatribuir_get_negado(self):
        r = self.client.get(
            f"/tarefas/{self.tarefa.pk}/reatribuir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_concluir_negado_nao_altera_status(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "a_fazer")

    def test_reabrir_negado(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_iniciar_negado(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/iniciar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_cancelar_negado(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/cancelar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_excluir_negado_nao_apaga(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Tarefa.objects.filter(pk=self.tarefa.pk).exists())


class TestTarefasAutorizacaoModuloConcedido(TarefasAutorizacaoBase):
    """
    Usuário autorizado ao módulo `tarefas` (nível `todos`, via papel
    dinâmico) preserva o comportamento HTTP existente das dez rotas.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_autorizacao_concedido"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Autorizacao Concedido"
        tenant.slug = "tarefas-autorizacao-concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_tarefas")
        papel = self._new_papel("Papel Tarefas Concedido")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_TAREFAS)
        self.client.force_login(self.user)
        self.tarefa = self._tarefa(responsavel=self.user)

    def test_quadro_autorizado(self):
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "tarefas/quadro.html")

    def test_lista_autorizada(self):
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "tarefas/lista.html")

    def test_nova_get_autorizado(self):
        r = self.client.get("/tarefas/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_nova_post_para_si_mesmo_autorizado_sem_habilitacao(self):
        r = self.client.post(
            "/tarefas/nova/",
            {"titulo": "Tarefa Própria", "prioridade": "media"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/tarefas/", fetch_redirect_response=False)

    def test_editar_get_autorizado(self):
        r = self.client.get(
            f"/tarefas/{self.tarefa.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_concluir_autorizado(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "concluida")

    def test_excluir_autorizado(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Tarefa.objects.filter(pk=self.tarefa.pk).exists())


class TestTarefasAtribuirOutrosAusente(TarefasAutorizacaoBase):
    """
    Usuário com módulo `tarefas` autorizado, mas sem
    `tarefas_atribuir_outros` — só pode criar/reatribuir tarefa para si
    mesmo; atribuição a terceiros é rejeitada.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_sem_atribuir_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Sem Atribuir Outros"
        tenant.slug = "tarefas-sem-atribuir-outros"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_atribuir_outros")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Tarefas Sem Atribuir Outros")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_TAREFAS)
        # Nenhuma HabilitacaoPapel para HAB_TAREFAS_ATRIBUIR_OUTROS —
        # módulo aberto, habilitação de atribuição a outros ausente.
        self.client.force_login(self.user)
        self.tarefa = self._tarefa(responsavel=self.user)

    def test_criar_para_outro_usuario_negado(self):
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            {
                "titulo": "Tentativa de Delegação",
                "prioridade": "media",
                "destinatario": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Tarefa.objects.count(), antes)

    def test_criar_para_si_mesmo_permitido(self):
        r = self.client.post(
            "/tarefas/nova/",
            {"titulo": "Tarefa Para Mim", "prioridade": "media"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/tarefas/", fetch_redirect_response=False)

    def test_reatribuir_para_outro_usuario_negado(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/reatribuir/",
            {"destinatario": self.outro_user.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.responsavel_id, self.user.pk)

    def test_reatribuir_para_si_mesmo_permitido(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/reatribuir/",
            {"destinatario": self.user.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)


class TestTarefasAtribuirOutrosConcedido(TarefasAutorizacaoBase):
    """
    Usuário com `tarefas_atribuir_outros` consegue criar e reatribuir
    tarefa para outro usuário.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_com_atribuir_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Com Atribuir Outros"
        tenant.slug = "tarefas-com-atribuir-outros"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_atribuir_outros")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Tarefas Com Atribuir Outros")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_TAREFAS)
        self._hp(papel, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS)
        self.client.force_login(self.user)
        self.tarefa = self._tarefa(responsavel=self.user)

    def test_criar_para_outro_usuario_permitido(self):
        r = self.client.post(
            "/tarefas/nova/",
            {
                "titulo": "Delegação Autorizada",
                "prioridade": "media",
                "destinatario": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/tarefas/", fetch_redirect_response=False)
        tarefa = Tarefa.objects.get(titulo="Delegação Autorizada")
        self.assertEqual(tarefa.responsavel_id, self.outro_user.pk)

    def test_reatribuir_para_outro_usuario_permitido(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/reatribuir/",
            {"destinatario": self.outro_user.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.responsavel_id, self.outro_user.pk)


class TestTarefasAtribuirOutrosAdmin(TarefasAutorizacaoBase):
    """Administrador do escritório dispensa `tarefas_atribuir_outros`."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_admin_atribuir_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Admin Atribuir Outros"
        tenant.slug = "tarefas-admin-atribuir-outros"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_escritorio")
        self._set_admin(self.admin, True)
        self.outro_user = self._user("outro_usuario")
        self.client.force_login(self.admin)

    def test_admin_cria_tarefa_para_outro_usuario(self):
        r = self.client.post(
            "/tarefas/nova/",
            {
                "titulo": "Delegação Pelo Admin",
                "prioridade": "media",
                "destinatario": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/tarefas/", fetch_redirect_response=False)
        tarefa = Tarefa.objects.get(titulo="Delegação Pelo Admin")
        self.assertEqual(tarefa.responsavel_id, self.outro_user.pk)
