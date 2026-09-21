"""
Testes da unificação de lista/calendário numa só página (spec
`agenda-calendario-lista-unificados.md`): as duas visões nascem no
mesmo request (alternância é só client-side, `data-view-toggle`), sem
perder filtro/data selecionada ao trocar de visão.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_TODOS
from apps.agenda.models import Compromisso


class TestIndexUnificado(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_index_unificado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Index Unificado"
        tenant.slug = "agenda-index-unificado"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

        self.user = User.objects.create_user(username="usuario_unificado", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Unificado", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_TODOS
        )
        self.client.force_login(self.user)

        Compromisso.objects.create(
            titulo="Compromisso do Dia",
            responsavel=self.user,
            data_hora_inicio="2026-09-10T10:00:00Z",
        )

    def test_index_padrao_traz_lista_e_calendario_no_mesmo_request(self):
        r = self.client.get("/agenda/?filtro=todos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "agenda/index.html")
        self.assertIn("compromissos", r.context)
        self.assertIn("cal_dias", r.context)

    def test_visao_calendario_usa_mesmo_template_e_traz_lista_tambem(self):
        r = self.client.get("/agenda/?visao=calendario", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "agenda/index.html")
        self.assertIn("compromissos", r.context)
        self.assertIn("cal_dias", r.context)

    def test_toggle_client_side_presente_no_html(self):
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertContains(r, 'data-view-toggle="lista"')
        self.assertContains(r, 'data-view-toggle="calendario"')
        self.assertContains(r, 'data-view="lista"')
        self.assertContains(r, 'data-view="calendario"')
