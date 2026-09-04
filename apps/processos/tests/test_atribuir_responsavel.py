"""
Testes de PDR-0014 — habilitação `processos_atribuir_responsavel`.

Cobre exclusivamente a reatribuição do responsável principal de
Processos: quem, além do Administrador, pode fazê-lo, e que o escopo de
mutação (Administrador ou responsavel == request.user, conforme
ARCHITECTURE.md) não é alterado por esta habilitação — ela apenas
libera o campo `responsavel` dentro do escopo de mutação já existente.

Segue o mesmo padrão de fixtures de test_escopo.py
(TenantTestCase, _user/_admin/_autorizar/_cliente/_processo/_payload).
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
    HAB_PROCESSOS_ANDAMENTO_ADICIONAR,
    HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL,
    HAB_PROCESSOS_CRIAR,
    HAB_PROCESSOS_EDITAR,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
)
from apps.clientes.models import Cliente
from apps.processos.models import Processo

FORM_BASE = {
    "area_direito": "CÍVEL",
    "fase": "conhecimento",
    "instancia": "1ª Instância",
    "gratuidade_justica_status": "nao_requerida",
}


class AtribuirResponsavelBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _admin(self, username="admin_atribuicao"):
        user = self._user(username)
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        return user

    def _autorizar(self, user, *, nivel=NIVEL_SOMENTE_SEUS, com_habilitacao=False):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PROCESSOS, ativo=True, nivel=nivel
        )
        for item in (
            HAB_PROCESSOS_CRIAR,
            HAB_PROCESSOS_EDITAR,
            HAB_PROCESSOS_ANDAMENTO_ADICIONAR,
        ):
            HabilitacaoPapel.objects.create(
                papel=papel,
                tipo_conta=None,
                modulo=MODULO_PROCESSOS,
                item=item,
                ativo=True,
            )
        if com_habilitacao:
            HabilitacaoPapel.objects.create(
                papel=papel,
                tipo_conta=None,
                modulo=MODULO_PROCESSOS,
                item=HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL,
                ativo=True,
            )
        return papel

    def _cliente(self, responsavel, nome="Cliente Atribuição"):
        return Cliente.objects.create(
            nome_razao_social=nome, tipo="PF", responsavel=responsavel, ativo=True
        )

    def _processo(self, responsavel, cliente, titulo="Processo Atribuição"):
        return Processo.objects.create(
            titulo=titulo, responsavel=responsavel, cliente=cliente, status="ativo"
        )

    def _payload(self, cliente, titulo="Processo alterado", **extra):
        payload = {"titulo": titulo, "cliente": cliente.pk, **FORM_BASE}
        payload.update(extra)
        return payload


class TestSemHabilitacaoNemAdmin(AtribuirResponsavelBase):
    """Usuário só com o módulo aberto não reatribui responsável, nem por POST direto."""

    @classmethod
    def get_test_schema_name(cls):
        return "pdr0014_sem_habilitacao"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_habilitacao_atribuir")
        self.outro_elegivel = self._user("outro_elegivel_sem_hab")
        self._autorizar(self.user)
        self._autorizar(self.outro_elegivel)
        self.cliente = self._cliente(self.user)
        self.processo = self._processo(self.user, self.cliente)
        self.client.force_login(self.user)

    def test_form_novo_nao_expoe_campo_responsavel(self):
        resposta = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        self.assertNotIn("responsavel", resposta.context["form"].fields)

    def test_post_editar_com_responsavel_e_ignorado(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._payload(self.cliente, responsavel=self.outro_elegivel.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.user.pk)

    def test_post_novo_com_responsavel_e_ignorado_usa_criador(self):
        resposta = self.client.post(
            "/processos/novo/",
            self._payload(self.cliente, titulo="Novo sem hab", responsavel=self.outro_elegivel.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        criado = Processo.objects.get(titulo="Novo sem hab")
        self.assertEqual(criado.responsavel_id, self.user.pk)


class TestComHabilitacaoAtribuirResponsavel(AtribuirResponsavelBase):
    """
    Usuário com `processos_atribuir_responsavel`, sem ser Administrador,
    reatribui o responsável dentro do seu escopo de mutação (processos
    dos quais já é responsável — PDR-0014 não amplia o escopo de
    mutação estabelecido em ARCHITECTURE.md, só libera o campo).
    """

    @classmethod
    def get_test_schema_name(cls):
        return "pdr0014_com_habilitacao"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_habilitacao_atribuir")
        self.elegivel = self._user("elegivel_com_hab")
        self._autorizar(self.user, com_habilitacao=True)
        self._autorizar(self.elegivel)
        self.cliente = self._cliente(self.user)
        self.processo = self._processo(self.user, self.cliente)
        self.client.force_login(self.user)

    def test_form_expoe_campo_responsavel_com_candidatos_elegiveis(self):
        resposta = self.client.get(
            f"/processos/{self.processo.pk}/editar/", HTTP_HOST=self.http_host
        )
        campo = resposta.context["form"].fields["responsavel"]
        self.assertIn("responsavel", resposta.context["form"].fields)
        self.assertIn(self.elegivel, campo.queryset)

    def test_reatribui_processo_do_qual_e_responsavel(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._payload(self.cliente, responsavel=self.elegivel.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.elegivel.pk)

    def test_define_responsavel_diferente_ao_criar(self):
        resposta = self.client.post(
            "/processos/novo/",
            self._payload(self.cliente, titulo="Novo com hab", responsavel=self.elegivel.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        criado = Processo.objects.get(titulo="Novo com hab")
        self.assertEqual(criado.responsavel_id, self.elegivel.pk)

    def test_nao_alcanca_processo_do_qual_nao_e_responsavel_nem_admin(self):
        alheio = self._processo(self.elegivel, self.cliente, "Processo alheio")
        resposta = self.client.post(
            f"/processos/{alheio.pk}/editar/",
            self._payload(self.cliente, responsavel=self.user.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 404)
        alheio.refresh_from_db()
        self.assertEqual(alheio.responsavel_id, self.elegivel.pk)


class TestAdministradorIndependeDaHabilitacao(AtribuirResponsavelBase):
    """Administrador continua reatribuindo qualquer processo sem depender da habilitação."""

    @classmethod
    def get_test_schema_name(cls):
        return "pdr0014_admin_independe"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.elegivel = self._user("elegivel_admin_indep")
        self._autorizar(self.elegivel)
        self.cliente = self._cliente(self.admin)
        self.processo = self._processo(self.elegivel, self.cliente)
        self.client.force_login(self.admin)

    def test_admin_reatribui_processo_alheio_sem_habilitacao_concedida(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._payload(self.cliente, responsavel=self.admin.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.admin.pk)
