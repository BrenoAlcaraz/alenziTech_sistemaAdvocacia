"""
Integrações da Agenda Jurídica (PDR-0034, issue #33): card "Agenda do
processo/cliente" com itens de qualquer tipo no escopo da agenda, aba
Prazos do processo levando ao item e atalho do Painel do gestor.
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    MODULO_CLIENTES,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.models import ItemAgenda
from apps.clientes.models import Cliente
from apps.processos.models import MovimentacaoProcessual, Processo


class TestIntegracoesAgenda(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_integracoes"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("adv_integracoes", password="testpass")
        self.outro = User.objects.create_user("outro_integracoes", password="testpass")
        self.papel = PapelAcesso.objects.create(nome="Papel integrações")
        UsuarioPapel.objects.create(usuario=self.usuario, papel=self.papel)
        for modulo in (MODULO_PROCESSOS, MODULO_CLIENTES):
            PermissaoPapel.objects.create(papel=self.papel, modulo=modulo, ativo=True, nivel=NIVEL_TODOS)
        PermissaoPapel.objects.create(papel=self.papel, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_SOMENTE_SEUS)
        self.cliente = Cliente.objects.create(nome_razao_social="Cliente Integração", tipo="PF", responsavel=self.usuario)
        self.processo = Processo.objects.create(criado_por=self.usuario, titulo="Processo Integração")
        self.processo.clientes.add(self.cliente)
        self.client.force_login(self.usuario)

    def _item(self, titulo, **kwargs):
        dados = {"tipo": "tarefa", "responsavel": self.usuario, "processo": self.processo, "cliente": self.cliente}
        dados.update(kwargs)
        return ItemAgenda.objects.create(titulo=titulo, **dados)

    def _get(self, url):
        return self.client.get(url, HTTP_HOST=self.http_host)

    def test_card_do_processo_e_do_cliente_mostra_qualquer_tipo_no_escopo(self):
        self._item("Tarefa própria")
        self._item("Audiência própria", tipo="audiencia", data_hora_inicio=timezone.now() + timedelta(days=2))
        self._item("Tarefa alheia", responsavel=self.outro)
        self._item("Tarefa concluída", status="concluido")

        for url, chave in (
            (f"/processos/{self.processo.pk}/", "agenda_do_processo"),
            (f"/clientes/{self.cliente.pk}/", "agenda_do_cliente"),
        ):
            resposta = self._get(url)
            agenda = resposta.context[chave]
            titulos = {item.titulo for item in agenda["itens"]}
            self.assertEqual(titulos, {"Tarefa própria", "Audiência própria"}, url)
            self.assertEqual(agenda["total"], 2)
            filtro = "processo" if chave == "agenda_do_processo" else "cliente"
            pk = self.processo.pk if filtro == "processo" else self.cliente.pk
            self.assertContains(resposta, f"/agenda/novo/?tipo=audiencia&{filtro}={pk}")
            self.assertContains(resposta, f"/agenda/?{filtro}={pk}")

    def test_item_so_visivel_leva_a_agenda_filtrada_e_nao_ao_formulario(self):
        PermissaoPapel.objects.filter(papel=self.papel, modulo=MODULO_AGENDA).update(nivel=NIVEL_TODOS)
        alheia = self._item("Tarefa alheia", responsavel=self.outro)

        agenda = self._get(f"/processos/{self.processo.pk}/").context["agenda_do_processo"]

        self.assertEqual(agenda["itens"][0].pk, alheia.pk)
        self.assertEqual(agenda["itens"][0].url, f"/agenda/?tipo=tarefa&processo={self.processo.pk}")

    def test_sem_modulo_agenda_nao_ha_card(self):
        PermissaoPapel.objects.filter(papel=self.papel, modulo=MODULO_AGENDA).delete()
        self._item("Tarefa própria")

        resposta = self._get(f"/processos/{self.processo.pk}/")

        self.assertIsNone(resposta.context["agenda_do_processo"])
        self.assertNotContains(resposta, "Agenda do processo")

    def test_aba_prazos_leva_ao_item_gerado(self):
        andamento = MovimentacaoProcessual.objects.create(
            processo=self.processo, descricao="Intimação", tipo="despacho", data_prazo=date(2026, 12, 1),
        )
        item = ItemAgenda.objects.get(movimentacao_origem=andamento)

        resposta = self._get(f"/processos/{self.processo.pk}/?aba=prazos")

        self.assertEqual(resposta.context["prazos"][0].item_prazo, item)
        self.assertContains(resposta, f"/agenda/{item.pk}/editar/")

    def test_aba_prazos_sem_link_quando_o_prazo_nao_esta_no_escopo(self):
        andamento = MovimentacaoProcessual.objects.create(
            processo=self.processo, descricao="Intimação", tipo="despacho", data_prazo=date(2026, 12, 1),
        )
        ItemAgenda.objects.filter(movimentacao_origem=andamento).update(responsavel=self.outro)

        resposta = self._get(f"/processos/{self.processo.pk}/?aba=prazos")

        self.assertIsNone(resposta.context["prazos"][0].item_prazo)
        self.assertNotContains(resposta, "Ver na Agenda Jurídica")

    def test_painel_do_gestor_tem_atalho_unico_para_a_agenda_filtrada(self):
        PerfilUsuario.objects.filter(user=self.usuario).update(is_admin_escritorio=True)

        resposta = self._get(f"/gestor/{self.outro.pk}/")

        self.assertContains(resposta, f'href="/agenda/?usuario={self.outro.pk}"', count=1)
        self.assertContains(resposta, "Ir para Agenda Jurídica")
        self.assertNotContains(resposta, "/tarefas/")

    def test_log_de_atividade_registra_as_acoes_do_item(self):
        from apps.atividade.models import LogAtividade

        PerfilUsuario.objects.filter(user=self.usuario).update(is_admin_escritorio=True)
        dados = {"titulo": "Tarefa logada", "tipo": "tarefa", "prioridade": "media"}
        self.client.post("/agenda/novo/", dados, HTTP_HOST=self.http_host)
        item = ItemAgenda.objects.get(titulo="Tarefa logada")
        self.client.post(f"/agenda/{item.pk}/editar/", {**dados, "titulo": "Tarefa logada 2"}, HTTP_HOST=self.http_host)
        for acao in ("iniciar", "concluir", "reabrir"):
            self.client.post(f"/agenda/{item.pk}/{acao}/", HTTP_HOST=self.http_host)
        self.client.post(f"/agenda/{item.pk}/reatribuir/", {"destinatario": self.outro.pk}, HTTP_HOST=self.http_host)
        self.client.post(f"/agenda/{item.pk}/cancelar/", HTTP_HOST=self.http_host)
        self.client.post(f"/agenda/{item.pk}/excluir/", HTTP_HOST=self.http_host)

        self.assertEqual(
            list(LogAtividade.objects.filter(usuario=self.usuario).exclude(tipo="login").order_by("pk").values_list("tipo", flat=True)),
            [
                "tarefa_criada", "tarefa_editada", "tarefa_iniciada", "tarefa_concluida",
                "tarefa_reaberta", "tarefa_reatribuida", "tarefa_cancelada", "tarefa_excluida",
            ],
        )
