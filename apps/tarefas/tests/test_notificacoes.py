"""
Testes de notificação de conclusão de tarefa (PDR-0016, parte Tarefas):
criador diferente do responsável recebe notificação ao concluir; criador
igual ao responsável e tarefa sem criador não geram notificação; reabrir
não gera notificação.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_TAREFAS, NIVEL_TODOS
from apps.notificacoes.models import Notificacao
from apps.tarefas.models import Tarefa


class TarefasNotificacaoBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_notificacao_tarefas"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.criador = User.objects.create_user("criador", password="testpass")
        self.responsavel = User.objects.create_user("responsavel", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Notificação Tarefas")
        UsuarioPapel.objects.create(usuario=self.responsavel, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_TAREFAS, ativo=True, nivel=NIVEL_TODOS
        )
        self.client.force_login(self.responsavel)

    def _concluir(self, tarefa):
        return self.client.post(
            f"/tarefas/{tarefa.pk}/concluir/",
            {"next": "/tarefas/"},
            HTTP_HOST=self.http_host,
        )

    def _reabrir(self, tarefa):
        return self.client.post(
            f"/tarefas/{tarefa.pk}/reabrir/",
            {"next": "/tarefas/"},
            HTTP_HOST=self.http_host,
        )


class TestNotificacaoAoConcluir(TarefasNotificacaoBase):
    def test_criador_diferente_do_responsavel_recebe_notificacao(self):
        tarefa = Tarefa.objects.create(
            titulo="Elaborar petição",
            criador=self.criador,
            responsavel=self.responsavel,
        )
        resposta = self._concluir(tarefa)
        self.assertEqual(resposta.status_code, 302)
        tarefa.refresh_from_db()
        self.assertEqual(tarefa.status, "concluida")
        notificacao = Notificacao.objects.get(destinatario=self.criador)
        self.assertIn(tarefa.titulo, notificacao.mensagem)
        self.assertFalse(notificacao.lida)

    def test_criador_igual_ao_responsavel_nao_gera_notificacao(self):
        tarefa = Tarefa.objects.create(
            titulo="Revisar contrato",
            criador=self.responsavel,
            responsavel=self.responsavel,
        )
        self._concluir(tarefa)
        self.assertFalse(Notificacao.objects.exists())

    def test_tarefa_sem_criador_nao_gera_notificacao_nem_erro(self):
        tarefa = Tarefa.objects.create(
            titulo="Tarefa sem criador",
            criador=None,
            responsavel=self.responsavel,
        )
        resposta = self._concluir(tarefa)
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Notificacao.objects.exists())

    def test_reabrir_nao_gera_notificacao(self):
        tarefa = Tarefa.objects.create(
            titulo="Audiência",
            criador=self.criador,
            responsavel=self.responsavel,
            status="concluida",
        )
        self._reabrir(tarefa)
        self.assertFalse(Notificacao.objects.exists())
