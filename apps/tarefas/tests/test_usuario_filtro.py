"""
Atalho "Ir para Tarefas" do Painel do gestor: ?usuario= só filtra de
fato para quem tem `gerir`/Admin — specs/dashboard-painel-do-gestor.md.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_GERIR, MODULO_TAREFAS, NIVEL_TODOS


class TestUsuarioFiltroTarefas(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_tarefas_usuario_filtro"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Usuário Filtro Tarefas"
        tenant.slug = "wi-tarefas-usuario-filtro"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        from apps.tarefas.models import Tarefa

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

        self.alvo = User.objects.create_user("alvo_tarefas", password="testpass")
        self.tarefa_alvo = Tarefa.objects.create(
            titulo="Tarefa do alvo", criador=self.alvo, atribuidor=self.alvo,
            responsavel=self.alvo, status="a_fazer",
        )

    def _autorizar_tarefas(self, user, *, gerir=False):
        papel = PapelAcesso.objects.create(nome=f"Papel Tarefas {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_TAREFAS, ativo=True, nivel=NIVEL_TODOS
        )
        if gerir:
            PermissaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
            )

    def test_usuario_sem_gerir_tem_parametro_ignorado(self):
        comum = User.objects.create_user("comum_tarefas", password="testpass")
        self._autorizar_tarefas(comum)
        self.client.force_login(comum)

        resposta = self.client.get(
            "/tarefas/", {"usuario": self.alvo.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNone(resposta.context["usuario_filtro"])

    def test_usuario_com_gerir_filtra_de_fato(self):
        gestor = User.objects.create_user("gestor_tarefas", password="testpass")
        self._autorizar_tarefas(gestor, gerir=True)
        self.client.force_login(gestor)

        resposta = self.client.get(
            "/tarefas/", {"usuario": self.alvo.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context["usuario_filtro"], self.alvo)
        todas = [
            t for grupo in resposta.context["tarefas_por_status"].values() for t in grupo
        ]
        self.assertIn(self.tarefa_alvo, todas)
