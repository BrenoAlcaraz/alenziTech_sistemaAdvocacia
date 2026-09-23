"""
Tela única da Agenda Jurídica (PDR-0034): Meu dia, Calendário e Kanban
saem da mesma lista filtrada no mesmo request; a barra de filtros vale
para as três visões; o que cada pessoa vê de filtro/ação segue o que ela
pode fazer (a autorização continua no backend).
"""

from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.delegacao import criar_convite_delegacao
from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_AGENDA_ATRIBUIR_OUTROS,
    MODULO_AGENDA,
    MODULO_GERIR,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.models import ItemAgenda, ParticipanteItemAgenda
from apps.clientes.models import Cliente
from apps.processos.models import MovimentacaoProcessual, Processo


class TelaAgendaBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.hoje = timezone.localdate()

    def _user(self, username, *, nivel=NIVEL_TODOS, gerir=False, atribuir=False):
        user = User.objects.create_user(username=username, password="testpass")
        papel = PapelAcesso.objects.create(nome=f"Papel {username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_AGENDA, ativo=True, nivel=nivel)
        if gerir:
            PermissaoPapel.objects.create(papel=papel, modulo=MODULO_GERIR, ativo=True, nivel="")
        if atribuir:
            HabilitacaoPapel.objects.create(
                papel=papel, modulo=MODULO_AGENDA, item=HAB_AGENDA_ATRIBUIR_OUTROS, ativo=True
            )
        return user

    def _afazer(self, titulo, *, responsavel, tipo="tarefa", **kwargs):
        return ItemAgenda.objects.create(tipo=tipo, titulo=titulo, responsavel=responsavel, **kwargs)

    def _evento(self, titulo, *, responsavel, inicio, tipo="reuniao", **kwargs):
        return ItemAgenda.objects.create(
            tipo=tipo, titulo=titulo, responsavel=responsavel, data_hora_inicio=inicio, **kwargs
        )

    def _em(self, dias, hora=10):
        return timezone.make_aware(datetime.combine(self.hoje + timedelta(days=dias), time(hora)))

    def _get(self, query=""):
        return self.client.get(f"/agenda/{query}", HTTP_HOST=self.http_host)

    @staticmethod
    def _titulos(itens):
        return [i.titulo for i in itens]

    def _grupo(self, r, chave):
        return self._titulos(next(g for g in r.context["grupos_dia"] if g["chave"] == chave)["itens"])

    def _coluna(self, r, status):
        return self._titulos(next(c for c in r.context["colunas_kanban"] if c["status"] == status)["itens"])


class TestVisoesEFiltros(TelaAgendaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_tela_visoes"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Tela Visoes"
        tenant.slug = "agenda-tela-visoes"

    def setUp(self):
        super().setUp()
        self.user = self._user("usuario_tela")
        self.client.force_login(self.user)

    def test_tres_visoes_no_mesmo_request_com_meu_dia_padrao(self):
        r = self._get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["visao"], "dia")
        for visao in ("dia", "calendario", "kanban"):
            self.assertContains(r, f'data-view-toggle="{visao}"')
            self.assertContains(r, f'data-view="{visao}"')
        self.assertEqual(self._get("?visao=kanban").context["visao"], "kanban")
        self.assertEqual(self._get("?visao=invalida").context["visao"], "dia")

    def test_meu_dia_agrupa_cada_item_uma_vez(self):
        u = self.user
        self._afazer("Fatal vencida", responsavel=u, data_fatal=self.hoje - timedelta(days=1))
        self._afazer("Para hoje", responsavel=u, data_para_fazer=self.hoje)
        self._evento("Reunião amanhã", responsavel=u, inicio=self._em(1))
        self._afazer("Em 5 dias", responsavel=u, data_para_fazer=self.hoje + timedelta(days=5))
        self._afazer("Em 20 dias", responsavel=u, data_para_fazer=self.hoje + timedelta(days=20))
        self._afazer("Sem data", responsavel=u)
        self._afazer("Sem data concluído", responsavel=u, status="concluido")
        self._afazer("Concluído vencido", responsavel=u, status="concluido", data_fatal=self.hoje - timedelta(days=3))
        self._evento("Audiência passada", responsavel=u, inicio=self._em(-1), tipo="audiencia")

        r = self._get()
        self.assertCountEqual(self._grupo(r, "atrasados"), ["Audiência passada", "Fatal vencida"])
        self.assertEqual(self._grupo(r, "hoje"), ["Para hoje"])
        self.assertEqual(self._grupo(r, "amanha"), ["Reunião amanhã"])
        self.assertEqual(self._grupo(r, "proximos"), ["Em 5 dias"])
        self.assertEqual(self._grupo(r, "sem_data"), ["Sem data"])
        todos = sum((g["itens"] for g in r.context["grupos_dia"]), [])
        self.assertEqual(len(todos), len(set(todos)))
        self.assertNotIn("Em 20 dias", self._titulos(todos))
        self.assertNotIn("Concluído vencido", self._titulos(todos))

    def test_calendario_posiciona_afazer_evento_e_marca_a_fatal(self):
        u = self.user
        dia = self.hoje.replace(day=10)
        fatal = self.hoje.replace(day=20)
        self._afazer("Com as duas datas", responsavel=u, tipo="prazo", data_para_fazer=dia, data_fatal=fatal)
        self._afazer("Só fatal", responsavel=u, tipo="protocolo", data_fatal=dia)
        self._afazer("Sem data", responsavel=u)
        self._evento("Perícia", responsavel=u, tipo="pericia",
                     inicio=timezone.make_aware(datetime.combine(dia, time(14))))

        r = self._get(f"?visao=calendario&ano={dia.year}&mes={dia.month}&dia=10")
        self.assertEqual(sorted(self._titulos(r.context["itens_dia"])), ["Com as duas datas", "Perícia", "Só fatal"])
        dias = {d["numero"]: d for d in r.context["cal_dias"]}
        self.assertTrue(dias[20]["fatal"])
        self.assertTrue(dias[10]["fatal"])
        self.assertEqual(dias[20]["tipos"], [])
        self.assertEqual({t["tipo"] for t in dias[10]["tipos"]}, {"prazo", "protocolo", "pericia"})
        self.assertContains(r, "data-marcador-fatal")

    def test_kanban_so_afazeres_por_status_com_ordenacao(self):
        u = self.user
        self._afazer("Baixa", responsavel=u, prioridade="baixa")
        self._afazer("Alta", responsavel=u, prioridade="alta")
        self._afazer("Andando", responsavel=u, status="em_andamento")
        self._afazer("Feita", responsavel=u, status="concluido")
        self._evento("Reunião", responsavel=u, inicio=self._em(1))

        r = self._get("?visao=kanban&ordem=prioridade_alta")
        self.assertEqual(self._coluna(r, "a_fazer"), ["Alta", "Baixa"])
        self.assertEqual(self._coluna(r, "em_andamento"), ["Andando"])
        self.assertEqual(self._coluna(r, "concluido"), ["Feita"])
        kanban = sum((c["itens"] for c in r.context["colunas_kanban"]), [])
        self.assertNotIn("Reunião", self._titulos(kanban))
        self.assertEqual(self._coluna(self._get("?ordem=prioridade_baixa"), "a_fazer"), ["Baixa", "Alta"])

    def test_filtros_de_tipo_natureza_e_origem_valem_em_todas_as_visoes(self):
        u = self.user
        processo = Processo.objects.create(responsavel=u, titulo="Processo Tela")
        MovimentacaoProcessual.objects.create(
            processo=processo, descricao="Intimação", tipo="despacho", data_prazo=self.hoje + timedelta(days=4),
        )
        self._afazer("Prazo manual", responsavel=u, tipo="prazo", data_fatal=self.hoje + timedelta(days=4))
        self._afazer("Tarefa", responsavel=u, data_para_fazer=self.hoje + timedelta(days=4))
        self._evento("Reunião", responsavel=u, inicio=self._em(4))

        r = self._get("?origem=processo")
        self.assertEqual(len(r.context["itens"]), 1)
        self.assertTrue(r.context["itens"][0].gerado_pelo_processo)
        self.assertContains(r, 'title="Gerado pelo andamento do processo"')

        r = self._get("?tipo=prazo&origem=manual")
        self.assertEqual(self._titulos(r.context["itens"]), ["Prazo manual"])
        self.assertEqual(self._grupo(r, "proximos"), ["Prazo manual"])
        self.assertEqual(self._coluna(r, "a_fazer"), ["Prazo manual"])

        r = self._get("?natureza=evento")
        self.assertEqual(self._titulos(r.context["itens"]), ["Reunião"])
        self.assertEqual(self._coluna(r, "a_fazer"), [])

    def test_filtro_de_processo_e_cliente_vale_em_todas_as_visoes_e_segue_nos_links(self):
        u = self.user
        cliente = Cliente.objects.create(nome_razao_social="Cliente Tela", tipo="PF", responsavel=u)
        processo = Processo.objects.create(responsavel=u, titulo="Processo Filtro")
        processo.clientes.add(cliente)
        amanha = self.hoje + timedelta(days=1)
        self._afazer("Do processo", responsavel=u, processo=processo, cliente=cliente, data_para_fazer=amanha)
        self._afazer("Avulso", responsavel=u, data_para_fazer=amanha)

        for query in (f"?processo={processo.pk}", f"?cliente={cliente.pk}"):
            r = self._get(query + f"&ano={amanha.year}&mes={amanha.month}&dia={amanha.day}")
            self.assertEqual(self._titulos(r.context["itens"]), ["Do processo"])
            self.assertEqual(self._grupo(r, "amanha"), ["Do processo"])
            self.assertEqual(self._titulos(r.context["itens_dia"]), ["Do processo"])
            self.assertEqual(self._coluna(r, "a_fazer"), ["Do processo"])
            self.assertContains(r, f"?{query[1:]}&visao=calendario")

    def test_filtro_invalido_e_ignorado(self):
        self._afazer("Tarefa", responsavel=self.user)
        r = self._get("?tipo=xpto&natureza=xpto&origem=xpto&processo=abc&ordem=xpto")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._titulos(r.context["itens"]), ["Tarefa"])

    def test_cancelado_fica_fora_das_visoes(self):
        self._afazer("Cancelado", responsavel=self.user, status="cancelado", cancelado_em=timezone.now())
        r = self._get()
        self.assertEqual(r.context["itens"], [])
        self.assertContains(r, "/agenda/cancelados/")

    def test_novo_oferece_os_tipos_e_repassa_processo_do_filtro(self):
        processo = Processo.objects.create(responsavel=self.user, titulo="Processo Novo")
        r = self._get(f"?processo={processo.pk}")
        self.assertContains(r, f"/agenda/novo/?tipo=audiencia&processo={processo.pk}")
        self.assertContains(r, f"/agenda/novo/?tipo=prazo&processo={processo.pk}")


