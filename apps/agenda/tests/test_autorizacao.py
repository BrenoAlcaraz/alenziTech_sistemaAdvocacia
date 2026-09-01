"""
Testes de autorização de módulo (Camada 1) e de habilitação funcional
(Camada 2) para apps/agenda/views.py.

Camada 1 cobre o enforcement de tem_permissao_modulo(user, "agenda") nas
sete rotas existentes (index, novo, editar, concluir, cancelar, reabrir,
excluir). Camada 2 cobre o enforcement de agenda_criar_para_outros em
`novo` — a única habilitação do módulo hoje.

Segue o mesmo padrão de fixtures de apps/tarefas/tests/test_autorizacao.py
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
    HAB_AGENDA_CRIAR_PARA_OUTROS,
    MODULO_AGENDA,
    NIVEL_TODOS,
)
from apps.agenda.models import Compromisso


class AgendaAutorizacaoBase(TenantTestCase):
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

    def _compromisso(self, *, responsavel, **kwargs):
        defaults = {
            "titulo": "Compromisso Teste",
            "data_hora_inicio": "2026-09-10T10:00:00Z",
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(responsavel=responsavel, **defaults)


class TestAgendaAutorizacaoModuloNegado(AgendaAutorizacaoBase):
    """
    Usuário autenticado sem autorização do módulo `agenda`
    (nenhum UsuarioPapel, nenhum Group técnico) — as sete rotas negam.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_autorizacao_negado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Autorizacao Negado"
        tenant.slug = "agenda-autorizacao-negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_agenda")
        self.client.force_login(self.user)
        self.compromisso = self._compromisso(responsavel=self.user)

    def test_index_negado(self):
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_get_negado(self):
        r = self.client.get("/agenda/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_post_negado_nao_cria_compromisso(self):
        antes = Compromisso.objects.count()
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Tentativa Negada",
                "tipo": "outro",
                "data_hora_inicio": "2026-09-10T10:00",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Compromisso.objects.count(), antes)

    def test_editar_get_negado(self):
        r = self.client.get(
            f"/agenda/{self.compromisso.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_concluir_negado_nao_altera_status(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.compromisso.refresh_from_db()
        self.assertEqual(self.compromisso.status, "agendado")

    def test_cancelar_negado(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_reabrir_negado(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/reabrir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_excluir_negado_nao_apaga(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Compromisso.objects.filter(pk=self.compromisso.pk).exists())


class TestAgendaAutorizacaoModuloConcedido(AgendaAutorizacaoBase):
    """
    Usuário autorizado ao módulo `agenda` (nível `todos`, via papel
    dinâmico) preserva o comportamento HTTP existente das sete rotas.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_autorizacao_concedido"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Autorizacao Concedido"
        tenant.slug = "agenda-autorizacao-concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_agenda")
        papel = self._new_papel("Papel Agenda Concedido")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_AGENDA)
        self.client.force_login(self.user)
        self.compromisso = self._compromisso(responsavel=self.user)

    def test_index_autorizado(self):
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "agenda/lista.html")

    def test_novo_get_autorizado(self):
        r = self.client.get("/agenda/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_novo_post_para_si_mesmo_autorizado_sem_habilitacao(self):
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Compromisso Próprio",
                "tipo": "outro",
                "data_hora_inicio": "2026-09-10T10:00",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/agenda/", fetch_redirect_response=False)

    def test_editar_get_autorizado(self):
        r = self.client.get(
            f"/agenda/{self.compromisso.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_concluir_autorizado(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.compromisso.refresh_from_db()
        self.assertEqual(self.compromisso.status, "concluido")

    def test_excluir_autorizado(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Compromisso.objects.filter(pk=self.compromisso.pk).exists())


class TestAgendaCriarParaOutrosAusente(AgendaAutorizacaoBase):
    """
    Usuário com módulo `agenda` autorizado, mas sem
    `agenda_criar_para_outros` — só pode criar compromisso para si
    mesmo; atribuição a terceiros é rejeitada.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_sem_criar_para_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Sem Criar Para Outros"
        tenant.slug = "agenda-sem-criar-para-outros"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_criar_para_outros")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Agenda Sem Criar Para Outros")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_AGENDA)
        # Nenhuma HabilitacaoPapel para HAB_AGENDA_CRIAR_PARA_OUTROS —
        # módulo aberto, habilitação de criação para outros ausente.
        self.client.force_login(self.user)

    def test_criar_para_outro_usuario_negado(self):
        antes = Compromisso.objects.count()
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Tentativa de Delegação",
                "tipo": "outro",
                "data_hora_inicio": "2026-09-10T10:00",
                "responsavel": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Compromisso.objects.count(), antes)

    def test_criar_para_si_mesmo_permitido(self):
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Compromisso Para Mim",
                "tipo": "outro",
                "data_hora_inicio": "2026-09-10T10:00",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/agenda/", fetch_redirect_response=False)


class TestAgendaCriarParaOutrosConcedido(AgendaAutorizacaoBase):
    """Usuário com `agenda_criar_para_outros` consegue criar compromisso para outro usuário."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_com_criar_para_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Com Criar Para Outros"
        tenant.slug = "agenda-com-criar-para-outros"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_criar_para_outros")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Agenda Com Criar Para Outros")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_AGENDA)
        self._hp(papel, MODULO_AGENDA, HAB_AGENDA_CRIAR_PARA_OUTROS)
        self.client.force_login(self.user)

    def test_criar_para_outro_usuario_permitido(self):
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Delegação Autorizada",
                "tipo": "outro",
                "data_hora_inicio": "2026-09-10T10:00",
                "responsavel": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/agenda/", fetch_redirect_response=False)
        compromisso = Compromisso.objects.get(titulo="Delegação Autorizada")
        self.assertEqual(compromisso.responsavel_id, self.outro_user.pk)


class TestAgendaCriarParaOutrosAdmin(AgendaAutorizacaoBase):
    """Administrador do escritório dispensa `agenda_criar_para_outros`."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_admin_criar_para_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Admin Criar Para Outros"
        tenant.slug = "agenda-admin-criar-para-outros"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_escritorio")
        self._set_admin(self.admin, True)
        self.outro_user = self._user("outro_usuario")
        self.client.force_login(self.admin)

    def test_admin_cria_compromisso_para_outro_usuario(self):
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Delegação Pelo Admin",
                "tipo": "outro",
                "data_hora_inicio": "2026-09-10T10:00",
                "responsavel": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/agenda/", fetch_redirect_response=False)
        compromisso = Compromisso.objects.get(titulo="Delegação Pelo Admin")
        self.assertEqual(compromisso.responsavel_id, self.outro_user.pk)
