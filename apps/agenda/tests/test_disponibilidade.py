"""
Testes do endpoint `agenda:disponibilidade_convidado` — verificação de
disponibilidade de convidado ao adicionar participante (spec
`agenda-calendario-lista-unificados.md`): mesma condição de
habilitação da sub-aba "Agenda de outros usuários" (`gerir`/Admin),
nunca impede a criação do compromisso, só informa conflito de
horário.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, MODULO_GERIR, NIVEL_TODOS
from apps.agenda.models import ItemAgenda


class AgendaDisponibilidadeBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _autorizar_agenda(self, user, *, gerir=False):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_TODOS
        )
        if gerir:
            PermissaoPapel.objects.create(
                papel=papel, modulo=MODULO_GERIR, ativo=True, nivel=""
            )


class TestDisponibilidadeAutorizacao(AgendaDisponibilidadeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_disponibilidade_autorizacao"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Disponibilidade Autorizacao"
        tenant.slug = "agenda-disponibilidade-autorizacao"

    def setUp(self):
        super().setUp()
        self.convidado = self._user("convidado")

    def test_sem_gerir_retorna_403(self):
        comum = self._user("comum_disp")
        self._autorizar_agenda(comum)
        self.client.force_login(comum)
        r = self.client.get(
            "/agenda/disponibilidade/",
            {"usuario": self.convidado.pk, "inicio": "2026-09-20T10:00:00"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)

    def test_sem_modulo_agenda_retorna_403(self):
        sem_modulo = self._user("sem_modulo_disp")
        self.client.force_login(sem_modulo)
        r = self.client.get(
            "/agenda/disponibilidade/",
            {"usuario": self.convidado.pk, "inicio": "2026-09-20T10:00:00"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)


class TestDisponibilidadeConflito(AgendaDisponibilidadeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_disponibilidade_conflito"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Disponibilidade Conflito"
        tenant.slug = "agenda-disponibilidade-conflito"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_disp")
        self._autorizar_agenda(self.gestor, gerir=True)
        self.client.force_login(self.gestor)
        self.convidado = self._user("convidado_disp")

    def test_sem_conflito_retorna_lista_vazia(self):
        r = self.client.get(
            "/agenda/disponibilidade/",
            {"usuario": self.convidado.pk, "inicio": "2026-09-20T10:00:00Z"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["compromissos"], [])

    def test_com_conflito_retorna_compromisso_existente(self):
        ItemAgenda.objects.create(tipo="reuniao", 
            titulo="Audiência do convidado",
            responsavel=self.convidado,
            data_hora_inicio="2026-09-20T10:00:00Z",
            data_hora_fim="2026-09-20T11:00:00Z",
        )
        r = self.client.get(
            "/agenda/disponibilidade/",
            {"usuario": self.convidado.pk, "inicio": "2026-09-20T10:30:00Z"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        titulos = [c["titulo"] for c in r.json()["compromissos"]]
        self.assertIn("Audiência do convidado", titulos)

    def test_nao_impede_criacao_do_compromisso(self):
        """Critério de aceite: disponibilidade é informativa, nunca bloqueia."""
        ItemAgenda.objects.create(tipo="reuniao", 
            titulo="Já ocupado",
            responsavel=self.convidado,
            data_hora_inicio="2026-09-20T10:00:00Z",
        )
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Novo Compromisso",
                "tipo": "reuniao",
                "data_hora_inicio": "2026-09-20T10:00",
                "responsavel": self.gestor.pk,
                "participantes": [self.convidado.pk],
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(ItemAgenda.objects.filter(titulo="Novo Compromisso").exists())

    def test_horario_diferente_nao_gera_conflito(self):
        ItemAgenda.objects.create(tipo="reuniao", 
            titulo="Manhã",
            responsavel=self.convidado,
            data_hora_inicio="2026-09-20T08:00:00Z",
            data_hora_fim="2026-09-20T09:00:00Z",
        )
        r = self.client.get(
            "/agenda/disponibilidade/",
            {"usuario": self.convidado.pk, "inicio": "2026-09-20T14:00:00Z"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.json()["compromissos"], [])
