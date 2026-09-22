"""
Convite de delegação em Agenda (specs/delegacao-por-convite-agenda-
tarefas.md, issue #30): delegar o responsável de um Compromisso para
outro usuário passa a exigir convite, exceto Administrador->qualquer
um e gerente->subordinado não-gerente da própria Equipe (issue #28,
apps/accounts/delegacao.py). Não confundir com a confirmação de
presença de participante (PDR-0020), que não muda.

Segue o mesmo padrão de fixtures de
apps/agenda/tests/test_criar_para_usuario.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    ConviteDelegacao,
    Equipe,
    HabilitacaoPapel,
    MembroEquipe,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import HAB_AGENDA_CRIAR_PARA_OUTROS, MODULO_AGENDA, NIVEL_SOMENTE_SEUS, NIVEL_TODOS
from apps.agenda.models import Compromisso


class AgendaConviteBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _set_admin(self, user):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        user._state.fields_cache.pop("perfil", None)

    def _dar_acesso_modulo(self, user, *, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=nivel)
        return papel

    def _dar_acesso_com_criar_para_outros(self, user):
        papel = self._dar_acesso_modulo(user)
        HabilitacaoPapel.objects.create(
            papel=papel, modulo=MODULO_AGENDA, item=HAB_AGENDA_CRIAR_PARA_OUTROS, ativo=True
        )
        return papel

    def _payload(self, *, destinatario, titulo="Compromisso Convite"):
        return {
            "titulo": titulo,
            "tipo": "reuniao",
            "data_hora_inicio": "2026-10-01T10:00",
            "responsavel": destinatario.pk,
        }

    def _criar(self, *, destinatario, titulo="Compromisso Convite"):
        return self.client.post(
            "/agenda/novo/", self._payload(destinatario=destinatario, titulo=titulo), HTTP_HOST=self.http_host
        )


class TestCriacaoExigeConvite(AgendaConviteBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_convite_exige"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Convite Exige"
        tenant.slug = "agenda-convite-exige"

    def setUp(self):
        super().setUp()
        self.delegante = self._user("delegante_convite_agenda")
        self.destinatario = self._user("destinatario_convite_agenda")
        self._dar_acesso_com_criar_para_outros(self.delegante)
        self.client.force_login(self.delegante)

    def test_convite_pendente_e_criado_e_vinculado_ao_compromisso(self):
        self._criar(destinatario=self.destinatario)
        compromisso = Compromisso.objects.get(titulo="Compromisso Convite")
        self.assertIsNotNone(compromisso.convite_delegacao)
        self.assertEqual(compromisso.convite_delegacao.status, ConviteDelegacao.STATUS_PENDENTE)
        self.assertEqual(compromisso.convite_delegacao.delegante_id, self.delegante.pk)
        self.assertEqual(compromisso.convite_delegacao.destinatario_id, self.destinatario.pk)
        self.assertEqual(compromisso.responsavel_id, self.destinatario.pk)

    def test_compromisso_nao_aparece_nas_listas_ativas_do_destinatario(self):
        self._criar(destinatario=self.destinatario)
        self.client.logout()
        self._dar_acesso_modulo(self.destinatario, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.destinatario)

        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        titulos_novidades = [c.titulo for c in r.context["compromissos_novidades"]]
        titulos_terceiro = [c.titulo for c in r.context["compromissos_terceiro"]]
        titulos_lista = [c.titulo for c in r.context["compromissos"]]
        self.assertNotIn("Compromisso Convite", titulos_novidades)
        self.assertNotIn("Compromisso Convite", titulos_terceiro)
        self.assertNotIn("Compromisso Convite", titulos_lista)

    def test_compromisso_aparece_em_delegados_por_mim_com_status_pendente(self):
        self._criar(destinatario=self.destinatario)
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        titulos = [c.titulo for c in r.context["compromissos_delegados"]]
        self.assertIn("Compromisso Convite", titulos)
        self.assertContains(r, "Convite pendente")

    def test_convite_aparece_na_aba_convites_recebidos_do_destinatario(self):
        self._criar(destinatario=self.destinatario)
        self.client.logout()
        self._dar_acesso_modulo(self.destinatario, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.destinatario)
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        convites = r.context["convites_recebidos"]
        self.assertEqual(len(convites), 1)
        self.assertEqual(convites[0].item.titulo, "Compromisso Convite")

    def test_destinatario_nao_consegue_acessar_compromisso_pendente_diretamente(self):
        self._criar(destinatario=self.destinatario)
        compromisso = Compromisso.objects.get(titulo="Compromisso Convite")
        self.client.logout()
        self._dar_acesso_modulo(self.destinatario, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.destinatario)
        r = self.client.get(f"/agenda/{compromisso.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)


class TestResponderConvite(AgendaConviteBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_convite_responder"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Convite Responder"
        tenant.slug = "agenda-convite-responder"

    def setUp(self):
        super().setUp()
        self.delegante = self._user("delegante_responder_agenda")
        self.destinatario = self._user("destinatario_responder_agenda")
        self.terceiro = self._user("terceiro_responder_agenda")
        self._dar_acesso_com_criar_para_outros(self.delegante)
        self._dar_acesso_modulo(self.destinatario, nivel=NIVEL_SOMENTE_SEUS)
        self._dar_acesso_modulo(self.terceiro, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.delegante)
        self._criar(destinatario=self.destinatario)
        self.compromisso = Compromisso.objects.get(titulo="Compromisso Convite")
        self.client.logout()

    def test_destinatario_aceita_e_compromisso_passa_a_aparecer(self):
        self.client.force_login(self.destinatario)
        r = self.client.post(
            f"/agenda/convites/{self.compromisso.convite_delegacao_id}/responder/",
            {"acao": "aceitar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.compromisso.convite_delegacao.refresh_from_db()
        self.assertEqual(self.compromisso.convite_delegacao.status, ConviteDelegacao.STATUS_ACEITO)

        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        titulos = [c.titulo for c in r.context["compromissos_novidades"]]
        self.assertIn("Compromisso Convite", titulos)

    def test_destinatario_recusa_com_justificativa(self):
        self.client.force_login(self.destinatario)
        r = self.client.post(
            f"/agenda/convites/{self.compromisso.convite_delegacao_id}/responder/",
            {"acao": "recusar", "justificativa": "Já tenho compromisso nesse horário."},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.compromisso.convite_delegacao.refresh_from_db()
        self.assertEqual(self.compromisso.convite_delegacao.status, ConviteDelegacao.STATUS_RECUSADO)
        self.assertEqual(
            self.compromisso.convite_delegacao.justificativa_recusa, "Já tenho compromisso nesse horário."
        )

    def test_terceiro_nao_pode_responder_convite_alheio(self):
        self.client.force_login(self.terceiro)
        r = self.client.post(
            f"/agenda/convites/{self.compromisso.convite_delegacao_id}/responder/",
            {"acao": "aceitar"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)
        self.compromisso.convite_delegacao.refresh_from_db()
        self.assertEqual(self.compromisso.convite_delegacao.status, ConviteDelegacao.STATUS_PENDENTE)


class TestDelegacaoDireta(AgendaConviteBase):
    """Administrador e gerente->subordinado da própria Equipe: compromisso
    ativo desde a criação, sem convite."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_convite_direta"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Convite Direta"
        tenant.slug = "agenda-convite-direta"

    def setUp(self):
        super().setUp()
        self.admin = self._user("admin_direta_agenda")
        self._set_admin(self.admin)
        self.destinatario = self._user("destinatario_direta_agenda")

        self.gerente = self._user("gerente_direta_agenda")
        self._dar_acesso_com_criar_para_outros(self.gerente)
        self.subordinado = self._user("subordinado_direta_agenda")
        equipe = Equipe.objects.create(nome="Equipe Direta Agenda")
        MembroEquipe.objects.create(usuario=self.gerente, equipe=equipe, eh_gerente=True, ativo=True)
        MembroEquipe.objects.create(usuario=self.subordinado, equipe=equipe, eh_gerente=False, ativo=True)

    def test_admin_delega_direto_sem_convite(self):
        self.client.force_login(self.admin)
        self._criar(destinatario=self.destinatario)
        compromisso = Compromisso.objects.get(titulo="Compromisso Convite")
        self.assertIsNone(compromisso.convite_delegacao)

    def test_gerente_delega_direto_para_subordinado_da_propria_equipe(self):
        self.client.force_login(self.gerente)
        self._criar(destinatario=self.subordinado)
        compromisso = Compromisso.objects.get(titulo="Compromisso Convite")
        self.assertIsNone(compromisso.convite_delegacao)

    def test_auto_atribuicao_nunca_gera_convite(self):
        comum = self._user("comum_auto_atribuicao_agenda")
        self._dar_acesso_com_criar_para_outros(comum)
        self.client.force_login(comum)
        self._criar(destinatario=comum, titulo="Compromisso Para Mim Mesmo")
        compromisso = Compromisso.objects.get(titulo="Compromisso Para Mim Mesmo")
        self.assertIsNone(compromisso.convite_delegacao)
