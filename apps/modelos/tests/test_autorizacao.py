"""
Testes de autorização de módulo (Camada 1) e de habilitação funcional
(Camada 2) para apps/modelos/views.py.

Camada 1 cobre o enforcement de tem_permissao_modulo(user, MODULO_MODELOS)
nas cinco rotas existentes (lista, novo, detalhe, editar, importar).
Camada 2 cobre o enforcement de tem_habilitacao() em `novo` e `importar`
(modelos_criar) — únicas rotas que criam ModeloPeca. `modelos_editar_estilo`
não tem view própria ainda (aba "Meu estilo" é placeholder) e continua
fora do escopo (ver docs/STATUS.md).

Segue o mesmo padrão de fixtures de apps/clientes/tests/test_autorizacao.py.
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
    HAB_MODELOS_CRIAR,
    MODULO_MODELOS,
    NIVEL_TODOS,
)
from apps.modelos.models import ModeloPeca


class ModelosAutorizacaoBase(TenantTestCase):
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

    def _admin(self, username="admin_modelos"):
        admin = self._user(username)
        PerfilUsuario.objects.filter(user=admin).update(is_admin_escritorio=True)
        return admin

    def _modelo(self, *, criado_por, **kwargs):
        defaults = {
            "titulo": "Modelo Teste",
            "categoria": "Petição inicial",
            "area_direito": "civil",
            "conteudo": "Conteúdo de teste.",
        }
        defaults.update(kwargs)
        return ModeloPeca.objects.create(criado_por=criado_por, **defaults)


class TestModelosAutorizacaoModuloNegado(ModelosAutorizacaoBase):
    """Usuário sem autorização do módulo `modelos` — as cinco rotas negam."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_modelos")
        self.client.force_login(self.user)
        self.modelo = self._modelo(criado_por=self.user)

    def test_lista_negada(self):
        r = self.client.get("/modelos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_negado(self):
        r = self.client.get("/modelos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_detalhe_negado(self):
        r = self.client.get(f"/modelos/{self.modelo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_negado(self):
        r = self.client.get(
            f"/modelos/{self.modelo.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_importar_negado(self):
        r = self.client.get("/modelos/importar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)


class TestModelosAutorizacaoModuloConcedido(ModelosAutorizacaoBase):
    """Usuário com autorização do módulo `modelos` — as cinco rotas operam normalmente."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_modelos")
        papel = self._new_papel("Papel Modelos")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        # modelos_criar concedida aqui para representar o caminho autorizado
        # completo de novo/importar (Camada 1 + Camada 2).
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        self.client.force_login(self.user)
        self.modelo = self._modelo(criado_por=self.user)

    def test_lista_ok(self):
        r = self.client.get("/modelos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_novo_ok(self):
        r = self.client.get("/modelos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_detalhe_ok(self):
        r = self.client.get(f"/modelos/{self.modelo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_editar_ok(self):
        r = self.client.get(
            f"/modelos/{self.modelo.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_importar_ok(self):
        r = self.client.get("/modelos/importar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)


class TestModelosAutorizacaoHabilitacaoCriarAusente(ModelosAutorizacaoBase):
    """
    Usuário com módulo `modelos` autorizado, mas sem `modelos_criar`
    (Camada 2) — prova que módulo autorizado não equivale a poder criar.
    Leitura (lista/detalhe) e edição de ModeloPeca existente (sem
    habilitação própria no kernel) continuam liberadas.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_sem_criar"

    def setUp(self):
        super().setUp()
        self.user = self._user("modulo_sem_modelos_criar")
        papel = self._new_papel("Papel Modelos Sem Criar")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        # Nenhuma HabilitacaoPapel para HAB_MODELOS_CRIAR — módulo aberto,
        # habilitação de criação ausente.
        self.client.force_login(self.user)
        self.modelo = self._modelo(criado_por=self.user)

    def test_novo_negado(self):
        r = self.client.get("/modelos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_importar_negado(self):
        r = self.client.get("/modelos/importar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_lista_continua_liberada(self):
        r = self.client.get("/modelos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_detalhe_continua_liberado(self):
        r = self.client.get(f"/modelos/{self.modelo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_editar_continua_liberado(self):
        r = self.client.get(
            f"/modelos/{self.modelo.pk}/editar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)


class TestModelosAutorizacaoAdminIndependeDeHabilitacao(ModelosAutorizacaoBase):
    """Administrador do escritório cria/importa modelo sem habilitação explícita (bypass do kernel)."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_admin_independe"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.client.force_login(self.admin)

    def test_novo_ok(self):
        r = self.client.get("/modelos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_importar_ok(self):
        r = self.client.get("/modelos/importar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
