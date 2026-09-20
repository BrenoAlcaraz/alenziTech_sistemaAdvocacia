"""
Aba "Painel do gestor" — lista de usuários + timeline de atividade do
dia — specs/dashboard-painel-do-gestor.md.
"""

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_GERIR, MODULO_PAINEL, NIVEL_TODOS
from apps.atividade.models import LogAtividade


class PainelGestorBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_gestor"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _conceder_painel(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel Painel {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PAINEL, ativo=True, nivel=NIVEL_TODOS
        )
        return papel


class TestPainelGestorAutorizacao(PainelGestorBase):
    def test_usuario_comum_nao_acessa_lista(self):
        comum = User.objects.create_user("comum_gestor", password="testpass")
        self._conceder_painel(comum)
        self.client.force_login(comum)

        resposta = self.client.get("/gestor/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 403)

    def test_com_modulo_gerir_acessa_lista(self):
        gestor = User.objects.create_user("com_gerir", password="testpass")
        papel = self._conceder_painel(gestor)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        self.client.force_login(gestor)

        resposta = self.client.get("/gestor/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)

    def test_admin_acessa_lista_sem_papel_gerir(self):
        admin = User.objects.create_user("admin_gestor", password="testpass")
        PerfilUsuario.objects.filter(user=admin).update(is_admin_escritorio=True)
        self.client.force_login(admin)

        resposta = self.client.get("/gestor/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)

    def test_aba_painel_do_gestor_some_do_menu_para_usuario_comum(self):
        comum = User.objects.create_user("sem_tab_gestor", password="testpass")
        self._conceder_painel(comum)
        self.client.force_login(comum)

        resposta = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertNotContains(resposta, "Painel do gestor")


class TestPainelGestorListaEDetalhe(PainelGestorBase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user("admin_lista_gestor", password="testpass")
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.client.force_login(self.admin)

        self.membro = User.objects.create_user("membro_equipe_gestor", password="testpass")
        agora = timezone.now()
        LogAtividade.objects.create(usuario=self.membro, tipo="login", descricao="Login no sistema")
        LogAtividade.objects.create(
            usuario=self.membro, tipo="processo_criado", descricao="Criou o processo X"
        )
        # Log de ontem não deve contar como "hoje".
        log_antigo = LogAtividade.objects.create(
            usuario=self.membro, tipo="login", descricao="Login de ontem"
        )
        LogAtividade.objects.filter(pk=log_antigo.pk).update(criado_em=agora - timezone.timedelta(days=1))

    def test_lista_mostra_contagem_de_hoje(self):
        resposta = self.client.get("/gestor/", HTTP_HOST=self.http_host)
        contexto = {c["usuario"].pk: c["acoes_hoje"] for c in resposta.context["usuarios_contexto"]}
        self.assertEqual(contexto[self.membro.pk], 2)

    def test_detalhe_mostra_timeline_do_dia_em_ordem(self):
        resposta = self.client.get(f"/gestor/{self.membro.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        descricoes = [a.descricao for a in resposta.context["atividades"]]
        self.assertEqual(descricoes, ["Login no sistema", "Criou o processo X"])
        self.assertNotIn("Login de ontem", descricoes)

    def test_detalhe_nao_oferece_atalho_separado_para_habilitacoes(self):
        # Habilitações fazem parte de "Permissões" (`usuario_overrides`).
        resposta = self.client.get(f"/gestor/{self.membro.pk}/", HTTP_HOST=self.http_host)
        html = resposta.content.decode()
        self.assertNotIn("Ir para Habilitações", html)
        self.assertIn("Ir para Permissões", html)
