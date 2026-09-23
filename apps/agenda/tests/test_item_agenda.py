"""
Item unificado da Agenda Jurídica (PDR-0034): validação por natureza
(Afazer × Evento), status único, reatribuição com histórico para
qualquer item, participantes em Afazer (só visibilidade) e aviso de
conclusão ao criador (herdado de Tarefas, PDR-0016).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_AGENDA_ATRIBUIR_OUTROS,
    MODULO_AGENDA,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.forms import ItemAgendaForm
from apps.agenda.models import ItemAgenda, ParticipanteItemAgenda
from apps.notificacoes.models import Notificacao


class ItemAgendaBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username, *, nivel=NIVEL_TODOS, atribuir_outros=False):
        user = User.objects.create_user(username, password="testpass")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=nivel)
        if atribuir_outros:
            HabilitacaoPapel.objects.create(
                papel=papel, modulo=MODULO_AGENDA, item=HAB_AGENDA_ATRIBUIR_OUTROS, ativo=True
            )
        return user

    def _post(self, url, dados=None):
        return self.client.post(url, dados or {}, HTTP_HOST=self.http_host)


class TestValidacaoPorNatureza(ItemAgendaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_item_natureza"

    def _form(self, **dados):
        return ItemAgendaForm(data={"titulo": "Item", **dados})

    def test_prazo_sem_data_fatal_e_rejeitado(self):
        form = self._form(tipo="prazo", data_para_fazer="2026-10-01")
        self.assertFalse(form.is_valid())
        self.assertIn("data_fatal", form.errors)

    def test_evento_sem_inicio_e_rejeitado(self):
        form = self._form(tipo="audiencia")
        self.assertFalse(form.is_valid())
        self.assertIn("data_hora_inicio", form.errors)

    def test_afazer_sem_nenhuma_data_e_permitido(self):
        form = self._form(tipo="tarefa")
        self.assertTrue(form.is_valid(), form.errors)

    def test_cada_natureza_guarda_so_os_proprios_campos(self):
        afazer = self._form(
            tipo="protocolo", data_para_fazer="2026-10-01", data_hora_inicio="2026-10-01T10:00",
            local="Fórum", prioridade="alta",
        )
        self.assertTrue(afazer.is_valid(), afazer.errors)
        self.assertIsNone(afazer.cleaned_data["data_hora_inicio"])
        self.assertEqual(afazer.cleaned_data["local"], "")
        self.assertEqual(afazer.cleaned_data["prioridade"], "alta")

        evento = self._form(
            tipo="reuniao", data_hora_inicio="2026-10-01T10:00", data_fatal="2026-10-02",
        )
        self.assertTrue(evento.is_valid(), evento.errors)
        self.assertIsNone(evento.cleaned_data["data_fatal"])

    def test_hora_para_fazer_exige_data(self):
        form = self._form(tipo="tarefa", hora_para_fazer="09:00")
        self.assertFalse(form.is_valid())
        self.assertIn("hora_para_fazer", form.errors)

    def test_item_em_andamento_nao_vira_evento(self):
        item = ItemAgenda.objects.create(tipo="tarefa", titulo="Em curso", status="em_andamento")
        form = ItemAgendaForm(
            data={"titulo": "Em curso", "tipo": "reuniao", "data_hora_inicio": "2026-10-01T10:00"},
            instance=item,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("tipo", form.errors)


class TestStatusEReatribuicao(ItemAgendaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_item_status_reatribuicao"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("resp_item", atribuir_outros=True)
        self.colega = self._user("colega_item")
        self.criador = self._user("criador_item")
        self.tarefa = ItemAgenda.objects.create(
            tipo="tarefa", titulo="Elaborar petição", responsavel=self.responsavel, criado_por=self.criador,
        )
        self.evento = ItemAgenda.objects.create(
            tipo="audiencia", titulo="Audiência", responsavel=self.responsavel,
            data_hora_inicio="2026-10-01T10:00:00Z",
        )

    def test_iniciar_afazer(self):
        self.client.force_login(self.responsavel)
        self._post(f"/agenda/{self.tarefa.pk}/iniciar/")
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "em_andamento")

    def test_evento_nao_tem_em_andamento(self):
        self.client.force_login(self.responsavel)
        r = self._post(f"/agenda/{self.evento.pk}/iniciar/")
        self.assertEqual(r.status_code, 404)
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.status, "a_fazer")

    def test_concluir_avisa_criador_diferente_do_responsavel(self):
        self.client.force_login(self.responsavel)
        self._post(f"/agenda/{self.tarefa.pk}/concluir/")
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "concluido")
        self.assertTrue(Notificacao.objects.filter(destinatario=self.criador).exists())

    def test_reabrir_concluido(self):
        self.client.force_login(self.responsavel)
        self.tarefa.status = "concluido"
        self.tarefa.save()
        self._post(f"/agenda/{self.tarefa.pk}/reabrir/")
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "a_fazer")

    def test_nao_responsavel_nao_muda_status_nem_reatribui(self):
        self.client.force_login(self.colega)
        self.assertEqual(self._post(f"/agenda/{self.tarefa.pk}/concluir/").status_code, 404)
        self.assertEqual(self._post(f"/agenda/{self.tarefa.pk}/iniciar/").status_code, 404)
        r = self._post(f"/agenda/{self.tarefa.pk}/reatribuir/", {"destinatario": self.colega.pk})
        self.assertEqual(r.status_code, 404)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "a_fazer")
        self.assertEqual(self.tarefa.responsavel, self.responsavel)

    def test_reatribuicao_de_evento_registra_historico(self):
        ParticipanteItemAgenda.objects.create(item=self.evento, usuario=self.colega)
        self.client.force_login(self.responsavel)
        r = self._post(f"/agenda/{self.evento.pk}/reatribuir/", {"destinatario": self.colega.pk})

        self.assertEqual(r.status_code, 302)
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.responsavel, self.colega)
        self.assertEqual(self.evento.atribuidor, self.responsavel)
        historico = self.evento.reatribuicoes.get()
        self.assertEqual(historico.responsavel_anterior, self.responsavel)
        self.assertEqual(historico.responsavel_novo, self.colega)
        self.assertEqual(historico.autor, self.responsavel)
        self.assertFalse(self.evento.participacoes.filter(usuario=self.colega).exists())

    def test_reatribuir_a_outro_exige_habilitacao(self):
        item = ItemAgenda.objects.create(tipo="tarefa", titulo="Do colega", responsavel=self.colega)
        self.client.force_login(self.colega)
        r = self._post(f"/agenda/{item.pk}/reatribuir/", {"destinatario": self.responsavel.pk})
        self.assertEqual(r.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.responsavel, self.colega)
        self.assertFalse(item.reatribuicoes.exists())

    def test_administrador_reatribui_item_alheio(self):
        admin = User.objects.create_user("admin_item", password="testpass")
        PerfilUsuario.objects.filter(user=admin).update(is_admin_escritorio=True)
        self.client.force_login(admin)
        self._post(f"/agenda/{self.tarefa.pk}/reatribuir/", {"destinatario": self.colega.pk})
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.responsavel, self.colega)


class TestParticipanteEmAfazer(ItemAgendaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_item_participante_afazer"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("resp_afazer")
        self.participante = self._user("part_afazer", nivel=NIVEL_SOMENTE_SEUS)
        self.tarefa = ItemAgenda.objects.create(
            tipo="tarefa", titulo="Revisar contrato", responsavel=self.responsavel,
        )
        ParticipanteItemAgenda.objects.create(item=self.tarefa, usuario=self.participante)

    def test_participante_ve_o_afazer_no_proprio_escopo(self):
        self.client.force_login(self.participante)
        r = self.client.get("/agenda/", HTTP_HOST=self.http_host)
        self.assertIn(self.tarefa, r.context["itens"])

    def test_participante_nao_confirma_presenca_em_afazer(self):
        self.client.force_login(self.participante)
        r = self._post(f"/agenda/{self.tarefa.pk}/confirmar-presenca/")
        self.assertEqual(r.status_code, 404)

    def test_participante_nao_muta_o_afazer(self):
        self.client.force_login(self.participante)
        r = self._post(f"/agenda/{self.tarefa.pk}/concluir/")
        self.assertEqual(r.status_code, 404)

    def test_adicionar_participante_em_afazer_nao_pede_confirmacao(self):
        novo = self._user("novo_afazer")
        self.client.force_login(self.responsavel)
        self._post(f"/agenda/{self.tarefa.pk}/participantes/adicionar/", {"usuario": novo.pk})
        self.assertTrue(self.tarefa.participacoes.filter(usuario=novo).exists())
        self.assertFalse(Notificacao.objects.filter(destinatario=novo).exists())
