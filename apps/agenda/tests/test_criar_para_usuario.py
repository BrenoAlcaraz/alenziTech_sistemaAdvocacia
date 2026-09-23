"""
Testes do botão "+ Novo compromisso nesta agenda" da sub-aba "Agenda
de outros usuários" (`?para_usuario=` em `agenda:novo`): campo
Responsável nasce travado no colega selecionado e a mutação continua
exigindo `agenda_criar_para_outros` — nenhuma autorização nova, só
reaproveita a checagem já existente em `form_compromisso`.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_AGENDA_ATRIBUIR_OUTROS,
    MODULO_AGENDA,
    NIVEL_TODOS,
)
from apps.agenda.models import ItemAgenda


class AgendaCriarParaUsuarioBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _autorizar_agenda(self, user, *, criar_para_outros=False):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_TODOS
        )
        if criar_para_outros:
            HabilitacaoPapel.objects.create(
                papel=papel,
                modulo=MODULO_AGENDA,
                item=HAB_AGENDA_ATRIBUIR_OUTROS,
                ativo=True,
            )
        return papel


class TestFormularioTravadoParaUsuario(AgendaCriarParaUsuarioBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_criar_para_usuario"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Criar Para Usuario"
        tenant.slug = "agenda-criar-para-usuario"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_para_usuario")
        self._autorizar_agenda(self.gestor, criar_para_outros=True)
        self.colega = self._user("colega_para_usuario")
        self.client.force_login(self.gestor)

    def test_get_com_para_usuario_trava_campo_responsavel(self):
        r = self.client.get(
            "/agenda/novo/", {"para_usuario": self.colega.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].fields["responsavel"].disabled)
        self.assertEqual(r.context["usuario_travado"], self.colega)

    def test_post_ignora_responsavel_adulterado_no_html(self):
        """
        O campo `responsavel` vem `disabled` no HTML — o navegador nem
        envia valor para ele. Mesmo que o POST traga um valor diferente
        (adulteração), o Django ignora porque o campo é `disabled`: o
        compromisso é sempre criado para `usuario_travado`.
        """
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Compromisso Delegado",
                "tipo": "reuniao",
                "data_hora_inicio": "2026-09-20T10:00",
                "responsavel": self.gestor.pk,  # tentativa de adulteração
                "para_usuario": self.colega.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        compromisso = ItemAgenda.objects.get(titulo="Compromisso Delegado")
        self.assertEqual(compromisso.responsavel_id, self.colega.pk)
        self.assertEqual(compromisso.criado_por_id, self.gestor.pk)


class TestParaUsuarioExigeHabilitacao(AgendaCriarParaUsuarioBase):
    """
    Travar o campo no colega não contorna a autorização de mutação já
    existente: sem `agenda_criar_para_outros`, o envio ainda é negado.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "agenda_para_usuario_sem_habilitacao"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Para Usuario Sem Habilitacao"
        tenant.slug = "agenda-para-usuario-sem-habilitacao"

    def setUp(self):
        super().setUp()
        self.usuario = self._user("sem_habilitacao_para_usuario")
        self._autorizar_agenda(self.usuario, criar_para_outros=False)
        self.colega = self._user("colega_sem_habilitacao")
        self.client.force_login(self.usuario)

    def test_post_sem_habilitacao_retorna_403_e_nao_cria(self):
        antes = ItemAgenda.objects.count()
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Tentativa Sem Habilitação",
                "tipo": "reuniao",
                "data_hora_inicio": "2026-09-20T10:00",
                "para_usuario": self.colega.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(ItemAgenda.objects.count(), antes)
