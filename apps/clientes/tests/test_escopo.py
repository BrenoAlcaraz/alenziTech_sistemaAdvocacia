"""
Testes de escopo de dados (Fase B) para apps/clientes/views.py: escopo
efetivo por responsável, autorização sobre objeto (IDOR intra-tenant →
404), escalonamento de escopo negado (403), regra de responsabilidade
obrigatória e reatribuição restrita ao Administrador do escritório.

Segue o mesmo padrão de fixtures de apps/clientes/tests/test_autorizacao.py
(WI-0001) sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PermissaoPapel,
    PerfilUsuario,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_CLIENTES_EDITAR,
    MODULO_CLIENTES,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente


class ClientesEscopoBase(TenantTestCase):
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

    def _cliente(self, *, responsavel, **kwargs):
        defaults = {"nome_razao_social": "Cliente Teste", "tipo": "PF"}
        defaults.update(kwargs)
        return Cliente.objects.create(responsavel=responsavel, **defaults)


class TestClientesEscopoSomenteSeus(ClientesEscopoBase):
    """
    Usuário autorizado ao módulo `clientes`, com nível máximo
    `somente_seus` — vê e alcança apenas clientes de sua própria
    responsabilidade.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0002_clientes_somente_seus"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0002 Clientes Somente Seus"
        tenant.slug = "wi0002-clientes-somente-seus"

    def setUp(self):
        super().setUp()
        self.user = self._user("limitado_somente_seus")
        self.outro_user = self._user("outro_usuario")
        papel = self._new_papel("Papel Clientes Somente Seus")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_CLIENTES, nivel=NIVEL_SOMENTE_SEUS)
        self._hp(papel, MODULO_CLIENTES, HAB_CLIENTES_CRIAR)
        self._hp(papel, MODULO_CLIENTES, HAB_CLIENTES_EDITAR)
        self.client.force_login(self.user)

        self.cliente_proprio = self._cliente(
            nome_razao_social="Cliente Próprio", responsavel=self.user
        )
        self.cliente_alheio = self._cliente(
            nome_razao_social="Cliente Alheio", responsavel=self.outro_user
        )
        self.cliente_proprio_inativo = self._cliente(
            nome_razao_social="Cliente Próprio Inativo",
            responsavel=self.user,
            ativo=False,
        )
        self.cliente_alheio_inativo = self._cliente(
            nome_razao_social="Cliente Alheio Inativo",
            responsavel=self.outro_user,
            ativo=False,
        )

    def test_lista_mostra_apenas_clientes_proprios(self):
        r = self.client.get("/clientes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        nomes = [c.nome_razao_social for c in r.context["clientes"]]
        self.assertIn("Cliente Próprio", nomes)
        self.assertNotIn("Cliente Alheio", nomes)

    def test_inativos_respeita_escopo(self):
        r = self.client.get("/clientes/inativos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        nomes = [c.nome_razao_social for c in r.context["clientes"]]
        self.assertIn("Cliente Próprio Inativo", nomes)
        self.assertNotIn("Cliente Alheio Inativo", nomes)

    def test_detalhe_proprio_funciona(self):
        r = self.client.get(
            f"/clientes/{self.cliente_proprio.pk}/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_detalhe_alheio_retorna_404(self):
        r = self.client.get(
            f"/clientes/{self.cliente_alheio.pk}/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_editar_alheio_retorna_404(self):
        r = self.client.get(
            f"/clientes/{self.cliente_alheio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_desativar_alheio_retorna_404_sem_alterar(self):
        r = self.client.post(
            f"/clientes/{self.cliente_alheio.pk}/desativar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.cliente_alheio.refresh_from_db()
        self.assertTrue(self.cliente_alheio.ativo)

    def test_desativar_proprio_funciona(self):
        r = self.client.post(
            f"/clientes/{self.cliente_proprio.pk}/desativar/", HTTP_HOST=self.http_host
        )
        self.assertRedirects(r, "/clientes/", fetch_redirect_response=False)
        self.cliente_proprio.refresh_from_db()
        self.assertFalse(self.cliente_proprio.ativo)

    def test_reativar_alheio_retorna_404_sem_alterar(self):
        r = self.client.post(
            f"/clientes/{self.cliente_alheio_inativo.pk}/reativar/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.cliente_alheio_inativo.refresh_from_db()
        self.assertFalse(self.cliente_alheio_inativo.ativo)

    def test_reativar_proprio_funciona(self):
        r = self.client.post(
            f"/clientes/{self.cliente_proprio_inativo.pk}/reativar/",
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/clientes/inativos/", fetch_redirect_response=False)
        self.cliente_proprio_inativo.refresh_from_db()
        self.assertTrue(self.cliente_proprio_inativo.ativo)

    def test_escalar_para_todos_retorna_403(self):
        r = self.client.get("/clientes/?escopo=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_escopo_da_equipe_retorna_403(self):
        r = self.client.get("/clientes/?escopo=da_equipe", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_escopo_vazio_retorna_403(self):
        """
        `?escopo=` (presente, vazio) é um valor inválido — não deve ser
        confundido com o parâmetro ausente, que usaria o padrão.
        """
        r = self.client.get("/clientes/?escopo=", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_get_exibe_responsavel_real_do_cliente(self):
        """
        Em edição, o campo somente leitura deve mostrar o responsável real
        do cliente (nunca o usuário que está editando), mesmo quando os
        dois coincidem — a fonte do valor exibido deve ser sempre
        `cliente.responsavel`, não o usuário autenticado.
        """
        r = self.client.get(
            f"/clientes/{self.cliente_proprio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.context["responsavel_exibido"].pk,
            self.cliente_proprio.responsavel_id,
        )

    def test_novo_get_exibe_o_proprio_usuario_como_responsavel(self):
        r = self.client.get("/clientes/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["responsavel_exibido"].pk, self.user.pk)

    def test_criar_cliente_forca_responsavel_request_user(self):
        r = self.client.post(
            "/clientes/novo/",
            {
                "tipo": "PF",
                "nome_razao_social": "Cliente Criado Limitado",
                "responsavel": self.outro_user.pk,  # tentativa de adulteração
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/clientes/", fetch_redirect_response=False)
        cliente = Cliente.objects.get(nome_razao_social="Cliente Criado Limitado")
        self.assertEqual(cliente.responsavel_id, self.user.pk)

    def test_post_adulterado_em_editar_nao_troca_responsavel(self):
        r = self.client.post(
            f"/clientes/{self.cliente_proprio.pk}/editar/",
            {
                "tipo": "PF",
                "nome_razao_social": "Cliente Próprio Editado",
                "responsavel": self.outro_user.pk,  # tentativa de adulteração
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r,
            f"/clientes/{self.cliente_proprio.pk}/",
            fetch_redirect_response=False,
        )
        self.cliente_proprio.refresh_from_db()
        self.assertEqual(self.cliente_proprio.responsavel_id, self.user.pk)


class TestClientesEscopoTodos(ClientesEscopoBase):
    """
    Usuário autorizado ao módulo `clientes`, com nível máximo `todos`
    (não administrador) — vê todos os clientes autorizados por padrão,
    mas pode reduzir a visualização para `somente_seus`.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0002_clientes_todos"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0002 Clientes Todos"
        tenant.slug = "wi0002-clientes-todos"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_nivel_todos")
        self.outro_user = self._user("outro_usuario_todos")
        papel = self._new_papel("Papel Clientes Todos")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_CLIENTES, nivel=NIVEL_TODOS)
        self._hp(papel, MODULO_CLIENTES, HAB_CLIENTES_EDITAR)
        self.client.force_login(self.user)

        self.cliente_proprio = self._cliente(
            nome_razao_social="Cliente Próprio", responsavel=self.user
        )
        self.cliente_alheio = self._cliente(
            nome_razao_social="Cliente Alheio", responsavel=self.outro_user
        )
        self.cliente_alheio_inativo = self._cliente(
            nome_razao_social="Cliente Alheio Inativo",
            responsavel=self.outro_user,
            ativo=False,
        )

    def test_lista_padrao_mostra_todos(self):
        r = self.client.get("/clientes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        nomes = [c.nome_razao_social for c in r.context["clientes"]]
        self.assertIn("Cliente Próprio", nomes)
        self.assertIn("Cliente Alheio", nomes)

    def test_reduzir_para_somente_seus_funciona(self):
        r = self.client.get(
            "/clientes/?escopo=somente_seus", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        nomes = [c.nome_razao_social for c in r.context["clientes"]]
        self.assertIn("Cliente Próprio", nomes)
        self.assertNotIn("Cliente Alheio", nomes)

    def test_seletor_exibe_todos_e_somente_seus(self):
        r = self.client.get("/clientes/", HTTP_HOST=self.http_host)
        conteudo = r.content.decode()
        self.assertIn("escopo=todos", conteudo)
        self.assertIn("escopo=somente_seus", conteudo)
        self.assertIn("Da equipe", conteudo)

    # ── "Todos" é escopo de visualização, não autorização de mutação ──
    # Um não-administrador com nível máximo `todos` pode listar/visualizar
    # qualquer cliente, mas só pode editar/desativar/reativar clientes de
    # sua própria responsabilidade — mutação sobre cliente alheio é 404,
    # mesmo com nível de visualização `todos`.

    def test_detalhe_alheio_funciona_com_nivel_todos(self):
        r = self.client.get(
            f"/clientes/{self.cliente_alheio.pk}/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_editar_alheio_retorna_404_mesmo_com_nivel_todos(self):
        r = self.client.get(
            f"/clientes/{self.cliente_alheio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_desativar_alheio_retorna_404_mesmo_com_nivel_todos(self):
        r = self.client.post(
            f"/clientes/{self.cliente_alheio.pk}/desativar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.cliente_alheio.refresh_from_db()
        self.assertTrue(self.cliente_alheio.ativo)

    def test_reativar_alheio_retorna_404_mesmo_com_nivel_todos(self):
        r = self.client.post(
            f"/clientes/{self.cliente_alheio_inativo.pk}/reativar/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.cliente_alheio_inativo.refresh_from_db()
        self.assertFalse(self.cliente_alheio_inativo.ativo)

    def test_editar_proprio_funciona_com_nivel_todos(self):
        r = self.client.get(
            f"/clientes/{self.cliente_proprio.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)


class TestClientesEscopoAdmin(ClientesEscopoBase):
    """
    Administrador do escritório: acessa qualquer cliente por padrão,
    pode reduzir a visualização, e é o único que pode reatribuir
    responsável.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0002_clientes_admin"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0002 Clientes Admin"
        tenant.slug = "wi0002-clientes-admin"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_escritorio")
        self._set_admin(self.admin, True)
        self.outro_user = self._user("usuario_ativo_qualquer")
        self.usuario_inativo = self._user("usuario_inativo", is_active=False)
        self.client.force_login(self.admin)

        self.cliente_alheio = self._cliente(
            nome_razao_social="Cliente Alheio", responsavel=self.outro_user
        )

    def test_lista_admin_ve_todos_por_padrao(self):
        r = self.client.get("/clientes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        nomes = [c.nome_razao_social for c in r.context["clientes"]]
        self.assertIn("Cliente Alheio", nomes)

    def test_admin_pode_reduzir_para_somente_seus(self):
        r = self.client.get(
            "/clientes/?escopo=somente_seus", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        nomes = [c.nome_razao_social for c in r.context["clientes"]]
        self.assertNotIn("Cliente Alheio", nomes)

    def test_novo_get_preenche_responsavel_com_o_proprio_admin(self):
        r = self.client.get("/clientes/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.context["form"].initial.get("responsavel"), self.admin.pk
        )

    def test_admin_pode_reatribuir_responsavel(self):
        r = self.client.post(
            f"/clientes/{self.cliente_alheio.pk}/editar/",
            {
                "tipo": "PF",
                "nome_razao_social": "Cliente Alheio",
                "responsavel": self.admin.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r,
            f"/clientes/{self.cliente_alheio.pk}/",
            fetch_redirect_response=False,
        )
        self.cliente_alheio.refresh_from_db()
        self.assertEqual(self.cliente_alheio.responsavel_id, self.admin.pk)

    def test_admin_nao_pode_atribuir_usuario_inativo(self):
        responsavel_original = self.cliente_alheio.responsavel_id
        r = self.client.post(
            f"/clientes/{self.cliente_alheio.pk}/editar/",
            {
                "tipo": "PF",
                "nome_razao_social": "Cliente Alheio",
                "responsavel": self.usuario_inativo.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["form"].is_valid())
        self.cliente_alheio.refresh_from_db()
        self.assertEqual(self.cliente_alheio.responsavel_id, responsavel_original)

    def test_admin_pode_selecionar_outro_responsavel_na_criacao(self):
        r = self.client.post(
            "/clientes/novo/",
            {
                "tipo": "PF",
                "nome_razao_social": "Cliente Criado Pelo Admin",
                "responsavel": self.outro_user.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/clientes/", fetch_redirect_response=False)
        cliente = Cliente.objects.get(nome_razao_social="Cliente Criado Pelo Admin")
        self.assertEqual(cliente.responsavel_id, self.outro_user.pk)


class TestClienteResponsavelObrigatorio(ClientesEscopoBase):
    """`Cliente.responsavel` é obrigatório a nível de schema."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi0002_clientes_responsavel_obrigatorio"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0002 Clientes Responsavel Obrigatorio"
        tenant.slug = "wi0002-clientes-responsavel-obrigatorio"

    def test_cliente_sem_responsavel_nao_pode_ser_persistido(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cliente.objects.create(
                    nome_razao_social="Cliente Sem Responsável", tipo="PF"
                )