class TestExibicaoPorPermissao(TelaAgendaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "agenda_tela_permissoes"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Agenda Tela Permissoes"
        tenant.slug = "agenda-tela-permissoes"

    def setUp(self):
        super().setUp()
        self.comum = self._user("comum_tela", nivel=NIVEL_SOMENTE_SEUS)
        self.gestor = self._user("gestor_tela", gerir=True, atribuir=True)

    def test_pessoa_e_delegados_so_para_quem_pode(self):
        self.client.force_login(self.comum)
        r = self._get()
        self.assertNotIn("usuarios_outros", r.context)
        self.assertNotContains(r, 'name="usuario"')
        self.assertNotContains(r, "Delegados por mim")
        self.assertNotContains(r, 'name="escopo"')

        self.client.force_login(self.gestor)
        r = self._get()
        self.assertContains(r, 'name="usuario"')
        self.assertContains(r, "Delegados por mim")
        self.assertContains(r, 'name="escopo"')

    def test_pessoa_mostra_agenda_do_outro_e_trava_o_novo(self):
        self._afazer("Do comum", responsavel=self.comum)
        self.client.force_login(self.gestor)
        r = self._get(f"?usuario={self.comum.pk}")
        self.assertEqual(self._titulos(r.context["itens"]), ["Do comum"])
        self.assertContains(r, f"/agenda/novo/?para_usuario={self.comum.pk}")

        self.client.force_login(self.comum)
        outro = self._afazer("Do gestor", responsavel=self.gestor)
        r = self._get(f"?usuario={self.gestor.pk}")
        self.assertIsNone(r.context["usuario_filtro"])
        self.assertNotIn(outro, r.context["itens"])

    def _delegar_com_convite(self, titulo):
        item = self._afazer(titulo, responsavel=self.comum, atribuidor=self.gestor)
        item.convite_delegacao = criar_convite_delegacao(self.gestor, self.comum, item)
        item.save(update_fields=["convite_delegacao"])
        return item

    def test_delegados_por_mim_inclui_convite_pendente_e_exclui_os_meus(self):
        delegado = self._delegar_com_convite("Delegado")
        self._afazer("Meu", responsavel=self.gestor, atribuidor=self.gestor)
        self.client.force_login(self.gestor)
        r = self._get("?delegados=1")
        self.assertEqual(r.context["itens"], [delegado])
        self.assertContains(r, "Convite pendente")

    def test_convites_recebidos_em_aviso_fixo_com_contador(self):
        self.client.force_login(self.comum)
        self.assertNotContains(self._get(), "data-convites-recebidos")

        convite = self._delegar_com_convite("Convite tela").convite_delegacao
        r = self._get()
        self.assertContains(r, "Convites recebidos (1)")
        self.assertContains(r, "Tarefa: Convite tela")
        self.assertContains(r, f"/agenda/convites/{convite.pk}/responder/")
        self.assertContains(r, 'name="justificativa"')
        self.assertEqual(r.context["itens"], [])

    def test_acoes_do_card_so_para_o_responsavel(self):
        proprio = self._afazer("Próprio", responsavel=self.comum)
        alheio = self._evento("Alheio", responsavel=self.gestor, inicio=self._em(1))
        ParticipanteItemAgenda.objects.create(item=alheio, usuario=self.comum)
        self.client.force_login(self.comum)
        r = self._get()
        self.assertEqual({i.titulo for i in r.context["itens"]}, {"Próprio", "Alheio"})
        self.assertContains(r, f"/agenda/{proprio.pk}/concluir/")
        self.assertContains(r, f"/agenda/{proprio.pk}/reatribuir/")
        self.assertNotContains(r, f"/agenda/{alheio.pk}/concluir/")
        self.assertNotContains(r, f"/agenda/{alheio.pk}/editar/")
        self.assertContains(r, f"/agenda/{alheio.pk}/confirmar-presenca/")

    def test_menu_agenda_juridica_e_redirect_de_tarefas(self):
        self.client.force_login(self.comum)
        r = self._get()
        self.assertContains(r, "Agenda Jurídica")
        self.assertNotContains(r, "<span>Tarefas</span>")
        r = self.client.get("/tarefas/?usuario=3", HTTP_HOST=self.http_host)
        self.assertRedirects(r, "/agenda/?usuario=3", fetch_redirect_response=False)
