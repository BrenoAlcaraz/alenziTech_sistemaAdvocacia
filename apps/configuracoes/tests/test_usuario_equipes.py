"""
Atalho "Grupos" do Painel do gestor — specs/dashboard-painel-do-gestor.md.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Equipe, MembroEquipe, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import HAB_GERIR_CRIAR_EQUIPE, MODULO_GERIR


class UsuarioEquipesBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_configuracoes_usuario_equipes"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario_alvo = User.objects.create_user("alvo_equipes", password="testpass")
        self.equipe = Equipe.objects.create(nome="Equipe Cível", ativo=True)

    def _conceder_gerir_equipes(self, user):
        from apps.accounts.models import HabilitacaoPapel

        papel = PapelAcesso.objects.create(nome=f"Papel Equipes {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        HabilitacaoPapel.objects.create(
            papel=papel, modulo=MODULO_GERIR,
            item=HAB_GERIR_CRIAR_EQUIPE, ativo=True,
        )

    def _url(self):
        return f"/configuracoes/usuarios/{self.usuario_alvo.pk}/equipes/"


class TestUsuarioEquipesAutorizacao(UsuarioEquipesBase):
    def test_sem_habilitacao_nega(self):
        gestor = User.objects.create_user("sem_gerir", password="testpass")
        self.client.force_login(gestor)
        resposta = self.client.get(self._url(), HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 403)


class TestUsuarioEquipesToggle(UsuarioEquipesBase):
    def setUp(self):
        super().setUp()
        self.gestor = User.objects.create_user("gestor_equipes", password="testpass")
        self._conceder_gerir_equipes(self.gestor)
        self.client.force_login(self.gestor)

    def test_adicionar_e_remover_membro(self):
        resposta = self.client.post(
            self._url(), {"equipe_id": self.equipe.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(
            MembroEquipe.objects.filter(
                usuario=self.usuario_alvo, equipe=self.equipe, ativo=True
            ).exists()
        )

        resposta = self.client.post(
            self._url(),
            {"equipe_id": self.equipe.pk, "acao": "remover"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(
            MembroEquipe.objects.filter(usuario=self.usuario_alvo, equipe=self.equipe).exists()
        )

    def test_lista_mostra_equipe_como_nao_membro_por_padrao(self):
        resposta = self.client.get(self._url(), HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        contexto = {c["equipe"].pk: c["membro"] for c in resposta.context["equipes_contexto"]}
        self.assertFalse(contexto[self.equipe.pk])
