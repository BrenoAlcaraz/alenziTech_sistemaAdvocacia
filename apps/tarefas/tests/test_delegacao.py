"""
Testes de delegação de tarefas (PDR-0002): criação com destinatário
diferente do criador, criação sem destinatário explícito, reatribuição
preservando o histórico mínimo, e edição comum não altera o responsável.

O criador destas fixtures recebe módulo `tarefas` + `tarefas_atribuir_outros`
— pré-requisito de autorização introduzido para o módulo (ver
apps/tarefas/tests/test_autorizacao.py) sem o qual a própria delegação
seria rejeitada.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import HAB_TAREFAS_ATRIBUIR_OUTROS, MODULO_TAREFAS, NIVEL_TODOS
from apps.tarefas.models import ReatribuicaoTarefa, Tarefa


class TarefasDelegacaoBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_delegacao_tarefas"

    def _set_admin(self, user, value=True):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=value)

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.criador = User.objects.create_user("criador", password="testpass")
        self.destinatario = User.objects.create_user("destinatario", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Delegação Tarefas")
        UsuarioPapel.objects.create(usuario=self.criador, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_TAREFAS, ativo=True, nivel=NIVEL_TODOS
        )
        HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_TAREFAS, item=HAB_TAREFAS_ATRIBUIR_OUTROS, ativo=True
        )
        self.client.force_login(self.criador)


class TestCriacaoComDelegacao(TarefasDelegacaoBase):
    def test_criar_com_destinatario_diferente_do_criador(self):
        resposta = self.client.post(
            "/tarefas/nova/",
            {
                "titulo": "Elaborar petição",
                "descricao": "",
                "prioridade": "media",
                "prazo": "",
                "cliente": "",
                "processo": "",
                "destinatario": self.destinatario.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        tarefa = Tarefa.objects.get(titulo="Elaborar petição")
        self.assertEqual(tarefa.criador_id, self.criador.pk)
        self.assertEqual(tarefa.atribuidor_id, self.criador.pk)
        self.assertEqual(tarefa.responsavel_id, self.destinatario.pk)
        self.assertIsNotNone(tarefa.atribuido_em)

    def test_criar_sem_destinatario_atribui_ao_proprio_criador(self):
        resposta = self.client.post(
            "/tarefas/nova/",
            {
                "titulo": "Revisar contrato",
                "descricao": "",
                "prioridade": "media",
                "prazo": "",
                "cliente": "",
                "processo": "",
                "destinatario": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        tarefa = Tarefa.objects.get(titulo="Revisar contrato")
        self.assertEqual(tarefa.criador_id, self.criador.pk)
        self.assertEqual(tarefa.atribuidor_id, self.criador.pk)
        self.assertEqual(tarefa.responsavel_id, self.criador.pk)


class TestReatribuicao(TarefasDelegacaoBase):
    """
    O criador é promovido a admin: após a primeira reatribuição ele deixa
    de ser o responsável atual, e só o Administrador do escritório
    mantém acesso de mutação a uma tarefa alheia — necessário para o
    cenário de duas reatribuições consecutivas pelo mesmo ator.
    """

    def setUp(self):
        super().setUp()
        self._set_admin(self.criador, True)
        self.tarefa = Tarefa.objects.create(
            titulo="Protocolar recurso",
            criador=self.criador,
            atribuidor=self.criador,
            responsavel=self.criador,
        )

    def test_reatribuir_atualiza_responsavel_e_preserva_historico(self):
        resposta = self.client.post(
            f"/tarefas/{self.tarefa.pk}/reatribuir/",
            {"destinatario": self.destinatario.pk, "next": "/tarefas/"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.responsavel_id, self.destinatario.pk)

        historico = ReatribuicaoTarefa.objects.get(tarefa=self.tarefa)
        self.assertEqual(historico.responsavel_anterior_id, self.criador.pk)
        self.assertEqual(historico.responsavel_novo_id, self.destinatario.pk)
        self.assertEqual(historico.autor_id, self.criador.pk)
        self.assertIsNotNone(historico.criado_em)

    def test_duas_reatribuicoes_preservam_as_duas_entradas(self):
        outro = User.objects.create_user("terceiro", password="testpass")

        self.client.post(
            f"/tarefas/{self.tarefa.pk}/reatribuir/",
            {"destinatario": self.destinatario.pk, "next": "/tarefas/"},
            HTTP_HOST=self.http_host,
        )
        self.client.post(
            f"/tarefas/{self.tarefa.pk}/reatribuir/",
            {"destinatario": outro.pk, "next": "/tarefas/"},
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(ReatribuicaoTarefa.objects.filter(tarefa=self.tarefa).count(), 2)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.responsavel_id, outro.pk)


class TestEdicaoNaoAlteraResponsavel(TarefasDelegacaoBase):
    """
    Editor é diferente do responsável da tarefa (criador != destinatario)
    — sob o escopo de mutação (responsável ou Administrador), só o
    Administrador alcança essa tarefa, por isso o criador é promovido a
    admin aqui especificamente para exercitar o cenário.
    """

    def setUp(self):
        super().setUp()
        self._set_admin(self.criador, True)
        self.tarefa = Tarefa.objects.create(
            titulo="Audiência",
            criador=self.criador,
            atribuidor=self.criador,
            responsavel=self.destinatario,
        )

    def test_editar_titulo_nao_muda_responsavel(self):
        resposta = self.client.post(
            f"/tarefas/{self.tarefa.pk}/editar/",
            {
                "titulo": "Audiência remarcada",
                "descricao": "",
                "prioridade": "media",
                "prazo": "",
                "cliente": "",
                "processo": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.titulo, "Audiência remarcada")
        self.assertEqual(self.tarefa.responsavel_id, self.destinatario.pk)


class TestStatusCancelada(TarefasDelegacaoBase):
    def test_status_cancelada_e_um_valor_valido(self):
        tarefa = Tarefa.objects.create(
            titulo="Tarefa cancelada",
            criador=self.criador,
            atribuidor=self.criador,
            responsavel=self.criador,
            status="cancelada",
        )
        tarefa.refresh_from_db()
        self.assertEqual(tarefa.status, "cancelada")

    def test_acao_cancelar_e_alcancavel_pela_ui(self):
        tarefa = Tarefa.objects.create(
            titulo="Tarefa a cancelar",
            criador=self.criador,
            atribuidor=self.criador,
            responsavel=self.criador,
            status="a_fazer",
        )
        resposta = self.client.post(
            f"/tarefas/{tarefa.pk}/cancelar/",
            {"next": "/tarefas/"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        tarefa.refresh_from_db()
        self.assertEqual(tarefa.status, "cancelada")
