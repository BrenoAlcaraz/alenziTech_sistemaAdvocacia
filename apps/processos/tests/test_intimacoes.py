"""
Criação/vínculo manual de Intimação — specs/dashboard-intimacoes.md.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_PROCESSOS, NIVEL_TODOS
from apps.processos.models import Intimacao, Processo


class IntimacoesBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_processos_intimacoes"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("resp_intimacao", password="testpass")
        self._autorizar_processos(self.usuario)
        self.processo = Processo.objects.create(
            titulo="Processo Intimável", criado_por=self.usuario
        )
        self.client.force_login(self.usuario)

    def _autorizar_processos(self, user, *, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel Intimacao {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=nivel
        )


class TestCriarIntimacaoManual(IntimacoesBase):
    def test_cria_intimacao_vinculada_ao_processo_do_proprio_escopo(self):
        resposta = self.client.post(
            "/processos/intimacoes/nova/",
            {
                "processo": self.processo.pk,
                "motivo": "Réplica à contestação",
                "prazo_manifestacao": "2026-12-01",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        intimacao = Intimacao.objects.get()
        self.assertEqual(intimacao.processo_id, self.processo.pk)
        self.assertEqual(intimacao.status, "pendente")
        self.assertEqual(intimacao.origem, "manual")
        self.assertEqual(intimacao.criado_por, self.usuario)

    def test_nao_pode_vincular_processo_fora_do_escopo_de_mutacao(self):
        outro_responsavel = User.objects.create_user("outro_resp", password="testpass")
        processo_alheio = Processo.objects.create(
            titulo="Processo Alheio", criado_por=outro_responsavel
        )
        resposta = self.client.post(
            "/processos/intimacoes/nova/",
            {
                "processo": processo_alheio.pk,
                "motivo": "Tentativa indevida",
                "prazo_manifestacao": "2026-12-01",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 200)  # form inválido, re-renderiza
        self.assertFalse(Intimacao.objects.exists())

    def test_admin_pode_vincular_processo_de_outro_responsavel(self):
        admin = User.objects.create_user("admin_intimacao", password="testpass")
        PerfilUsuario.objects.filter(user=admin).update(is_admin_escritorio=True)
        self.client.force_login(admin)

        resposta = self.client.post(
            "/processos/intimacoes/nova/",
            {
                "processo": self.processo.pk,
                "motivo": "Intimação via admin",
                "prazo_manifestacao": "2026-12-01",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Intimacao.objects.filter(processo=self.processo).exists())


class TestManifestarIntimacao(IntimacoesBase):
    def setUp(self):
        super().setUp()
        self.intimacao = Intimacao.objects.create(
            processo=self.processo,
            motivo="Réplica à contestação",
            prazo_manifestacao="2026-12-01",
            criado_por=self.usuario,
        )

    def test_marcar_como_manifestada_muda_status(self):
        resposta = self.client.post(
            f"/processos/intimacoes/{self.intimacao.pk}/manifestar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 302)
        self.intimacao.refresh_from_db()
        self.assertEqual(self.intimacao.status, "manifestada")

    def test_nao_pode_manifestar_intimacao_de_processo_alheio(self):
        outro_responsavel = User.objects.create_user("outro_resp2", password="testpass")
        processo_alheio = Processo.objects.create(
            titulo="Processo Alheio 2", criado_por=outro_responsavel
        )
        intimacao_alheia = Intimacao.objects.create(
            processo=processo_alheio, motivo="Alheia", prazo_manifestacao="2026-12-01",
        )
        resposta = self.client.post(
            f"/processos/intimacoes/{intimacao_alheia.pk}/manifestar/", HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 404)
        intimacao_alheia.refresh_from_db()
        self.assertEqual(intimacao_alheia.status, "pendente")
