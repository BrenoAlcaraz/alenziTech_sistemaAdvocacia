"""
Prazo gerado pelo andamento (PDR-0034): todo andamento com `data_prazo`
gera exatamente um item tipo Prazo para o responsável do processo, sem
convite, com data fatal travada na origem e data para fazer padrão de 2
dias corridos antes; alterar/remover o prazo acompanha; e a troca de
responsável do processo leva junto os Prazos gerados ainda abertos.
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, MODULO_PROCESSOS, NIVEL_TODOS
from apps.agenda.models import ItemAgenda
from apps.clientes.models import Cliente
from apps.processos.models import MovimentacaoProcessual, Processo
from apps.processos.services import transferir_processos_de_usuarios_sem_acesso


FATAL = date(2026, 10, 20)


class PrazoDoAndamentoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.dono = User.objects.create_user("dono_processo", password="testpass")
        self.outro = User.objects.create_user("outro_advogado", password="testpass")
        self.cliente = Cliente.objects.create(nome_razao_social="Cliente Prazo", tipo="PF", responsavel=self.dono)
        self.processo = Processo.objects.create(responsavel=self.dono, titulo="Processo Prazo")
        self.processo.clientes.add(self.cliente)

    def _andamento(self, data_prazo=FATAL, **kwargs):
        return MovimentacaoProcessual.objects.create(
            processo=self.processo, descricao="Intimação para contestar",
            tipo="despacho", data_prazo=data_prazo, **kwargs,
        )

    def _prazos(self):
        return ItemAgenda.objects.filter(movimentacao_origem__isnull=False)


class TestGeracaoDoPrazo(PrazoDoAndamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_prazo_andamento"

    def test_andamento_com_prazo_cria_um_prazo_para_o_responsavel_do_processo(self):
        andamento = self._andamento()

        item = ItemAgenda.objects.get(movimentacao_origem=andamento)
        self.assertEqual(item.tipo, "prazo")
        self.assertEqual(item.data_fatal, FATAL)
        self.assertEqual(item.data_para_fazer, FATAL - timedelta(days=2))
        self.assertEqual(item.responsavel, self.dono)
        self.assertEqual(item.processo, self.processo)
        self.assertEqual(item.cliente, self.cliente)
        self.assertIsNone(item.convite_delegacao)
        self.assertEqual(item.status, "a_fazer")

    def test_andamento_sem_prazo_nao_cria_item(self):
        self._andamento(data_prazo=None)
        self.assertFalse(self._prazos().exists())

    def test_salvar_de_novo_nunca_duplica(self):
        andamento = self._andamento()
        andamento.descricao = "Texto revisado"
        andamento.save()
        andamento.save()
        self.assertEqual(self._prazos().count(), 1)

    def test_alterar_data_prazo_atualiza_fatal_e_data_para_fazer_padrao(self):
        andamento = self._andamento()
        nova = FATAL + timedelta(days=10)
        andamento.data_prazo = nova
        andamento.save()

        item = ItemAgenda.objects.get(movimentacao_origem=andamento)
        self.assertEqual(item.data_fatal, nova)
        self.assertEqual(item.data_para_fazer, nova - timedelta(days=2))

    def test_alterar_data_prazo_preserva_data_para_fazer_ajustada(self):
        andamento = self._andamento()
        ajustada = FATAL - timedelta(days=5)
        ItemAgenda.objects.filter(movimentacao_origem=andamento).update(data_para_fazer=ajustada)
        andamento.data_prazo = FATAL + timedelta(days=10)
        andamento.save()

        item = ItemAgenda.objects.get(movimentacao_origem=andamento)
        self.assertEqual(item.data_para_fazer, ajustada)

    def test_remover_prazo_do_andamento_remove_o_item(self):
        andamento = self._andamento()
        andamento.data_prazo = None
        andamento.save()
        self.assertFalse(self._prazos().exists())

    def test_apagar_andamento_remove_o_item(self):
        andamento = self._andamento()
        andamento.delete()
        self.assertFalse(self._prazos().exists())

    def test_edicao_do_prazo_gerado_nao_altera_fatal_nem_vinculo(self):
        PerfilUsuario.objects.filter(user=self.dono).update(is_admin_escritorio=True)
        self.client.force_login(self.dono)
        andamento = self._andamento()
        item = ItemAgenda.objects.get(movimentacao_origem=andamento)

        r = self.client.post(
            f"/agenda/{item.pk}/editar/",
            {
                "tipo": "tarefa",
                "titulo": "Contestação",
                "data_fatal": "2030-01-01",
                "data_para_fazer": "2026-10-15",
                "processo": "",
                "cliente": "",
            },
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(r.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.titulo, "Contestação")
        self.assertEqual(item.tipo, "prazo")
        self.assertEqual(item.data_fatal, FATAL)
        self.assertEqual(item.data_para_fazer, date(2026, 10, 15))
        self.assertEqual(item.processo, self.processo)


class TestTrocaDeResponsavelDoProcesso(PrazoDoAndamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_prazo_troca_responsavel"

    def test_troca_leva_prazos_gerados_abertos_e_registra_historico(self):
        aberto = ItemAgenda.objects.get(movimentacao_origem=self._andamento())

        self.processo.responsavel = self.outro
        self.processo.save()

        aberto.refresh_from_db()
        self.assertEqual(aberto.responsavel, self.outro)
        reatribuicao = aberto.reatribuicoes.get()
        self.assertEqual(reatribuicao.responsavel_anterior, self.dono)
        self.assertEqual(reatribuicao.responsavel_novo, self.outro)
        self.assertIsNone(reatribuicao.autor)

    def test_concluido_cancelado_e_prazo_manual_nao_mudam(self):
        concluido = ItemAgenda.objects.get(movimentacao_origem=self._andamento())
        concluido.status = "concluido"
        concluido.save()
        cancelado = ItemAgenda.objects.get(movimentacao_origem=self._andamento())
        cancelado.status = "cancelado"
        cancelado.save()
        manual = ItemAgenda.objects.create(
            tipo="prazo", titulo="Prazo manual", data_fatal=FATAL,
            responsavel=self.dono, processo=self.processo,
        )

        self.processo.responsavel = self.outro
        self.processo.save()

        for item in (concluido, cancelado, manual):
            item.refresh_from_db()
            self.assertEqual(item.responsavel, self.dono)

    def test_salvar_processo_sem_trocar_responsavel_nao_mexe(self):
        aberto = ItemAgenda.objects.get(movimentacao_origem=self._andamento())
        self.processo.titulo = "Outro título"
        self.processo.save()
        self.assertFalse(aberto.reatribuicoes.exists())

    def test_transferencia_ao_administrador_por_perda_de_acesso_leva_os_prazos(self):
        admin = User.objects.create_user("administrador", password="testpass")
        PerfilUsuario.objects.filter(user=admin).update(is_admin_escritorio=True)
        papel = PapelAcesso.objects.create(nome="Papel Sem Processos")
        UsuarioPapel.objects.create(usuario=self.dono, papel=papel)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_TODOS)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PROCESSOS, ativo=False, nivel=NIVEL_TODOS)
        aberto = ItemAgenda.objects.get(movimentacao_origem=self._andamento())

        transferir_processos_de_usuarios_sem_acesso([self.dono.pk])

        self.processo.refresh_from_db()
        aberto.refresh_from_db()
        self.assertEqual(self.processo.responsavel, admin)
        self.assertEqual(aberto.responsavel, admin)
