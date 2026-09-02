"""
Testes de PDR-0014 — integrantes habilitados de Processos.

Cobre a relação N:N `Processo.integrantes_habilitados`: quem pode
gerenciá-la (exclusivamente `gerir_habilitar_usuario_processos`, kernel
já existente e nunca antes aplicado em view) e que ela não afeta
responsável principal nem prazos.

Segue o mesmo padrão de fixtures de test_atribuir_responsavel.py.
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
    HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
    MODULO_GERIR,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
)
from apps.clientes.models import Cliente
from apps.processos.models import Processo


class IntegrantesBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _admin(self, username="admin_integrantes"):
        user = self._user(username)
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        return user

    def _autorizar_processos(self, user, *, nivel=NIVEL_SOMENTE_SEUS):
        papel = PapelAcesso.objects.create(nome=f"Papel Processos {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PROCESSOS, ativo=True, nivel=nivel
        )
        return papel

    def _conceder_gerir_habilitar(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel Gerir {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        HabilitacaoPapel.objects.create(
            papel=papel,
            tipo_conta=None,
            modulo=MODULO_GERIR,
            item=HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
            ativo=True,
        )
        return papel

    def _cliente(self, responsavel, nome="Cliente Integrantes"):
        return Cliente.objects.create(
            nome_razao_social=nome, tipo="PF", responsavel=responsavel, ativo=True
        )

    def _processo(self, responsavel, cliente, titulo="Processo Integrantes"):
        return Processo.objects.create(
            titulo=titulo, responsavel=responsavel, cliente=cliente, status="ativo"
        )


class TestGerenciarIntegrantesComHabilitacao(IntegrantesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0014_integrantes_com_habilitacao"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_integrantes")
        self._autorizar_processos(self.responsavel)
        self.gestor = self._user("gestor_integrantes")
        self._conceder_gerir_habilitar(self.gestor)
        self.candidato = self._user("candidato_integrante")
        self._autorizar_processos(self.candidato)
        self.cliente = self._cliente(self.responsavel)
        self.processo = self._processo(self.responsavel, self.cliente)
        self.client.force_login(self.gestor)

    def test_adiciona_integrante(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/adicionar/",
            {"usuario": self.candidato.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            resposta,
            f"/processos/{self.processo.pk}/?aba=integrantes",
            fetch_redirect_response=False,
        )
        self.assertIn(self.candidato, self.processo.integrantes_habilitados.all())

    def test_adicionar_integrante_nao_altera_responsavel_principal(self):
        self.client.post(
            f"/processos/{self.processo.pk}/integrantes/adicionar/",
            {"usuario": self.candidato.pk},
            HTTP_HOST=self.http_host,
        )
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.responsavel.pk)

    def test_remove_integrante(self):
        self.processo.integrantes_habilitados.add(self.candidato)
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/{self.candidato.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            resposta,
            f"/processos/{self.processo.pk}/?aba=integrantes",
            fetch_redirect_response=False,
        )
        self.assertNotIn(self.candidato, self.processo.integrantes_habilitados.all())

    def test_remover_integrante_inexistente_e_404(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/{self.candidato.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 404)


class TestGerenciarIntegrantesSemHabilitacao(IntegrantesBase):
    """Módulo `processos` aberto, mas sem `gerir_habilitar_usuario_processos` — nega."""

    @classmethod
    def get_test_schema_name(cls):
        return "pdr0014_integrantes_sem_habilitacao"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_sem_hab_int")
        self._autorizar_processos(self.responsavel)
        self.candidato = self._user("candidato_sem_hab_int")
        self._autorizar_processos(self.candidato)
        self.cliente = self._cliente(self.responsavel)
        self.processo = self._processo(self.responsavel, self.cliente)
        self.client.force_login(self.responsavel)

    def test_adicionar_integrante_negado(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/adicionar/",
            {"usuario": self.candidato.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(self.processo.integrantes_habilitados.count(), 0)

    def test_remover_integrante_negado(self):
        self.processo.integrantes_habilitados.add(self.candidato)
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/{self.candidato.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertIn(self.candidato, self.processo.integrantes_habilitados.all())


class TestGerenciarIntegrantesAdministrador(IntegrantesBase):
    """Administrador gerencia integrantes mesmo sem HabilitacaoPapel concedida (bypass do kernel)."""

    @classmethod
    def get_test_schema_name(cls):
        return "pdr0014_integrantes_admin"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.responsavel = self._user("responsavel_admin_int")
        self._autorizar_processos(self.responsavel)
        self.candidato = self._user("candidato_admin_int")
        self._autorizar_processos(self.candidato)
        self.cliente = self._cliente(self.responsavel)
        self.processo = self._processo(self.responsavel, self.cliente)
        self.client.force_login(self.admin)

    def test_admin_adiciona_integrante_sem_habilitacao_explicita(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/adicionar/",
            {"usuario": self.candidato.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(self.candidato, self.processo.integrantes_habilitados.all())
