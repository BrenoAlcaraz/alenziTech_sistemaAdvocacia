"""
Testes de autorização de módulo (Camada 1) e de habilitação funcional
(Camada 2) para apps/clientes/views.py.

Camada 1 cobre o enforcement de tem_permissao_modulo(user, "clientes") nas
sete rotas existentes (lista, detalhe, novo, editar, desativar, inativos,
reativar). Camada 2 cobre o enforcement de tem_habilitacao() apenas em
`novo` (clientes_criar) e `editar` (clientes_editar) — nenhuma outra
operação possui habilitação específica no kernel atual. Os usuários
positivos de "novo" e "editar" já recebiam clientes_criar/clientes_editar
desde a preparação da Camada 1, justamente para permanecer estáveis com a
Camada 2 agora implementada.

Segue o mesmo padrão de fixtures de apps/accounts/tests/ (_user, _new_papel,
_assign_papel, _pp, _hp) sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_CLIENTES_EDITAR,
    MODULO_CLIENTES,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente


class ClientesAutorizacaoBase(TenantTestCase):
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

    def _cliente(self, **kwargs):
        defaults = {"nome_razao_social": "Cliente Teste", "tipo": "PF"}
        defaults.update(kwargs)
        return Cliente.objects.create(**defaults)


class TestClientesAutorizacaoModuloNegado(ClientesAutorizacaoBase):
    """
    Usuário autenticado sem autorização do módulo `clientes`
    (nenhum UsuarioPapel, nenhum Group técnico) — as sete rotas negam.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0001_clientes_negado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0001 Clientes Negado"
        tenant.slug = "wi0001-clientes-negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_clientes")
        self.client.force_login(self.user)
        self.cliente_ativo = self._cliente(nome_razao_social="Cliente Ativo")
        self.cliente_inativo = self._cliente(
            nome_razao_social="Cliente Inativo", ativo=False
        )

    def test_lista_negada(self):
        r = self.client.get("/clientes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_detalhe_negado(self):
        r = self.client.get(
            f"/clientes/{self.cliente_ativo.pk}/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_inativos_negado(self):
        r = self.client.get("/clientes/inativos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_get_negado(self):
        r = self.client.get("/clientes/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_post_negado_nao_cria_cliente(self):
        antes = Cliente.objects.count()
        r = self.client.post(
            "/clientes/novo/",
            {"tipo": "PF", "nome_razao_social": "Tentativa Negada"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Cliente.objects.count(), antes)

    def test_editar_get_negado(self):
        r = self.client.get(
            f"/clientes/{self.cliente_ativo.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_editar_post_negado_preserva_valores(self):
        nome_original = self.cliente_ativo.nome_razao_social
        r = self.client.post(
            f"/clientes/{self.cliente_ativo.pk}/editar/",
            {"tipo": "PF", "nome_razao_social": "Nome Alterado Indevido"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.cliente_ativo.refresh_from_db()
        self.assertEqual(self.cliente_ativo.nome_razao_social, nome_original)

    def test_desativar_get_negado(self):
        r = self.client.get(
            f"/clientes/{self.cliente_ativo.pk}/desativar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_desativar_post_negado_nao_altera_ativo(self):
        r = self.client.post(
            f"/clientes/{self.cliente_ativo.pk}/desativar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.cliente_ativo.refresh_from_db()
        self.assertTrue(self.cliente_ativo.ativo)

    def test_reativar_get_negado(self):
        r = self.client.get(
            f"/clientes/{self.cliente_inativo.pk}/reativar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_reativar_post_negado_nao_altera_ativo(self):
        r = self.client.post(
            f"/clientes/{self.cliente_inativo.pk}/reativar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)
        self.cliente_inativo.refresh_from_db()
        self.assertFalse(self.cliente_inativo.ativo)


class TestClientesAutorizacaoModuloConcedido(ClientesAutorizacaoBase):
    """
    Usuário autorizado ao módulo `clientes` (via papel dinâmico) preserva
    o comportamento HTTP existente das sete rotas.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0001_clientes_concedido"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0001 Clientes Concedido"
        tenant.slug = "wi0001-clientes-concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_clientes")
        papel = self._new_papel("Papel Clientes Concedido")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_CLIENTES)
        # As habilitações de criação e edição são concedidas neste fixture
        # para representar o caminho autorizado completo de novo/editar
        # (Camada 1 + Camada 2).
        self._hp(papel, MODULO_CLIENTES, HAB_CLIENTES_CRIAR)
        self._hp(papel, MODULO_CLIENTES, HAB_CLIENTES_EDITAR)
        self.client.force_login(self.user)
        self.cliente_ativo = self._cliente(nome_razao_social="Cliente Ativo")
        self.cliente_inativo = self._cliente(
            nome_razao_social="Cliente Inativo", ativo=False
        )

    def test_lista_autorizada(self):
        r = self.client.get("/clientes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "clientes/lista.html")

    def test_detalhe_autorizado(self):
        r = self.client.get(
            f"/clientes/{self.cliente_ativo.pk}/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "clientes/detalhe.html")

    def test_inativos_autorizado(self):
        r = self.client.get("/clientes/inativos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "clientes/inativos.html")

    def test_novo_get_autorizado(self):
        r = self.client.get("/clientes/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "clientes/form.html")

    def test_novo_post_autorizado_cria_cliente(self):
        antes = Cliente.objects.count()
        r = self.client.post(
            "/clientes/novo/",
            {"tipo": "PF", "nome_razao_social": "Cliente Novo Autorizado"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/clientes/", fetch_redirect_response=False)
        self.assertEqual(Cliente.objects.count(), antes + 1)

    def test_editar_get_autorizado(self):
        r = self.client.get(
            f"/clientes/{self.cliente_ativo.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "clientes/form.html")

    def test_editar_post_autorizado_altera_cliente(self):
        r = self.client.post(
            f"/clientes/{self.cliente_ativo.pk}/editar/",
            {"tipo": "PF", "nome_razao_social": "Nome Alterado Autorizado"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/clientes/{self.cliente_ativo.pk}/", fetch_redirect_response=False
        )
        self.cliente_ativo.refresh_from_db()
        self.assertEqual(
            self.cliente_ativo.nome_razao_social, "Nome Alterado Autorizado"
        )

    def test_desativar_get_autorizado_preserva_redirect_fallback(self):
        r = self.client.get(
            f"/clientes/{self.cliente_ativo.pk}/desativar/", HTTP_HOST=self.http_host
        )
        self.assertRedirects(
            r, f"/clientes/{self.cliente_ativo.pk}/", fetch_redirect_response=False
        )
        self.cliente_ativo.refresh_from_db()
        self.assertTrue(self.cliente_ativo.ativo)

    def test_desativar_post_autorizado_desativa_cliente(self):
        r = self.client.post(
            f"/clientes/{self.cliente_ativo.pk}/desativar/", HTTP_HOST=self.http_host
        )
        self.assertRedirects(r, "/clientes/", fetch_redirect_response=False)
        self.cliente_ativo.refresh_from_db()
        self.assertFalse(self.cliente_ativo.ativo)

    def test_reativar_get_autorizado_preserva_redirect_fallback(self):
        r = self.client.get(
            f"/clientes/{self.cliente_inativo.pk}/reativar/", HTTP_HOST=self.http_host
        )
        self.assertRedirects(r, "/clientes/inativos/", fetch_redirect_response=False)
        self.cliente_inativo.refresh_from_db()
        self.assertFalse(self.cliente_inativo.ativo)

    def test_reativar_post_autorizado_reativa_cliente(self):
        r = self.client.post(
            f"/clientes/{self.cliente_inativo.pk}/reativar/", HTTP_HOST=self.http_host
        )
        self.assertRedirects(r, "/clientes/inativos/", fetch_redirect_response=False)
        self.cliente_inativo.refresh_from_db()
        self.assertTrue(self.cliente_inativo.ativo)


class TestClientesAutorizacaoHabilitacaoCriarAusente(ClientesAutorizacaoBase):
    """
    Usuário com módulo `clientes` autorizado, mas sem `clientes_criar`
    (Camada 2) — prova que módulo autorizado não equivale a poder criar.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0001_clientes_sem_criar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0001 Clientes Sem Criar"
        tenant.slug = "wi0001-clientes-sem-criar"

    def setUp(self):
        super().setUp()
        self.user = self._user("modulo_sem_clientes_criar")
        papel = self._new_papel("Papel Clientes Sem Criar")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_CLIENTES)
        # Nenhuma HabilitacaoPapel para HAB_CLIENTES_CRIAR — módulo aberto,
        # habilitação de criação ausente.
        self.client.force_login(self.user)

    def test_novo_get_negado(self):
        r = self.client.get("/clientes/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_post_negado_nao_cria_cliente(self):
        antes = Cliente.objects.count()
        r = self.client.post(
            "/clientes/novo/",
            {"tipo": "PF", "nome_razao_social": "Tentativa Sem Habilitacao"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Cliente.objects.count(), antes)


class TestClientesAutorizacaoHabilitacaoEditarAusente(ClientesAutorizacaoBase):
    """
    Usuário com módulo `clientes` autorizado, mas sem `clientes_editar`
    (Camada 2) — prova que módulo autorizado não equivale a poder editar.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0001_clientes_sem_editar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0001 Clientes Sem Editar"
        tenant.slug = "wi0001-clientes-sem-editar"

    def setUp(self):
        super().setUp()
        self.user = self._user("modulo_sem_clientes_editar")
        papel = self._new_papel("Papel Clientes Sem Editar")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_CLIENTES)
        # Nenhuma HabilitacaoPapel para HAB_CLIENTES_EDITAR — módulo aberto,
        # habilitação de edição ausente.
        self.client.force_login(self.user)
        self.cliente_ativo = self._cliente(nome_razao_social="Cliente Ativo")

    def test_editar_get_negado(self):
        r = self.client.get(
            f"/clientes/{self.cliente_ativo.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_editar_post_negado_preserva_valores(self):
        nome_original = self.cliente_ativo.nome_razao_social
        r = self.client.post(
            f"/clientes/{self.cliente_ativo.pk}/editar/",
            {"tipo": "PF", "nome_razao_social": "Nome Alterado Sem Habilitacao"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.cliente_ativo.refresh_from_db()
        self.assertEqual(self.cliente_ativo.nome_razao_social, nome_original)
