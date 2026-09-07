"""
Testes do filtro de Processo por Cliente no formulário de Compromissos e
do endpoint que o alimenta (specs/filtro-processo-por-cliente.md).

Segue o mesmo padrão de fixtures de apps/agenda/tests/test_autorizacao.py
sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_TODOS
from apps.agenda.forms import CompromissoForm
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.saas_tenants.models import Dominio


class FiltroProcessoClienteAgendaBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _conceder_modulo(self, user, *, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel Agenda {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_AGENDA, ativo=True, nivel=nivel
        )

    def _cliente(self, nome, *, responsavel):
        return Cliente.objects.create(nome_razao_social=nome, tipo="PF", responsavel=responsavel)

    def _processo(self, titulo, *, cliente, responsavel, status="ativo"):
        return Processo.objects.create(
            titulo=titulo, cliente=cliente, responsavel=responsavel, status=status
        )


class TestCompromissoFormValidaProcessoDoCliente(FiltroProcessoClienteAgendaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_filtro_processo_cliente"

    def setUp(self):
        super().setUp()
        self.user = self._user("resp_agenda")
        self.cliente_a = self._cliente("Cliente A", responsavel=self.user)
        self.cliente_b = self._cliente("Cliente B", responsavel=self.user)
        self.processo_a = self._processo("Processo A", cliente=self.cliente_a, responsavel=self.user)
        self.processo_b = self._processo("Processo B", cliente=self.cliente_b, responsavel=self.user)

    def _dados_base(self, **extra):
        dados = {"titulo": "Compromisso Teste", "tipo": "outro", "data_hora_inicio": "2026-09-10T10:00"}
        dados.update(extra)
        return dados

    def test_queryset_do_processo_e_restrito_ao_cliente_ja_selecionado(self):
        form = CompromissoForm(data=self._dados_base(cliente=self.cliente_a.id))
        self.assertIn(self.processo_a, form.fields["processo"].queryset)
        self.assertNotIn(self.processo_b, form.fields["processo"].queryset)

    def test_processo_de_outro_cliente_e_rejeitado_na_validacao(self):
        form = CompromissoForm(data=self._dados_base(cliente=self.cliente_a.id, processo=self.processo_b.id))
        self.assertFalse(form.is_valid())
        self.assertIn("processo", form.errors)

    def test_processo_do_mesmo_cliente_e_aceito(self):
        form = CompromissoForm(data=self._dados_base(cliente=self.cliente_a.id, processo=self.processo_a.id))
        self.assertTrue(form.is_valid(), form.errors)


class TestEndpointProcessosPorClienteAgenda(FiltroProcessoClienteAgendaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_endpoint_processos_cliente"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_acesso_agenda")
        self._conceder_modulo(self.user)
        self.sem_acesso = self._user("sem_acesso_agenda")

        self.cliente_a = self._cliente("Cliente A", responsavel=self.user)
        self.cliente_b = self._cliente("Cliente B", responsavel=self.user)
        self.processo_a = self._processo("Processo A", cliente=self.cliente_a, responsavel=self.user)
        self.processo_b = self._processo("Processo B", cliente=self.cliente_b, responsavel=self.user)

    def test_retorna_apenas_processos_do_cliente_informado(self):
        self.client.force_login(self.user)
        r = self.client.get(
            "/agenda/processos-por-cliente/",
            {"cliente": self.cliente_a.id},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        ids = [p["id"] for p in r.json()["processos"]]
        self.assertEqual(ids, [self.processo_a.id])

    def test_sem_permissao_do_modulo_agenda_retorna_403(self):
        self.client.force_login(self.sem_acesso)
        r = self.client.get(
            "/agenda/processos-por-cliente/",
            {"cliente": self.cliente_a.id},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
