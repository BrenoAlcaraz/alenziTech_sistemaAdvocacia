"""
Atalho "Ir para Agenda" do Painel do gestor: ?usuario= só filtra de
fato para quem tem `gerir`/Admin — specs/dashboard-painel-do-gestor.md.
"""

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, MODULO_GERIR, NIVEL_TODOS
from apps.agenda.models import Compromisso


class TestUsuarioFiltroAgenda(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_agenda_usuario_filtro"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

        self.alvo = User.objects.create_user("alvo_agenda", password="testpass")
        self.compromisso_alvo = Compromisso.objects.create(
            titulo="Compromisso do alvo",
            responsavel=self.alvo,
            data_hora_inicio=timezone.now(),
        )

    def _autorizar_agenda(self, user, *, gerir=False):
        papel = PapelAcesso.objects.create(nome=f"Papel Agenda {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_TODOS
        )
        if gerir:
            PermissaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
            )

    def test_usuario_sem_gerir_tem_parametro_ignorado(self):
        comum = User.objects.create_user("comum_agenda", password="testpass")
        self._autorizar_agenda(comum)
        self.client.force_login(comum)

        resposta = self.client.get(
            "/agenda/", {"usuario": self.alvo.pk, "filtro": "todos"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNone(resposta.context["usuario_filtro"])

    def test_usuario_com_gerir_filtra_de_fato(self):
        gestor = User.objects.create_user("gestor_agenda", password="testpass")
        self._autorizar_agenda(gestor, gerir=True)
        self.client.force_login(gestor)

        resposta = self.client.get(
            "/agenda/", {"usuario": self.alvo.pk, "filtro": "todos"}, HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["usuario_filtro"], self.alvo)
        self.assertIn(self.compromisso_alvo, resposta.context["compromissos"])
