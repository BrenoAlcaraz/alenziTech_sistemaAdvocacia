"""
Atalho "Habilitar em processos" do Painel do gestor —
specs/dashboard-painel-do-gestor.md.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import HAB_GERIR_HABILITAR_USUARIO_PROCESSOS, MODULO_GERIR
from apps.atividade.models import LogAtividade
from apps.processos.models import Processo


class UsuarioProcessosHabilitadosBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_configuracoes_usuario_processos_hab"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.responsavel = User.objects.create_user("resp_proc_hab", password="testpass")
        self.usuario_alvo = User.objects.create_user("alvo_proc_hab", password="testpass")
        self.processo = Processo.objects.create(
            titulo="Processo Habilitável", criado_por=self.responsavel, area_direito="CÍVEL",
        )
        self.gestor = User.objects.create_user("gestor_proc_hab", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Gestor Proc Hab")
        UsuarioPapel.objects.create(usuario=self.gestor, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        HabilitacaoPapel.objects.create(
            papel=papel, modulo=MODULO_GERIR,
            item=HAB_GERIR_HABILITAR_USUARIO_PROCESSOS, ativo=True,
        )
        self.client.force_login(self.gestor)

    def _url(self):
        return f"/configuracoes/usuarios/{self.usuario_alvo.pk}/processos/"


class TestUsuarioProcessosHabilitadosAutorizacao(UsuarioProcessosHabilitadosBase):
    def test_sem_habilitacao_nega(self):
        outro = User.objects.create_user("sem_hab_proc", password="testpass")
        self.client.force_login(outro)
        resposta = self.client.get(self._url(), HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 403)


class TestUsuarioProcessosHabilitadosToggle(UsuarioProcessosHabilitadosBase):
    def test_habilitar_e_remover_gera_log_e_persiste(self):
        resposta = self.client.post(
            self._url(), {"processo_id": self.processo.pk}, HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(self.usuario_alvo, self.processo.integrantes_habilitados.all())
        self.assertEqual(
            LogAtividade.objects.filter(tipo="processo_integrante_adicionado").count(), 1
        )

        resposta = self.client.post(
            self._url(),
            {"processo_id": self.processo.pk, "acao": "remover"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertNotIn(self.usuario_alvo, self.processo.integrantes_habilitados.all())
        self.assertEqual(
            LogAtividade.objects.filter(tipo="processo_integrante_removido").count(), 1
        )

    def test_filtro_por_materia(self):
        outro_processo = Processo.objects.create(
            titulo="Processo Trabalhista", criado_por=self.responsavel, area_direito="TRABALHISTA",
        )
        resposta = self.client.get(self._url(), {"materia": "CÍVEL"}, HTTP_HOST=self.http_host)
        titulos = [p.titulo for p in resposta.context["processos"]]
        self.assertIn(self.processo.titulo, titulos)
        self.assertNotIn(outro_processo.titulo, titulos)
