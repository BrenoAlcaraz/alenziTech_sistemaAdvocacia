"""
Testes dos blocos pessoais de Agenda no Dashboard — ticket "Agenda:
cancelamento consultável e indicadores de confirmação no Dashboard"
(spec `specs/agenda-participantes-confirmacao.md`): "próximos
compromissos confirmados" (responsável ou participante confirmado, 7
dias) e "confirmação pendente" (participação própria pendente) — ambos
sempre pessoais, independente do nível somente_seus/todos do módulo
Agenda.

Segue o mesmo padrão de fixtures de
apps/dashboard/tests/test_escopo.py sobre
django_tenants.test.cases.TenantTestCase.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, MODULO_PAINEL, NIVEL_TODOS
from apps.agenda.models import Compromisso, ParticipanteCompromisso


class DashboardAgendaPessoalBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_acesso(self, user, *, nivel_agenda=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_AGENDA, ativo=True, nivel=nivel_agenda
        )
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PAINEL, ativo=True, nivel=NIVEL_TODOS
        )

    def _compromisso(self, *, responsavel, dias_a_frente=2, **kwargs):
        defaults = {
            "titulo": "Compromisso Teste",
            "status": "agendado",
            "data_hora_inicio": timezone.now() + timedelta(days=dias_a_frente),
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(responsavel=responsavel, **defaults)

    def _get_painel(self):
        return self.client.get("/", HTTP_HOST=self.http_host)


class TestBlocoConfirmados(DashboardAgendaPessoalBase):
    """
    Bloco "próximos compromissos confirmados" inclui compromisso onde o
    usuário é responsável ou participante confirmado — mesmo com nível
    `todos`, nunca mostra compromisso alheio onde não participa.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_agenda_confirmados"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("dashboard_confirmados")
        self.outro = self._user("dashboard_outro")
        self._dar_acesso(self.usuario, nivel_agenda=NIVEL_TODOS)
        self.client.force_login(self.usuario)

        self.proprio = self._compromisso(
            titulo="Compromisso Próprio", responsavel=self.outro
        )
        self.proprio.responsavel = self.usuario
        self.proprio.save()

        self.participante_confirmado = self._compromisso(
            titulo="Participante Confirmado", responsavel=self.outro
        )
        ParticipanteCompromisso.objects.create(
            compromisso=self.participante_confirmado,
            usuario=self.usuario,
            status=ParticipanteCompromisso.STATUS_CONFIRMADO,
        )

        self.participante_pendente = self._compromisso(
            titulo="Participante Pendente", responsavel=self.outro
        )
        ParticipanteCompromisso.objects.create(
            compromisso=self.participante_pendente,
            usuario=self.usuario,
            status=ParticipanteCompromisso.STATUS_PENDENTE,
        )

        self.alheio = self._compromisso(titulo="Totalmente Alheio", responsavel=self.outro)

    def test_confirmados_inclui_proprio_e_participante_confirmado(self):
        resposta = self._get_painel()
        titulos = [c.titulo for c in resposta.context["compromissos_dashboard"]]
        self.assertIn("Compromisso Próprio", titulos)
        self.assertIn("Participante Confirmado", titulos)

    def test_confirmados_exclui_participante_pendente_e_alheio_mesmo_com_nivel_todos(self):
        resposta = self._get_painel()
        titulos = [c.titulo for c in resposta.context["compromissos_dashboard"]]
        self.assertNotIn("Participante Pendente", titulos)
        self.assertNotIn("Totalmente Alheio", titulos)

    def test_resumo_compromissos_proximos_conta_so_pessoal(self):
        resposta = self._get_painel()
        self.assertEqual(resposta.context["resumo"]["compromissos_proximos"], 2)

    def test_proprio_com_multiplos_participantes_nao_duplica(self):
        """
        Regressão: `_compromissos_confirmados` faz LEFT JOIN com
        `participacoes` para checar `Q(responsavel=...) | Q(participacoes__...)`;
        sem `.distinct()`, um compromisso próprio com N participantes
        convidados aparecia N vezes no bloco e inflava a contagem do resumo.
        """
        convidado_1 = self._user("dashboard_convidado_1")
        convidado_2 = self._user("dashboard_convidado_2")
        ParticipanteCompromisso.objects.create(
            compromisso=self.proprio, usuario=convidado_1
        )
        ParticipanteCompromisso.objects.create(
            compromisso=self.proprio, usuario=convidado_2
        )

        resposta = self._get_painel()
        titulos = [c.titulo for c in resposta.context["compromissos_dashboard"]]
        self.assertEqual(titulos.count("Compromisso Próprio"), 1)
        self.assertEqual(resposta.context["resumo"]["compromissos_proximos"], 2)


class TestBlocoPendentesDeConfirmacao(DashboardAgendaPessoalBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_agenda_pendentes"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("dashboard_pendentes")
        self.outro = self._user("dashboard_pendentes_outro")
        self._dar_acesso(self.usuario)
        self.client.force_login(self.usuario)

        self.pendente = self._compromisso(titulo="Convite Pendente", responsavel=self.outro)
        self.participacao_pendente = ParticipanteCompromisso.objects.create(
            compromisso=self.pendente,
            usuario=self.usuario,
            status=ParticipanteCompromisso.STATUS_PENDENTE,
        )

        confirmado = self._compromisso(titulo="Já Confirmado", responsavel=self.outro)
        ParticipanteCompromisso.objects.create(
            compromisso=confirmado,
            usuario=self.usuario,
            status=ParticipanteCompromisso.STATUS_CONFIRMADO,
        )

    def test_bloco_pendentes_lista_so_participacoes_pendentes_do_usuario(self):
        resposta = self._get_painel()
        pendentes = resposta.context["compromissos_pendentes_dashboard"]
        titulos = [p.compromisso.titulo for p in pendentes]
        self.assertIn("Convite Pendente", titulos)
        self.assertNotIn("Já Confirmado", titulos)

    def test_confirmar_via_dashboard_redireciona_para_o_painel(self):
        r = self.client.post(
            f"/agenda/{self.pendente.pk}/confirmar-presenca/",
            {"next": "/"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        self.participacao_pendente.refresh_from_db()
        self.assertEqual(
            self.participacao_pendente.status, ParticipanteCompromisso.STATUS_CONFIRMADO
        )
