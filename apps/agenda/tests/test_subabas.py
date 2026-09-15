"""
Testes da faixa de sub-abas da Agenda (spec
`agenda-calendario-lista-unificados.md`): "Novos na sua agenda
(últimas 24h)"/"Adicionado por terceiro" sempre visíveis; "Delegados
por mim"/"Agenda de outros usuários" condicionadas às habilitações já
aprovadas hoje (Permissão "Agenda"/"Todos" + Gerir para a última,
`agenda_criar_para_outros` para a penúltima) — nenhuma habilitação
nova.

Segue o mesmo padrão de fixtures de apps/agenda/tests/test_escopo.py
sobre django_tenants.test.cases.TenantTestCase.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_AGENDA_CRIAR_PARA_OUTROS,
    MODULO_AGENDA,
    MODULO_GERIR,
    NIVEL_TODOS,
)
from apps.agenda.models import Compromisso


class AgendaSubabasBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _set_admin(self, user, value=True):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=value)

    def _new_papel(self, nome):
        return PapelAcesso.objects.create(nome=nome, ativo=True)

    def _assign_papel(self, user, papel):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)

    def _pp(self, papel, modulo, *, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=True, nivel=nivel
        )

    def _hp(self, papel, modulo, item):
        return HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, item=item, ativo=True
        )

    def _dar_acesso_agenda(self, user, *, nivel=NIVEL_TODOS):
        papel = self._new_papel(f"Papel Agenda {user.username}")
        self._assign_papel(user, papel)
        self._pp(papel, MODULO_AGENDA, nivel=nivel)
        return papel

    def _compromisso(self, *, responsavel, criado_por=None, **kwargs):
        defaults = {
            "titulo": "Compromisso Teste",
            "data_hora_inicio": timezone.now(),
        }
        defaults.update(kwargs)
        return Compromisso.objects.create(
            responsavel=responsavel, criado_por=criado_por, **defaults
        )


class TestSubabaNovidades(AgendaSubabasBase):
    """"Novos na sua agenda (últimas 24h)" — sempre visível, qualquer origem."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_subaba_novidades"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Subaba Novidades"
        tenant.slug = "agenda-subaba-novidades"

    def setUp(self):
        super().setUp()
        self.user = self._user("usuario_novidades")
        self._dar_acesso_agenda(self.user)
        self.client.force_login(self.user)

    def test_compromisso_recente_como_responsavel_aparece(self):
        recente = self._compromisso(
            titulo="Recente", responsavel=self.user, criado_por=self.user
        )
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertIn(recente, r.context["compromissos_novidades"])

    def test_compromisso_antigo_nao_aparece(self):
        antigo = self._compromisso(
            titulo="Antigo", responsavel=self.user, criado_por=self.user
        )
        Compromisso.objects.filter(pk=antigo.pk).update(
            criado_em=timezone.now() - timedelta(hours=30)
        )
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertNotIn(antigo, r.context["compromissos_novidades"])

    def test_compromisso_cancelado_nao_aparece(self):
        cancelado = self._compromisso(
            titulo="Cancelado", responsavel=self.user, criado_por=self.user,
            status="cancelado",
        )
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertNotIn(cancelado, r.context["compromissos_novidades"])


class TestSubabaAdicionadoPorTerceiro(AgendaSubabasBase):
    """"Adicionado por terceiro" — sempre visível, só quando o criador é outra pessoa."""

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_subaba_terceiro"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Subaba Terceiro"
        tenant.slug = "agenda-subaba-terceiro"

    def setUp(self):
        super().setUp()
        self.user = self._user("usuario_terceiro")
        self.colega = self._user("colega_terceiro")
        self._dar_acesso_agenda(self.user)
        self.client.force_login(self.user)

    def test_criado_por_outro_aparece(self):
        c = self._compromisso(
            titulo="De Terceiro", responsavel=self.user, criado_por=self.colega
        )
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertIn(c, r.context["compromissos_terceiro"])

    def test_criado_pelo_proprio_usuario_nao_aparece(self):
        c = self._compromisso(
            titulo="Próprio", responsavel=self.user, criado_por=self.user
        )
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertNotIn(c, r.context["compromissos_terceiro"])

    def test_sem_criado_por_registrado_nao_aparece(self):
        c = self._compromisso(titulo="Legado", responsavel=self.user, criado_por=None)
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertNotIn(c, r.context["compromissos_terceiro"])


class TestSubabaDelegadosPorMim(AgendaSubabasBase):
    """
    "Delegados por mim" — só para quem tem `agenda_criar_para_outros`;
    mostra qualquer status, inclusive cancelado.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_subaba_delegados"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Subaba Delegados"
        tenant.slug = "agenda-subaba-delegados"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_delegados")
        self.colega = self._user("colega_delegados")
        self.comum = self._user("comum_delegados")

        papel_gestor = self._dar_acesso_agenda(self.gestor)
        self._hp(papel_gestor, MODULO_AGENDA, HAB_AGENDA_CRIAR_PARA_OUTROS)

        self._dar_acesso_agenda(self.comum)

    def test_aba_nao_aparece_para_quem_nao_pode_delegar(self):
        self.client.force_login(self.comum)
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertNotIn("compromissos_delegados", r.context)
        self.assertNotContains(r, "Delegados por mim")

    def test_aba_mostra_compromisso_delegado_mesmo_cancelado(self):
        self.client.force_login(self.gestor)
        delegado = self._compromisso(
            titulo="Delegado Cancelado",
            responsavel=self.colega,
            criado_por=self.gestor,
            status="cancelado",
        )
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertIn(delegado, r.context["compromissos_delegados"])

    def test_aba_nao_mostra_compromisso_proprio(self):
        self.client.force_login(self.gestor)
        proprio = self._compromisso(
            titulo="Próprio do Gestor", responsavel=self.gestor, criado_por=self.gestor
        )
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertNotIn(proprio, r.context["compromissos_delegados"])


class TestSubabaAgendaDeOutrosUsuarios(AgendaSubabasBase):
    """
    "Agenda de outros usuários" — só para quem tem `gerir`/Admin
    (mesma condição já usada pelo atalho `?usuario=` do Painel do
    gestor); reutiliza o próprio parâmetro `?usuario=` já existente.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_subaba_outros"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Subaba Outros"
        tenant.slug = "agenda-subaba-outros"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_outros")
        self.comum = self._user("comum_outros")
        self.colega = self._user("colega_outros")

        papel_gestor = self._dar_acesso_agenda(self.gestor)
        self._pp(papel_gestor, MODULO_GERIR, nivel="")

        self._dar_acesso_agenda(self.comum)

    def test_aba_nao_aparece_para_usuario_comum(self):
        self.client.force_login(self.comum)
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertNotIn("usuarios_outros", r.context)
        self.assertNotContains(r, "Agenda de outros usuários")

    def test_aba_aparece_para_gestor_com_picker(self):
        self.client.force_login(self.gestor)
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertIn("usuarios_outros", r.context)
        self.assertContains(r, "Agenda de outros usuários")

    def test_selecionar_usuario_ativa_aba_outros_automaticamente(self):
        self.client.force_login(self.gestor)
        r = self.client.get(
            "/agenda/", {"usuario": self.colega.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.context["aba_ativa"], "outros")
        self.assertEqual(r.context["usuario_filtro"], self.colega)
