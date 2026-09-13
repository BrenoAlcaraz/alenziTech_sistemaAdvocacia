"""
Painel "Intimações" na Visão geral do Dashboard —
specs/dashboard-intimacoes.md.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_PAINEL,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.processos.models import Intimacao, Processo


class PainelIntimacoesBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_intimacoes"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("usuario_painel_intimacao", password="testpass")

    def _autorizar(self, *, nivel_processos=NIVEL_TODOS, painel=True):
        papel = PapelAcesso.objects.create(nome="Papel Intimacoes")
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PROCESSOS, ativo=True, nivel=nivel_processos
        )
        if painel:
            PermissaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=MODULO_PAINEL, ativo=True, nivel=NIVEL_TODOS
            )
        self.client.force_login(self.usuario)


class TestPainelIntimacoesSemAcessoProcessos(PainelIntimacoesBase):
    def test_painel_sem_processos_nao_mostra_intimacoes(self):
        papel = PapelAcesso.objects.create(nome="Papel Sem Processos")
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PAINEL, ativo=True, nivel=NIVEL_TODOS
        )
        self.client.force_login(self.usuario)

        resposta = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertIsNone(resposta.context["intimacoes"])
        self.assertNotContains(resposta, "Nenhuma intimação pendente.")


class TestPainelIntimacoesComAcesso(PainelIntimacoesBase):
    def setUp(self):
        super().setUp()
        self._autorizar()
        self.processo = Processo.objects.create(titulo="Processo com intimação", responsavel=self.usuario)
        self.pendente = Intimacao.objects.create(
            processo=self.processo, motivo="Réplica", prazo_manifestacao="2026-12-01",
        )
        self.manifestada = Intimacao.objects.create(
            processo=self.processo, motivo="Já respondida", prazo_manifestacao="2026-11-01",
            status="manifestada",
        )

    def test_mostra_so_pendentes(self):
        resposta = self.client.get("/", HTTP_HOST=self.http_host)
        intimacoes = list(resposta.context["intimacoes"])
        self.assertEqual(intimacoes, [self.pendente])

    def test_manifestar_remove_do_painel(self):
        self.client.post(
            f"/processos/intimacoes/{self.pendente.pk}/manifestar/", HTTP_HOST=self.http_host
        )
        resposta = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertEqual(list(resposta.context["intimacoes"]), [])


class TestPainelIntimacoesEscopo(PainelIntimacoesBase):
    def test_somente_seus_nao_mostra_intimacao_de_processo_alheio(self):
        self._autorizar(nivel_processos=NIVEL_SOMENTE_SEUS)
        outro = User.objects.create_user("outro_dono_processo", password="testpass")
        processo_alheio = Processo.objects.create(titulo="Processo Alheio", responsavel=outro)
        Intimacao.objects.create(
            processo=processo_alheio, motivo="Não deveria aparecer", prazo_manifestacao="2026-12-01",
        )

        resposta = self.client.get("/", HTTP_HOST=self.http_host)
        self.assertEqual(list(resposta.context["intimacoes"]), [])
