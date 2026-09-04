"""
Testes de regra de negócio de Honorários advocatícios (PDR-0007).

Cobre: confirmar recebimento exclusivo do Administrador do escritório,
notificação ao advogado responsável pelo processo (nunca a quem
confirmou), validação de valor efetivo/data recebida obrigatórios, e
cancelamento. Autorização de módulo/nível de dados das rotas é coberta
em test_autorizacao.py — não aqui.

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_autorizacao.py sobre
django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.clientes.models import Cliente
from apps.financeiro.models import Honorario
from apps.notificacoes.models import Notificacao
from apps.processos.models import Processo
from apps.saas_tenants.models import Dominio


class HonorariosBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _set_admin(self, user, value=True):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=value)

    def _conceder_modulo(self, user, *, nivel=NIVEL_DADOS_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel Financeiro {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_FINANCEIRO, ativo=True, nivel=nivel
        )

    def _processo(self, *, responsavel):
        cliente = Cliente.objects.create(nome_razao_social="Cliente Teste", responsavel=responsavel)
        return Processo.objects.create(titulo="Processo Teste", cliente=cliente, responsavel=responsavel)

    def _honorario(self, **kwargs):
        defaults = {"tipo": "contratual", "valor_estimado": "2000.00"}
        defaults.update(kwargs)
        return Honorario.objects.create(**defaults)


class TestConfirmarRecebimentoAdminOnly(HonorariosBase):
    """Confirmar recebimento é ação exclusiva do Administrador do
    escritório, independentemente do nível de acesso ao módulo
    (docs/modules/financeiro.md#honorários-pdr-0007)."""

    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_admin_only"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Honorarios Admin Only"
        tenant.slug = "honorarios-admin-only"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_escritorio")
        self._conceder_modulo(self.admin)
        self._set_admin(self.admin, True)

        self.nao_admin = self._user("financeiro_dados_todos")
        self._conceder_modulo(self.nao_admin)

        self.honorario = self._honorario()

    def test_get_negado_para_nao_admin(self):
        self.client.force_login(self.nao_admin)
        r = self.client.get(
            f"/financeiro/honorarios/{self.honorario.pk}/confirmar-recebimento/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_post_negado_para_nao_admin_nao_altera_status(self):
        self.client.force_login(self.nao_admin)
        r = self.client.post(
            f"/financeiro/honorarios/{self.honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "2000.00", "data_recebida": "2026-09-10"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.honorario.refresh_from_db()
        self.assertEqual(self.honorario.status, "previsto")

    def test_get_autorizado_para_admin(self):
        self.client.force_login(self.admin)
        r = self.client.get(
            f"/financeiro/honorarios/{self.honorario.pk}/confirmar-recebimento/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)

    def test_post_autorizado_para_admin_confirma_recebimento(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            f"/financeiro/honorarios/{self.honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "1800.00", "data_recebida": "2026-09-10"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/financeiro/honorarios/", fetch_redirect_response=False)
        self.honorario.refresh_from_db()
        self.assertEqual(self.honorario.status, "recebido")
        self.assertEqual(str(self.honorario.valor_efetivo), "1800.00")
        self.assertEqual(str(self.honorario.data_recebida), "2026-09-10")

    def test_post_sem_valor_efetivo_rejeitado(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            f"/financeiro/honorarios/{self.honorario.pk}/confirmar-recebimento/",
            {"data_recebida": "2026-09-10"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)
        self.honorario.refresh_from_db()
        self.assertEqual(self.honorario.status, "previsto")

    def test_post_sem_data_recebida_rejeitado(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            f"/financeiro/honorarios/{self.honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "2000.00"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)
        self.honorario.refresh_from_db()
        self.assertEqual(self.honorario.status, "previsto")

    def test_post_valor_efetivo_zero_rejeitado(self):
        self.client.force_login(self.admin)
        r = self.client.post(
            f"/financeiro/honorarios/{self.honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "0.00", "data_recebida": "2026-09-10"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)


class TestConfirmarRecebimentoNotificacao(HonorariosBase):
    """Ao confirmar recebimento, notifica o advogado responsável pelo
    processo vinculado — nunca o Administrador que confirmou."""

    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_notificacao"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Honorarios Notificacao"
        tenant.slug = "honorarios-notificacao"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_escritorio")
        self._conceder_modulo(self.admin)
        self._set_admin(self.admin, True)
        self.client.force_login(self.admin)

    def test_confirmar_com_processo_notifica_responsavel(self):
        advogado = self._user("advogado_responsavel")
        processo = self._processo(responsavel=advogado)
        honorario = self._honorario(processo=processo, cliente=processo.cliente)
        antes = Notificacao.objects.count()

        r = self.client.post(
            f"/financeiro/honorarios/{honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "2000.00", "data_recebida": "2026-09-10"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Notificacao.objects.count(), antes + 1)
        notificacao = Notificacao.objects.latest("criado_em")
        self.assertEqual(notificacao.destinatario, advogado)

    def test_confirmar_sem_processo_nao_notifica(self):
        honorario = self._honorario()
        antes = Notificacao.objects.count()

        r = self.client.post(
            f"/financeiro/honorarios/{honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "2000.00", "data_recebida": "2026-09-10"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Notificacao.objects.count(), antes)

    def test_admin_confirma_proprio_processo_nao_notifica_a_si_mesmo(self):
        processo = self._processo(responsavel=self.admin)
        honorario = self._honorario(processo=processo, cliente=processo.cliente)
        antes = Notificacao.objects.count()

        r = self.client.post(
            f"/financeiro/honorarios/{honorario.pk}/confirmar-recebimento/",
            {"valor_efetivo": "2000.00", "data_recebida": "2026-09-10"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        honorario.refresh_from_db()
        self.assertEqual(honorario.status, "recebido")
        self.assertEqual(Notificacao.objects.count(), antes)


class TestHonorarioForm(HonorariosBase):
    """Validação de negócio no cadastro (valor estimado > 0)."""

    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_form"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Honorarios Form"
        tenant.slug = "honorarios-form"

    def setUp(self):
        super().setUp()
        self.user = self._user("financeiro_dados_todos")
        self._conceder_modulo(self.user)
        self.client.force_login(self.user)

    def test_criar_com_valor_estimado_zero_rejeitado(self):
        antes = Honorario.objects.count()
        r = self.client.post(
            "/financeiro/honorarios/novo/",
            {"tipo": "contratual", "valor_estimado": "0.00"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors)
        self.assertEqual(Honorario.objects.count(), antes)


class TestCancelarHonorario(HonorariosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "honorarios_cancelar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Honorarios Cancelar"
        tenant.slug = "honorarios-cancelar"

    def setUp(self):
        super().setUp()
        self.user = self._user("financeiro_dados_todos")
        self._conceder_modulo(self.user)
        self.client.force_login(self.user)

    def test_cancelar_nao_admin_autorizado(self):
        """Cancelar não é restrito ao Administrador — diferente de
        confirmar recebimento."""
        honorario = self._honorario()
        r = self.client.post(
            f"/financeiro/honorarios/{honorario.pk}/cancelar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        honorario.refresh_from_db()
        self.assertEqual(honorario.status, "cancelado")
