"""
Notificações ampliadas da Agenda Jurídica (PDR-0034, issue #33): avisos
por data (véspera/dia da fatal, data para fazer de Prazo vencida), uma
única vez por item/destinatário/motivo e nunca para item concluído ou
cancelado; e avisos de atribuição, reatribuição, convite recebido,
Prazo gerado pelo andamento e data fatal alterada no andamento.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import ConviteDelegacao, PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_TODOS
from apps.agenda.avisos import enviar_avisos_de_data
from apps.agenda.models import ItemAgenda
from apps.notificacoes.models import Notificacao
from apps.processos.models import MovimentacaoProcessual, Processo


class NotificacoesBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.hoje = timezone.localdate()
        self.responsavel = User.objects.create_user("resp_avisos", password="testpass")

    def _afazer(self, **kwargs):
        dados = {"tipo": "tarefa", "titulo": "Protocolar petição", "responsavel": self.responsavel}
        dados.update(kwargs)
        return ItemAgenda.objects.create(**dados)

    def _avisos(self, usuario, trecho=""):
        return Notificacao.objects.filter(destinatario=usuario, mensagem__contains=trecho)


class TestAvisosDeData(NotificacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_avisos_data"

    def test_vespera_e_dia_da_fatal_avisam_uma_unica_vez(self):
        self._afazer(titulo="Vence amanhã", data_fatal=self.hoje + timedelta(days=1))
        self._afazer(titulo="Vence hoje", data_fatal=self.hoje)
        self._afazer(titulo="Vence depois", data_fatal=self.hoje + timedelta(days=5))

        enviar_avisos_de_data(self.hoje)
        enviar_avisos_de_data(self.hoje)

        self.assertEqual(self._avisos(self.responsavel, "Data fatal amanhã").count(), 1)
        self.assertEqual(self._avisos(self.responsavel, "Data fatal hoje").count(), 1)
        self.assertFalse(self._avisos(self.responsavel, "Vence depois").exists())

    def test_item_concluido_cancelado_ou_com_convite_pendente_nao_avisa(self):
        self._afazer(data_fatal=self.hoje, status="concluido")
        self._afazer(data_fatal=self.hoje, status="cancelado", cancelado_em=timezone.now())
        delegante = User.objects.create_user("delegante_avisos", password="testpass")
        convite = ConviteDelegacao.objects.create(
            delegante=delegante, destinatario=self.responsavel,
            content_type_id=1, object_id=1,
        )
        self._afazer(data_fatal=self.hoje, convite_delegacao=convite)

        self.assertEqual(enviar_avisos_de_data(self.hoje), 0)
        self.assertFalse(Notificacao.objects.exists())

    def test_prazo_com_data_para_fazer_vencida_avisa_uma_vez_por_data(self):
        prazo = self._afazer(
            tipo="prazo", titulo="Contestação",
            data_para_fazer=self.hoje - timedelta(days=1), data_fatal=self.hoje + timedelta(days=3),
        )
        self._afazer(titulo="Tarefa atrasada", data_para_fazer=self.hoje - timedelta(days=1))

        enviar_avisos_de_data(self.hoje)
        enviar_avisos_de_data(self.hoje)
        self.assertEqual(self._avisos(self.responsavel, "Data para fazer vencida").count(), 1)
        self.assertFalse(self._avisos(self.responsavel, "Tarefa atrasada").exists())

        # Nova data para fazer também vencida: é outro aviso.
        prazo.data_para_fazer = self.hoje - timedelta(days=2)
        prazo.save()
        enviar_avisos_de_data(self.hoje)
        self.assertEqual(self._avisos(self.responsavel, "Data para fazer vencida").count(), 2)

    def test_prazo_com_fatal_ja_vencida_nao_gera_aviso_de_data_para_fazer(self):
        self._afazer(
            tipo="prazo", data_para_fazer=self.hoje - timedelta(days=10), data_fatal=self.hoje - timedelta(days=5),
        )
        self.assertEqual(enviar_avisos_de_data(self.hoje), 0)

    def test_job_periodico_envia_avisos_de_data(self):
        self._afazer(data_fatal=self.hoje)
        call_command("enviar_lembretes_agenda")
        call_command("enviar_lembretes_agenda")
        self.assertEqual(self._avisos(self.responsavel, "Data fatal hoje").count(), 1)


class TestAvisosDeAcao(NotificacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_avisos_acao"

    def setUp(self):
        super().setUp()
        self.autor = User.objects.create_user("autor_avisos", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel avisos")
        for usuario in (self.autor, self.responsavel):
            UsuarioPapel.objects.create(usuario=usuario, papel=papel)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_TODOS)
        self.client.force_login(self.autor)

    def _set_admin(self, user):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)

    def _criar_tarefa_para(self, responsavel):
        return self.client.post("/agenda/novo/", {
            "titulo": "Revisar contrato", "tipo": "tarefa", "prioridade": "media",
            "responsavel": responsavel.pk, "atribuidos": [responsavel.pk],
        }, HTTP_HOST=self.http_host)

    def test_criacao_direta_para_outro_avisa_o_responsavel(self):
        self._set_admin(self.autor)
        self._criar_tarefa_para(self.responsavel)

        self.assertTrue(ItemAgenda.objects.filter(responsavel=self.responsavel).exists())
        self.assertEqual(self._avisos(self.responsavel, "atribuiu a você").count(), 1)
        self.assertFalse(self._avisos(self.responsavel, "convidou").exists())

    def test_auto_atribuicao_nao_avisa(self):
        self._criar_tarefa_para(self.autor)
        self.assertTrue(ItemAgenda.objects.filter(responsavel=self.autor).exists())
        self.assertFalse(Notificacao.objects.exists())

    def test_convite_recebido_avisa_o_destinatario(self):
        from apps.accounts.models import HabilitacaoPapel
        from apps.accounts.permissoes_constants import HAB_AGENDA_ATRIBUIR_OUTROS

        HabilitacaoPapel.objects.create(
            papel=PapelAcesso.objects.get(nome="Papel avisos"), modulo=MODULO_AGENDA,
            item=HAB_AGENDA_ATRIBUIR_OUTROS, ativo=True,
        )
        self._criar_tarefa_para(self.responsavel)

        item = ItemAgenda.objects.get(responsavel=self.responsavel)
        self.assertIsNotNone(item.convite_delegacao)
        self.assertEqual(self._avisos(self.responsavel, "convidou você").count(), 1)
        self.assertFalse(self._avisos(self.responsavel, "atribuiu a você").exists())

    def test_reatribuicao_avisa_o_novo_responsavel(self):
        self._set_admin(self.autor)
        item = self._afazer(responsavel=self.autor)

        self.client.post(
            f"/agenda/{item.pk}/reatribuir/", {"destinatario": self.responsavel.pk}, HTTP_HOST=self.http_host,
        )

        item.refresh_from_db()
        self.assertEqual(item.responsavel, self.responsavel)
        self.assertEqual(self._avisos(self.responsavel, "atribuiu a você").count(), 1)

    def test_alterar_data_fatal_no_andamento_avisa_o_responsavel_do_prazo(self):
        processo = Processo.objects.create(responsavel=self.responsavel, titulo="Processo avisos")
        fatal = self.hoje + timedelta(days=20)
        andamento = MovimentacaoProcessual.objects.create(
            processo=processo, descricao="Intimação", tipo="despacho", data_prazo=fatal,
        )
        andamento.descricao = "Sem mudar a data"
        andamento.save()
        self.assertFalse(self._avisos(self.responsavel, "Data fatal alterada").exists())

        andamento.data_prazo = fatal + timedelta(days=5)
        andamento.save()
        self.assertEqual(self._avisos(self.responsavel, "Data fatal alterada").count(), 1)

        ItemAgenda.objects.filter(movimentacao_origem=andamento).update(status="concluido")
        andamento.data_prazo = fatal + timedelta(days=8)
        andamento.save()
        self.assertEqual(self._avisos(self.responsavel, "Data fatal alterada").count(), 1)

    def test_prazo_gerado_pelo_andamento_avisa_o_responsavel_do_processo_uma_vez(self):
        processo = Processo.objects.create(responsavel=self.responsavel, titulo="Processo novo prazo")
        fatal = self.hoje + timedelta(days=15)
        andamento = MovimentacaoProcessual.objects.create(
            processo=processo, descricao="Intimação", tipo="despacho", data_prazo=fatal,
        )
        andamento.descricao = "Revisado"
        andamento.save()

        avisos = self._avisos(self.responsavel, "Novo prazo no processo")
        self.assertEqual(avisos.count(), 1)
        self.assertIn(f"fatal {fatal:%d/%m}", avisos.get().mensagem)

        MovimentacaoProcessual.objects.create(processo=processo, descricao="Sem prazo", tipo="despacho")
        self.assertEqual(Notificacao.objects.count(), 1)

    def test_troca_de_responsavel_do_processo_avisa_quem_recebe_o_prazo(self):
        processo = Processo.objects.create(responsavel=self.responsavel, titulo="Processo troca")
        MovimentacaoProcessual.objects.create(
            processo=processo, descricao="Intimação", tipo="despacho", data_prazo=self.hoje + timedelta(days=20),
        )

        processo.responsavel = self.autor
        processo.save()

        self.assertEqual(self._avisos(self.autor, "pelo processo").count(), 1)
