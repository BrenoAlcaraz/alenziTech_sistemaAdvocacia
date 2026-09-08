"""
Testes de participantes e confirmação de presença em Compromisso —
ticket "Agenda: participantes e confirmação de presença em
compromisso" (spec `specs/agenda-participantes-confirmacao.md`):
visibilidade em `somente_seus`, gestão de participantes reaproveitando
a autorização de edição já existente (sem habilitação nova),
confirmação/recusa como ação do próprio participante sobre o próprio
registro, notificação de convite e reset de confirmação ao reagendar.

Segue o mesmo padrão de fixtures de apps/agenda/tests/test_escopo.py
sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_SOMENTE_SEUS
from apps.agenda.models import Compromisso, ParticipanteCompromisso
from apps.notificacoes.models import Notificacao


class AgendaParticipantesBase(TenantTestCase):
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

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_SOMENTE_SEUS):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=ativo, nivel=nivel
        )

    def _dar_acesso_agenda(self, user, *, nivel=NIVEL_SOMENTE_SEUS):
        papel = self._new_papel(f"Papel Agenda {user.username}")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_AGENDA, nivel=nivel)

    def _compromisso(self, *, responsavel, **kwargs):
        defaults = {
            "titulo": "Compromisso Teste",
            "data_hora_inicio": "2026-09-10T10:00:00Z",
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(responsavel=responsavel, **defaults)

    def _participacao(self, compromisso, usuario, *, status=ParticipanteCompromisso.STATUS_PENDENTE):
        return ParticipanteCompromisso.objects.create(
            compromisso=compromisso, usuario=usuario, status=status
        )


class TestVisibilidadeParticipante(AgendaParticipantesBase):
    """Participante vê o compromisso em `somente_seus` mesmo sem ser responsável."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_part_visibilidade"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Participantes Visibilidade"
        tenant.slug = "agenda-part-visibilidade"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel")
        self.participante = self._user("participante")
        self.estranho = self._user("estranho")
        for user in (self.responsavel, self.participante, self.estranho):
            self._dar_acesso_agenda(user)

        self.compromisso = self._compromisso(
            titulo="Reunião com participante", responsavel=self.responsavel
        )
        self._participacao(self.compromisso, self.participante)

    def test_participante_ve_compromisso_em_somente_seus(self):
        self.client.force_login(self.participante)
        r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertIn("Reunião com participante", titulos)

    def test_estranho_nao_ve_compromisso_em_somente_seus(self):
        self.client.force_login(self.estranho)
        r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertNotIn("Reunião com participante", titulos)

    def test_participante_recusado_continua_vendo_o_compromisso(self):
        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.participante
        )
        participacao.status = ParticipanteCompromisso.STATUS_RECUSADO
        participacao.save(update_fields=["status"])

        self.client.force_login(self.participante)
        r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
        titulos = [c.titulo for c in r.context["compromissos"]]
        self.assertIn("Reunião com participante", titulos)


