"""
Laboratório Jurídico como aba de Processos (`processos:lista?aba=laboratorio`).

Mantém o gate de duas camadas que antes vivia em `/laboratorio/`:
módulo `processos` autorizado + habilitação `processos_usar_laboratorio`.
A rota antiga só redireciona para a aba.

Fixtures no mesmo padrão de apps/processos/tests/test_autorizacao.py.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_PROCESSOS_USAR_LABORATORIO,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)

URL_ABA = "/processos/?aba=laboratorio"
TEXTO_LABORATORIO = "Gerar peça com IA"
TEXTO_ABA = "?aba=laboratorio"


class LaboratorioAbaBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _get(self, url):
        return self.client.get(url, HTTP_HOST=self.http_host)

    def _user_com_processos(self, username, *, habilitado):
        user = User.objects.create_user(username=username, password="testpass")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_PROCESSOS, nivel=NIVEL_TODOS, ativo=True
        )
        if habilitado:
            HabilitacaoPapel.objects.create(
                papel=papel, modulo=MODULO_PROCESSOS,
                item=HAB_PROCESSOS_USAR_LABORATORIO, ativo=True,
            )
        return user


class TestLaboratorioAbaModuloNegado(LaboratorioAbaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "lab_aba_modulo_negado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "lab_aba_modulo_negado"
        tenant.slug = "lab-aba-modulo-negado"

    def test_aba_negada_sem_modulo(self):
        user = User.objects.create_user(username="sem_modulo", password="x")
        self.client.force_login(user)
        self.assertEqual(self._get(URL_ABA).status_code, 403)


class TestLaboratorioAbaSemHabilitacao(LaboratorioAbaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "lab_aba_sem_habilitacao"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "lab_aba_sem_habilitacao"
        tenant.slug = "lab-aba-sem-habilitacao"

    def setUp(self):
        super().setUp()
        self.client.force_login(
            self._user_com_processos("sem_hab_lab", habilitado=False)
        )

    def test_aba_negada(self):
        self.assertEqual(self._get(URL_ABA).status_code, 403)

    def test_lista_nao_mostra_aba(self):
        r = self._get("/processos/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, TEXTO_ABA)


class TestLaboratorioAbaAutorizado(LaboratorioAbaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "lab_aba_autorizado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "lab_aba_autorizado"
        tenant.slug = "lab-aba-autorizado"

    def setUp(self):
        super().setUp()
        self.client.force_login(
            self._user_com_processos("com_hab_lab", habilitado=True)
        )

    def test_aba_renderiza_laboratorio(self):
        r = self._get(URL_ABA)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "processos/_laboratorio.html")
        self.assertContains(r, TEXTO_LABORATORIO)

    def test_lista_mostra_aba(self):
        r = self._get("/processos/")
        self.assertContains(r, TEXTO_ABA)
        self.assertNotContains(r, TEXTO_LABORATORIO)

    def test_rota_antiga_redireciona_para_aba(self):
        r = self._get("/laboratorio/")
        self.assertRedirects(r, URL_ABA, fetch_redirect_response=False)


class TestLaboratorioAbaAdministrador(LaboratorioAbaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "lab_aba_admin"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "lab_aba_admin"
        tenant.slug = "lab-aba-admin"

    def test_admin_acessa_aba(self):
        admin = User.objects.create_user(username="admin_lab", password="x")
        PerfilUsuario.objects.filter(user=admin).update(is_admin_escritorio=True)
        self.client.force_login(admin)
        r = self._get(URL_ABA)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, TEXTO_LABORATORIO)
