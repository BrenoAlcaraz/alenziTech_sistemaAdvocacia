"""
Testes de cancelamento consultável de Compromisso — ticket "Agenda:
cancelamento consultável e indicadores de confirmação no Dashboard"
(spec `specs/agenda-participantes-confirmacao.md`): notificação
distinta de cancelamento para responsável e participantes, compromisso
cancelado saindo da grade operacional padrão, seção "Cancelados"
(consulta, escopo, sem reativar) e `cancelado_em` registrado/limpo.

Segue o mesmo padrão de fixtures de apps/agenda/tests/test_escopo.py
sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_SOMENTE_SEUS, NIVEL_TODOS
from apps.agenda.models import Compromisso, ParticipanteCompromisso
from apps.notificacoes.models import Notificacao


class AgendaCancelamentoBase(TenantTestCase):
    """Helpers de fixture e de acesso HTTP compartilhados pelos testes deste módulo."""

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_acesso_agenda(self, user, *, nivel=NIVEL_SOMENTE_SEUS):
        papel = PapelAcesso.objects.create(nome=f"Papel Agenda {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_AGENDA, ativo=True, nivel=nivel
        )

    def _compromisso(self, *, responsavel, **kwargs):
        defaults = {
            "titulo": "Compromisso Teste",
            "data_hora_inicio": "2026-09-10T10:00:00Z",
            "status": "agendado",
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(responsavel=responsavel, **defaults)

    def _participacao(self, compromisso, usuario, *, status=ParticipanteCompromisso.STATUS_PENDENTE):
        return ParticipanteCompromisso.objects.create(
            compromisso=compromisso, usuario=usuario, status=status
        )


class TestCancelarNotificaEExclui(AgendaCancelamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_cancelar_notifica"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Cancelar Notifica"
        tenant.slug = "agenda-cancelar-notifica"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel")
        self.confirmado = self._user("confirmado")
        self.pendente = self._user("pendente")
        self._dar_acesso_agenda(self.responsavel, nivel=NIVEL_TODOS)

        self.compromisso = self._compromisso(
            titulo="Reunião a Cancelar", responsavel=self.responsavel
        )
        self._participacao(self.compromisso, self.confirmado, status=ParticipanteCompromisso.STATUS_CONFIRMADO)
        self._participacao(self.compromisso, self.pendente, status=ParticipanteCompromisso.STATUS_PENDENTE)

    def test_cancelar_notifica_responsavel_e_todos_os_participantes(self):
        self.client.force_login(self.responsavel)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)

        for destinatario in (self.responsavel, self.confirmado, self.pendente):
            notificacao = Notificacao.objects.get(destinatario=destinatario)
            self.assertIn("cancelado", notificacao.mensagem.lower())
            self.assertIn(self.compromisso.titulo, notificacao.mensagem)

    def test_cancelar_registra_cancelado_em(self):
        self.client.force_login(self.responsavel)
        self.client.post(f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host)
        self.compromisso.refresh_from_db()
        self.assertIsNotNone(self.compromisso.cancelado_em)

    def test_reabrir_limpa_cancelado_em(self):
        self.client.force_login(self.responsavel)
        self.client.post(f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host)
        self.client.post(f"/agenda/{self.compromisso.pk}/reabrir/", HTTP_HOST=self.http_host)
        self.compromisso.refresh_from_db()
        self.assertIsNone(self.compromisso.cancelado_em)
        self.assertEqual(self.compromisso.status, "agendado")

    def test_compromisso_cancelado_some_da_grade_operacional_para_todos(self):
        self.client.force_login(self.responsavel)
        self.client.post(f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host)

        for user in (self.responsavel, self.confirmado, self.pendente):
            if user != self.responsavel:
                self._dar_acesso_agenda(user)
            self.client.force_login(user)
            r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
            titulos = [c.titulo for c in r.context["compromissos"]]
            self.assertNotIn("Reunião a Cancelar", titulos)


class TestCancelarEIdempotente(AgendaCancelamentoBase):
    """
    Regressão do review final: cancelar um compromisso já cancelado não
    pode resetar `cancelado_em` (quebraria a janela de retenção de 7
    dias) nem reenviar notificação de cancelamento.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_cancelar_idempotente"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Cancelar Idempotente"
        tenant.slug = "agenda-cancelar-idempotente"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel")
        self.confirmado = self._user("confirmado")
        self._dar_acesso_agenda(self.responsavel)

        self.compromisso = self._compromisso(
            titulo="Reunião a Cancelar Duas Vezes", responsavel=self.responsavel
        )
        self._participacao(
            self.compromisso, self.confirmado, status=ParticipanteCompromisso.STATUS_CONFIRMADO
        )
        self.client.force_login(self.responsavel)
        self.client.post(f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host)
        self.compromisso.refresh_from_db()
        self.cancelado_em_original = self.compromisso.cancelado_em

    def test_segundo_cancelar_nao_reseta_cancelado_em(self):
        self.client.post(f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host)
        self.compromisso.refresh_from_db()
        self.assertEqual(self.compromisso.cancelado_em, self.cancelado_em_original)

    def test_segundo_cancelar_nao_duplica_notificacao(self):
        self.client.post(f"/agenda/{self.compromisso.pk}/cancelar/", HTTP_HOST=self.http_host)
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.confirmado).count(), 1
        )
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.responsavel).count(), 1
        )


class TestSecaoCancelados(AgendaCancelamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_secao_cancelados"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Secao Cancelados"
        tenant.slug = "agenda-secao-cancelados"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel")
        self.outro = self._user("outro_responsavel")
        self._dar_acesso_agenda(self.responsavel)
        self._dar_acesso_agenda(self.outro)

        self.compromisso_proprio = self._compromisso(
            titulo="Cancelado Próprio", responsavel=self.responsavel
        )
        self.compromisso_alheio = self._compromisso(
            titulo="Cancelado Alheio", responsavel=self.outro
        )
        for c in (self.compromisso_proprio, self.compromisso_alheio):
            self.client.force_login(c.responsavel)
            self.client.post(f"/agenda/{c.pk}/cancelar/", HTTP_HOST=self.http_host)

        self.compromisso_agendado = self._compromisso(
            titulo="Ainda Agendado", responsavel=self.responsavel
        )

    def test_cancelados_lista_apenas_cancelados_no_escopo(self):
        self.client.force_login(self.responsavel)
        r = self.client.get("/agenda/cancelados/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertIn("Cancelado Próprio", titulos)
        self.assertNotIn("Cancelado Alheio", titulos)
        self.assertNotIn("Ainda Agendado", titulos)

    def test_cancelados_nao_oferece_reativar(self):
        self.client.force_login(self.responsavel)
        r = self.client.get("/agenda/cancelados/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "Reabrir")

    def test_cancelados_exige_autorizacao_de_modulo(self):
        sem_acesso = self._user("sem_acesso_agenda")
        self.client.force_login(sem_acesso)
        r = self.client.get("/agenda/cancelados/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)