class TestGerenciarParticipantes(AgendaParticipantesBase):
    """
    Adicionar/remover participante reaproveita a autorização de edição
    do compromisso já existente — responsável ou Administrador do
    escritório, sem habilitação granular própria.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_part_gerenciar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Participantes Gerenciar"
        tenant.slug = "agenda-part-gerenciar"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel")
        self.convidado = self._user("convidado")
        self.outro_usuario = self._user("outro_usuario")
        for user in (self.responsavel, self.convidado, self.outro_usuario):
            self._dar_acesso_agenda(user)

        self.compromisso = self._compromisso(
            titulo="Compromisso Gerenciado", responsavel=self.responsavel
        )

    def test_responsavel_adiciona_participante_e_notifica(self):
        self.client.force_login(self.responsavel)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/adicionar/",
            {"usuario": self.convidado.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/agenda/{self.compromisso.pk}/editar/", fetch_redirect_response=False
        )
        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.convidado
        )
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_PENDENTE)
        notificacao = Notificacao.objects.get(destinatario=self.convidado)
        self.assertIn(self.compromisso.titulo, notificacao.mensagem)

    def test_usuario_alheio_nao_adiciona_participante(self):
        self.client.force_login(self.outro_usuario)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/adicionar/",
            {"usuario": self.convidado.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.assertFalse(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso).exists()
        )

    def test_responsavel_nao_convida_a_si_mesmo(self):
        self.client.force_login(self.responsavel)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/adicionar/",
            {"usuario": self.responsavel.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)

    def test_responsavel_remove_participante(self):
        self._participacao(self.compromisso, self.convidado)
        self.client.force_login(self.responsavel)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/{self.convidado.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/agenda/{self.compromisso.pk}/editar/", fetch_redirect_response=False
        )
        self.assertFalse(
            ParticipanteCompromisso.objects.filter(
                compromisso=self.compromisso, usuario=self.convidado
            ).exists()
        )

    def test_usuario_alheio_nao_remove_participante(self):
        self._participacao(self.compromisso, self.convidado)
        self.client.force_login(self.outro_usuario)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/{self.convidado.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.assertTrue(
            ParticipanteCompromisso.objects.filter(
                compromisso=self.compromisso, usuario=self.convidado
            ).exists()
        )

    def test_admin_adiciona_participante_sem_ser_responsavel(self):
        admin = self._user("admin_escritorio")
        self._set_admin(admin, True)
        self.client.force_login(admin)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/adicionar/",
            {"usuario": self.convidado.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/agenda/{self.compromisso.pk}/editar/", fetch_redirect_response=False
        )
        self.assertTrue(
            ParticipanteCompromisso.objects.filter(
                compromisso=self.compromisso, usuario=self.convidado
            ).exists()
        )


class TestConfirmarRecusarPresenca(AgendaParticipantesBase):
    """Confirmar/recusar presença é ação do próprio participante sobre o
    próprio registro — não depende de ser responsável nem admin."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_part_confirmar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Participantes Confirmar"
        tenant.slug = "agenda-part-confirmar"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel")
        self.participante = self._user("participante")
        self.outro_participante = self._user("outro_participante")
        for user in (self.responsavel, self.participante, self.outro_participante):
            self._dar_acesso_agenda(user)

        self.compromisso = self._compromisso(
            titulo="Compromisso Confirmação", responsavel=self.responsavel
        )
        self._participacao(self.compromisso, self.participante)
        self._participacao(self.compromisso, self.outro_participante)

    def test_participante_confirma_a_propria_presenca(self):
        self.client.force_login(self.participante)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/confirmar-presenca/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.participante
        )
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_CONFIRMADO)

    def test_participante_recusa_a_propria_presenca(self):
        self.client.force_login(self.participante)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/recusar-presenca/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.participante
        )
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_RECUSADO)

    def test_confirmar_nao_afeta_participacao_de_outro_usuario(self):
        self.client.force_login(self.participante)
        self.client.post(
            f"/agenda/{self.compromisso.pk}/confirmar-presenca/", HTTP_HOST=self.http_host
        )
        outro = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.outro_participante
        )
        self.assertEqual(outro.status, ParticipanteCompromisso.STATUS_PENDENTE)

    def test_responsavel_nao_confirma_presenca_de_outro_participante(self):
        self.client.force_login(self.responsavel)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/confirmar-presenca/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)

    def test_nao_participante_recebe_404_ao_tentar_confirmar(self):
        estranho = self._user("estranho")
        self._dar_acesso_agenda(estranho)
        self.client.force_login(estranho)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/confirmar-presenca/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)


class TestResetConfirmacaoPorReagendamento(AgendaParticipantesBase):
    """
    Alterar `data_hora_inicio` na edição volta confirmação já dada para
    pendente e notifica o participante afetado; participante ainda
    pendente ou recusado não gera notificação de reagendamento.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_part_reagendamento"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Participantes Reagendamento"
        tenant.slug = "agenda-part-reagendamento"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel")
        self.confirmado = self._user("confirmado")
        self.pendente = self._user("pendente")
        for user in (self.responsavel, self.confirmado, self.pendente):
            self._dar_acesso_agenda(user)

        self.compromisso = self._compromisso(
            titulo="Compromisso Reagendável",
            responsavel=self.responsavel,
            data_hora_inicio="2026-09-10T10:00:00Z",
        )
        self._participacao(
            self.compromisso, self.confirmado, status=ParticipanteCompromisso.STATUS_CONFIRMADO
        )
        self._participacao(
            self.compromisso, self.pendente, status=ParticipanteCompromisso.STATUS_PENDENTE
        )

    def _editar_data(self, nova_data):
        self.client.force_login(self.responsavel)
        return self.client.post(
            f"/agenda/{self.compromisso.pk}/editar/",
            {
                "titulo": self.compromisso.titulo,
                "tipo": "outro",
                "data_hora_inicio": nova_data,
            },
            HTTP_HOST=self.http_host,
        )

    def test_reagendar_volta_confirmado_para_pendente_e_notifica(self):
        r = self._editar_data("2026-09-15T14:00")
        self.assertRedirects(r, "/agenda/", fetch_redirect_response=False)

        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.confirmado
        )
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_PENDENTE)
        notificacao = Notificacao.objects.get(destinatario=self.confirmado)
        self.assertIn("reagendado", notificacao.mensagem)

    def test_reagendar_nao_notifica_quem_ja_estava_pendente(self):
        self._editar_data("2026-09-15T14:00")
        self.assertFalse(Notificacao.objects.filter(destinatario=self.pendente).exists())

    def test_editar_sem_mudar_data_nao_reseta_confirmacao(self):
        # Mesmo horário do fixture, mas expresso na hora local usada pelo
        # formulário — o fixture usa "Z" (UTC); comparar strings distintas
        # de fuso não deve ser confundido com uma mudança real de data.
        self.compromisso.refresh_from_db()
        mesma_data_local = timezone.localtime(
            self.compromisso.data_hora_inicio
        ).strftime("%Y-%m-%dT%H:%M")
        self._editar_data(mesma_data_local)
        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.confirmado
        )
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_CONFIRMADO)
        self.assertFalse(Notificacao.objects.filter(destinatario=self.confirmado).exists())
