"""
Testes de escopo de dados para apps/tarefas/views.py: filtro de leitura
por responsável (quadro/lista), autorização sobre objeto em mutação
(IDOR intra-tenant → 404), escalonamento de escopo negado (403) e
comportamento do Administrador do escritório.

Segue o mesmo padrão de fixtures de apps/clientes/tests/test_escopo.py
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
    MODULO_TAREFAS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.tarefas.models import Tarefa


class TarefasEscopoBase(TenantTestCase):
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


class TestTarefasEscopoSomenteSeus(TarefasEscopoBase):
    """
    Usuário autorizado ao módulo `tarefas`, com nível máximo
    `somente_seus` — vê e alcança apenas tarefas da própria
    responsabilidade.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_escopo_somente_seus"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Escopo Somente Seus"
        tenant.slug = "tarefas-escopo-somente-seus"

    def setUp(self):
        super().setUp()
        self.user = self._user("limitado_somente_seus")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Tarefas Somente Seus")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_TAREFAS, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.user)

        self.tarefa_propria = self._tarefa(
            titulo="Tarefa Própria", responsavel=self.user
        )
        self.tarefa_alheia = self._tarefa(
            titulo="Tarefa Alheia", responsavel=self.outro_user
        )

    def test_quadro_mostra_apenas_tarefas_proprias(self):
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [
            t.titulo for coluna in r.context["tarefas_por_status"].values() for t in coluna
        ]
        self.assertIn("Tarefa Própria", titulos)
        self.assertNotIn("Tarefa Alheia", titulos)

    def test_lista_mostra_apenas_tarefas_proprias(self):
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [t.titulo for t in r.context["tarefas"]]
        self.assertIn("Tarefa Própria", titulos)
        self.assertNotIn("Tarefa Alheia", titulos)

    def test_editar_alheia_retorna_404(self):
        r = self.client.get(
            f"/tarefas/{self.tarefa_alheia.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_concluir_alheia_retorna_404_sem_alterar(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa_alheia.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.tarefa_alheia.refresh_from_db()
        self.assertEqual(self.tarefa_alheia.status, "a_fazer")

    def test_excluir_alheia_retorna_404_sem_apagar(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa_alheia.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Tarefa.objects.filter(pk=self.tarefa_alheia.pk).exists())

    def test_concluir_propria_funciona(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa_propria.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa_propria.refresh_from_db()
        self.assertEqual(self.tarefa_propria.status, "concluida")

    def test_escalar_para_todos_retorna_403(self):
        r = self.client.get("/tarefas/?escopo=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_escopo_vazio_retorna_403(self):
        """
        `?escopo=` (presente, vazio) é um valor inválido — não deve ser
        confundido com o parâmetro ausente, que usaria o padrão.
        """
        r = self.client.get("/tarefas/?escopo=", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_com_escopo_invalido_retorna_403(self):
        """
        Rotas de mutação também validam `?escopo=`, mesmo sem usar o
        resultado para filtrar — mesmo padrão de
        `apps/clientes/views.py` (editar/desativar/reativar).
        """
        r = self.client.get(
            f"/tarefas/{self.tarefa_propria.pk}/editar/?escopo=todos",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestTarefasEscopoTodos(TarefasEscopoBase):
    """
    Usuário autorizado ao módulo `tarefas`, com nível máximo `todos`
    (não administrador) — vê todas as tarefas por padrão, mas só muta
    tarefa da própria responsabilidade.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_escopo_todos"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Escopo Todos"
        tenant.slug = "tarefas-escopo-todos"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_nivel_todos")
        self.outro_user = self._user("outro_usuario_todos")
        papel = self._new_papel("Papel Tarefas Todos")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_TAREFAS, nivel=NIVEL_TODOS)
        self.client.force_login(self.user)

        self.tarefa_propria = self._tarefa(
            titulo="Tarefa Própria", responsavel=self.user
        )
        self.tarefa_alheia = self._tarefa(
            titulo="Tarefa Alheia", responsavel=self.outro_user
        )

    def test_lista_padrao_mostra_todas(self):
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [t.titulo for t in r.context["tarefas"]]
        self.assertIn("Tarefa Própria", titulos)
        self.assertIn("Tarefa Alheia", titulos)

    def test_reduzir_para_somente_seus_funciona(self):
        r = self.client.get(
            "/tarefas/lista/?escopo=somente_seus", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        titulos = [t.titulo for t in r.context["tarefas"]]
        self.assertIn("Tarefa Própria", titulos)
        self.assertNotIn("Tarefa Alheia", titulos)

    # "Todos" é escopo de visualização, não autorização de mutação — um
    # não-administrador com nível máximo `todos` vê qualquer tarefa, mas
    # só muta tarefa da própria responsabilidade.

    def test_editar_alheia_retorna_404_mesmo_com_nivel_todos(self):
        r = self.client.get(
            f"/tarefas/{self.tarefa_alheia.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_concluir_alheia_retorna_404_mesmo_com_nivel_todos(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa_alheia.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.tarefa_alheia.refresh_from_db()
        self.assertEqual(self.tarefa_alheia.status, "a_fazer")

    def test_editar_propria_funciona_com_nivel_todos(self):
        r = self.client.get(
            f"/tarefas/{self.tarefa_propria.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)


class TestTarefasEscopoAdmin(TarefasEscopoBase):
    """Administrador do escritório muta qualquer tarefa do tenant."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_escopo_admin"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Tarefas Escopo Admin"
        tenant.slug = "tarefas-escopo-admin"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_escritorio")
        self._set_admin(self.admin, True)
        self.outro_user = self._user("usuario_ativo_qualquer")
        self.client.force_login(self.admin)

        self.tarefa_alheia = self._tarefa(
            titulo="Tarefa Alheia", responsavel=self.outro_user
        )

    def test_lista_admin_ve_tarefa_alheia(self):
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [t.titulo for t in r.context["tarefas"]]
        self.assertIn("Tarefa Alheia", titulos)

    def test_admin_edita_tarefa_alheia(self):
        r = self.client.get(
            f"/tarefas/{self.tarefa_alheia.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_admin_conclui_tarefa_alheia(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa_alheia.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa_alheia.refresh_from_db()
        self.assertEqual(self.tarefa_alheia.status, "concluida")

    def test_admin_exclui_tarefa_alheia(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa_alheia.pk}/excluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Tarefa.objects.filter(pk=self.tarefa_alheia.pk).exists())
