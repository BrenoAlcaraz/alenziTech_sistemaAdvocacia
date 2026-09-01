"""
Testes de escopo de dados para apps/agenda/views.py: filtro de leitura
por responsável (index), autorização sobre objeto em mutação (IDOR
intra-tenant → 404), escalonamento de escopo negado (403), preservação
do responsável ao editar e comportamento do Administrador do
escritório.

Segue o mesmo padrão de fixtures de apps/tarefas/tests/test_escopo.py
sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.models import Compromisso


class AgendaEscopoBase(TenantTestCase):
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

    def _compromisso(self, *, responsavel, **kwargs):
        defaults = {
            "titulo": "Compromisso Teste",
            "data_hora_inicio": "2026-09-10T10:00:00Z",
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(responsavel=responsavel, **defaults)


class TestAgendaEscopoSomenteSeus(AgendaEscopoBase):
    """
    Usuário autorizado ao módulo `agenda`, com nível máximo
    `somente_seus` — vê e alcança apenas compromissos da própria
    responsabilidade.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_escopo_somente_seus"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Escopo Somente Seus"
        tenant.slug = "agenda-escopo-somente-seus"

    def setUp(self):
        super().setUp()
        self.user = self._user("limitado_somente_seus")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Agenda Somente Seus")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_AGENDA, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.user)

        self.compromisso_proprio = self._compromisso(
            titulo="Compromisso Próprio", responsavel=self.user
        )
        self.compromisso_alheio = self._compromisso(
            titulo="Compromisso Alheio", responsavel=self.outro_user
        )

    def test_index_mostra_apenas_compromissos_proprios(self):
        r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertIn("Compromisso Próprio", titulos)
        self.assertNotIn("Compromisso Alheio", titulos)

    def test_editar_alheio_retorna_404(self):
        r = self.client.get(
            f"/agenda/{self.compromisso_alheio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_concluir_alheio_retorna_404_sem_alterar(self):
        r = self.client.post(
            f"/agenda/{self.compromisso_alheio.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.compromisso_alheio.refresh_from_db()
        self.assertEqual(self.compromisso_alheio.status, "agendado")

    def test_excluir_alheio_retorna_404_sem_apagar(self):
        r = self.client.post(
            f"/agenda/{self.compromisso_alheio.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Compromisso.objects.filter(pk=self.compromisso_alheio.pk).exists())

    def test_concluir_proprio_funciona(self):
        r = self.client.post(
            f"/agenda/{self.compromisso_proprio.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.compromisso_proprio.refresh_from_db()
        self.assertEqual(self.compromisso_proprio.status, "concluido")

    def test_escalar_para_todos_retorna_403(self):
        r = self.client.get("/agenda/?escopo=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_escopo_vazio_retorna_403(self):
        """
        `?escopo=` (presente, vazio) é um valor inválido — não deve ser
        confundido com o parâmetro ausente, que usaria o padrão.
        """
        r = self.client.get("/agenda/?escopo=", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_com_escopo_invalido_retorna_403(self):
        """
        Rotas de mutação também validam `?escopo=`, mesmo sem usar o
        resultado para filtrar — mesmo padrão de
        `apps/tarefas/views.py`.
        """
        r = self.client.get(
            f"/agenda/{self.compromisso_proprio.pk}/editar/?escopo=todos",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestAgendaEscopoTodos(AgendaEscopoBase):
    """
    Usuário autorizado ao módulo `agenda`, com nível máximo `todos`
    (não administrador) — vê todos os compromissos por padrão, mas só
    muta compromisso da própria responsabilidade.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_escopo_todos"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Escopo Todos"
        tenant.slug = "agenda-escopo-todos"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_nivel_todos")
        self.outro_user = self._user("outro_usuario_todos")
        papel = self._new_papel("Papel Agenda Todos")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_AGENDA, nivel=NIVEL_TODOS)
        self.client.force_login(self.user)

        self.compromisso_proprio = self._compromisso(
            titulo="Compromisso Próprio", responsavel=self.user
        )
        self.compromisso_alheio = self._compromisso(
            titulo="Compromisso Alheio", responsavel=self.outro_user
        )

    def test_index_padrao_mostra_todos(self):
        r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertIn("Compromisso Próprio", titulos)
        self.assertIn("Compromisso Alheio", titulos)

    def test_reduzir_para_somente_seus_funciona(self):
        r = self.client.get(
            "/agenda/?filtro=todos&escopo=somente_seus", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertIn("Compromisso Próprio", titulos)
        self.assertNotIn("Compromisso Alheio", titulos)

    # "Todos" é escopo de visualização, não autorização de mutação — um
    # não-administrador com nível máximo `todos` vê qualquer compromisso,
    # mas só muta compromisso da própria responsabilidade.

    def test_editar_alheio_retorna_404_mesmo_com_nivel_todos(self):
        r = self.client.get(
            f"/agenda/{self.compromisso_alheio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_concluir_alheio_retorna_404_mesmo_com_nivel_todos(self):
        r = self.client.post(
            f"/agenda/{self.compromisso_alheio.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.compromisso_alheio.refresh_from_db()
        self.assertEqual(self.compromisso_alheio.status, "agendado")

    def test_editar_proprio_funciona_com_nivel_todos(self):
        r = self.client.get(
            f"/agenda/{self.compromisso_proprio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)


class TestAgendaEscopoAdmin(AgendaEscopoBase):
    """Administrador do escritório muta qualquer compromisso do tenant."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_escopo_admin"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Escopo Admin"
        tenant.slug = "agenda-escopo-admin"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_escritorio")
        self._set_admin(self.admin, True)
        self.outro_user = self._user("usuario_ativo_qualquer")
        self.client.force_login(self.admin)

        self.compromisso_alheio = self._compromisso(
            titulo="Compromisso Alheio", responsavel=self.outro_user
        )

    def test_index_admin_ve_compromisso_alheio(self):
        r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertIn("Compromisso Alheio", titulos)

    def test_admin_edita_compromisso_alheio(self):
        r = self.client.get(
            f"/agenda/{self.compromisso_alheio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_admin_conclui_compromisso_alheio(self):
        r = self.client.post(
            f"/agenda/{self.compromisso_alheio.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.compromisso_alheio.refresh_from_db()
        self.assertEqual(self.compromisso_alheio.status, "concluido")

    def test_admin_exclui_compromisso_alheio(self):
        r = self.client.post(
            f"/agenda/{self.compromisso_alheio.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Compromisso.objects.filter(pk=self.compromisso_alheio.pk).exists())


class TestAgendaEditarPreservaResponsavel(AgendaEscopoBase):
    """
    `editar` nunca reatribui o compromisso a outro responsável, mesmo
    que o formulário submetido traga um valor diferente — não existe em
    Agenda um fluxo equivalente ao "reatribuir" de Tarefas.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_editar_preserva_responsavel"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Editar Preserva Responsavel"
        tenant.slug = "agenda-editar-preserva-responsavel"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_compromisso")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Agenda Editar")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_AGENDA, nivel=NIVEL_TODOS)
        self.client.force_login(self.user)

        self.compromisso = self._compromisso(
            titulo="Compromisso Original", responsavel=self.user
        )

    def test_editar_ignora_responsavel_diferente_no_formulario(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/editar/",
            {
                "titulo": "Compromisso Editado",
                "tipo": "outro",
                "data_hora_inicio": "2026-09-11T10:00",
                "responsavel": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/agenda/", fetch_redirect_response=False)
        self.compromisso.refresh_from_db()
        self.assertEqual(self.compromisso.titulo, "Compromisso Editado")
        self.assertEqual(self.compromisso.responsavel_id, self.user.pk)
