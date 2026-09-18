"""
Aba "Análise de dados" do Dashboard — filtros, natureza, localidade
hierárquica (Estado→Cidade→Vara com auto-skip), status, patrocínio
best-effort e "Tempo e resultados" —
specs/dashboard-abas-visao-geral-analise-dados.md.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_PAINEL,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.processos.models import MovimentacaoProcessual, ParteProcesso, Processo


class AnaliseBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("analista", password="testpass")

    def _autorizar_processos(self, nivel):
        papel = PapelAcesso.objects.create(nome=f"Papel Analise {nivel}", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        for modulo in (MODULO_PAINEL, MODULO_PROCESSOS):
            PermissaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=modulo, ativo=True, nivel=nivel
            )
        return papel

    def _processo(self, titulo, *, responsavel=None, cliente=None, **extra):
        processo = Processo.objects.create(
            titulo=titulo, responsavel=responsavel or self.usuario, **extra
        )
        if cliente is not None:
            processo.clientes.add(cliente)
        return processo

    def _get(self, **params):
        return self.client.get("/analise/", params, HTTP_HOST=self.http_host)


class TestAnaliseAutorizacao(AnaliseBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_autorizacao"

    def test_sem_modulo_processos_nega_acesso(self):
        self.client.force_login(self.usuario)
        resposta = self._get()
        self.assertEqual(resposta.status_code, 403)


class TestAnaliseNaturezaEStatus(AnaliseBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_natureza"

    def setUp(self):
        super().setUp()
        self._autorizar_processos(NIVEL_TODOS)
        self.client.force_login(self.usuario)

    def test_agrupa_por_natureza_e_status(self):
        self._processo("Cível 1", area_direito="CÍVEL", status="ativo")
        self._processo("Cível 2", area_direito="CÍVEL", status="suspenso")
        self._processo("Trabalhista 1", area_direito="TRABALHISTA", status="ativo")

        resposta = self._get()

        self.assertEqual(resposta.status_code, 200)
        natureza = {b["label"]: b["total"] for b in resposta.context["natureza_barras"]}
        self.assertEqual(natureza["Cível"], 2)
        self.assertEqual(natureza["Trabalhista"], 1)
        status = {b["label"]: b["total"] for b in resposta.context["status_barras"]}
        self.assertEqual(status["Ativo"], 2)
        self.assertEqual(status["Suspenso"], 1)

    def test_inclui_processo_arquivado_diferente_da_visao_geral(self):
        self._processo("Arquivado antigo", status="arquivado")

        resposta = self._get()

        self.assertEqual(resposta.context["total_processos"], 1)


class TestAnaliseEscopo(AnaliseBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_escopo"

    def test_somente_seus_nao_mostra_seletor_e_filtra_por_responsavel(self):
        self._autorizar_processos(NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.usuario)
        outro = User.objects.create_user("outro_resp", password="testpass")
        self._processo("Meu processo")
        self._processo("Processo de outro", responsavel=outro)

        resposta = self._get()

        self.assertFalse(resposta.context["mostrar_seletor_escopo"])
        self.assertEqual(resposta.context["total_processos"], 1)

    def test_todos_com_filtro_somente_meus_via_query_param(self):
        self._autorizar_processos(NIVEL_TODOS)
        self.client.force_login(self.usuario)
        outro = User.objects.create_user("outro_resp2", password="testpass")
        self._processo("Meu processo")
        self._processo("Processo de outro", responsavel=outro)

        resposta_todos = self._get()
        self.assertEqual(resposta_todos.context["total_processos"], 2)

        resposta_meus = self._get(escopo="somente_seus")
        self.assertEqual(resposta_meus.context["total_processos"], 1)


class TestAnaliseLocalidade(AnaliseBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_localidade"

    def setUp(self):
        super().setUp()
        self._autorizar_processos(NIVEL_TODOS)
        self.client.force_login(self.usuario)

    def test_pula_nivel_estado_quando_so_ha_uma_opcao(self):
        self._processo("P1", estado="SP", cidade="Campinas", vara="1ª Vara Cível")
        self._processo("P2", estado="SP", cidade="São Paulo", vara="2ª Vara Cível")

        resposta = self._get()

        self.assertFalse(resposta.context["loc_mostrando_estados"])
        self.assertTrue(resposta.context["loc_mostrando_cidades"])
        self.assertEqual(resposta.context["loc_estado_ativo"], "SP")

    def test_mostra_estados_quando_ha_mais_de_um(self):
        self._processo("P1", estado="SP")
        self._processo("P2", estado="RJ")

        resposta = self._get()

        self.assertTrue(resposta.context["loc_mostrando_estados"])
        opcoes = {o["valor"]: o["total"] for o in resposta.context["loc_estado_opcoes"]}
        self.assertEqual(opcoes["SP"], 1)
        self.assertEqual(opcoes["RJ"], 1)

    def test_drill_down_ate_vara_por_query_param(self):
        self._processo("P1", estado="SP", cidade="Campinas", vara="1ª Vara Cível")
        self._processo("P2", estado="RJ", cidade="Niterói", vara="3ª Vara Cível")

        resposta = self._get(loc_estado="SP")

        self.assertTrue(resposta.context["loc_mostrando_varas"])
        varas = {b["label"]: b["total"] for b in resposta.context["loc_vara_barras"]}
        self.assertEqual(varas["1ª Vara Cível"], 1)


class TestAnaliseFaseEFaseAndamento(AnaliseBase):
    """Painel #2 e #3, specs/painel-novos-recortes-analise.md."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_fase"

    def setUp(self):
        super().setUp()
        self._autorizar_processos(NIVEL_TODOS)
        self.client.force_login(self.usuario)

    def test_agrupa_por_fase_do_processo(self):
        self._processo("P1", fase="conhecimento")
        self._processo("P2", fase="conhecimento")
        self._processo("P3", fase="recursal")

        resposta = self._get()

        fase = {b["label"]: b["total"] for b in resposta.context["fase_barras"]}
        self.assertEqual(fase["Conhecimento"], 2)
        self.assertEqual(fase["Recursal"], 1)

    def test_agrupa_por_fase_do_andamento_atual_incluindo_nao_informado(self):
        self._processo("P1", fase_andamento_atual="prazo_contestacao")
        self._processo("P2", fase_andamento_atual="prazo_contestacao")
        self._processo("P3")  # sem fase de andamento preenchida

        resposta = self._get()

        fase_andamento = {b["label"]: b["total"] for b in resposta.context["fase_andamento_barras"]}
        self.assertEqual(fase_andamento["Em prazo de contestação"], 2)
        self.assertEqual(fase_andamento["Não informado"], 1)

    def test_fase_andamento_e_preenchida_manualmente_sem_sugestao_automatica(self):
        processo = self._processo("P1")
        self.assertEqual(processo.fase_andamento_atual, "")

        processo.fase_andamento_atual = "aguardando_sentenca"
        processo.save(update_fields=["fase_andamento_atual"])
        processo.refresh_from_db()

        self.assertEqual(processo.fase_andamento_atual, "aguardando_sentenca")


class TestAnaliseClientesPorLocalidade(AnaliseBase):
    """Painel #1, specs/painel-novos-recortes-analise.md — espelha o
    padrão de "Processos por localidade" (TestAnaliseLocalidade), mas
    agrupa Clientes (Estado→Cidade→Bairro) restritos aos vinculados aos
    processos já filtrados pelo escopo/filtros da página."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_clientes_localidade"

    def setUp(self):
        super().setUp()
        self._autorizar_processos(NIVEL_TODOS)
        self.client.force_login(self.usuario)

    def _cliente(self, nome, **extra):
        return Cliente.objects.create(
            nome_razao_social=nome, tipo="PF", responsavel=self.usuario, **extra
        )

    def test_pula_nivel_estado_quando_so_ha_uma_opcao(self):
        c1 = self._cliente("C1", estado="SP", cidade="Campinas", bairro="Centro")
        c2 = self._cliente("C2", estado="SP", cidade="São Paulo", bairro="Pinheiros")
        self._processo("P1", cliente=c1)
        self._processo("P2", cliente=c2)

        resposta = self._get()

        self.assertFalse(resposta.context["cloc_mostrando_estados"])
        self.assertTrue(resposta.context["cloc_mostrando_cidades"])
        self.assertEqual(resposta.context["cloc_estado_ativo"], "SP")

    def test_mostra_estados_quando_ha_mais_de_um(self):
        c1 = self._cliente("C1", estado="SP")
        c2 = self._cliente("C2", estado="RJ")
        self._processo("P1", cliente=c1)
        self._processo("P2", cliente=c2)

        resposta = self._get()

        self.assertTrue(resposta.context["cloc_mostrando_estados"])
        opcoes = {o["valor"]: o["total"] for o in resposta.context["cloc_estado_opcoes"]}
        self.assertEqual(opcoes["SP"], 1)
        self.assertEqual(opcoes["RJ"], 1)

    def test_drill_down_ate_bairro_por_query_param(self):
        c1 = self._cliente("C1", estado="SP", cidade="Campinas", bairro="Centro")
        c2 = self._cliente("C2", estado="RJ", cidade="Niterói", bairro="Icaraí")
        self._processo("P1", cliente=c1)
        self._processo("P2", cliente=c2)

        resposta = self._get(cloc_estado="SP")

        self.assertTrue(resposta.context["cloc_mostrando_bairros"])
        bairros = {b["label"]: b["total"] for b in resposta.context["cloc_bairro_barras"]}
        self.assertEqual(bairros["Centro"], 1)

    def test_cliente_sem_processo_no_escopo_nao_aparece(self):
        self._cliente("Sem processo algum", estado="BA")
        c1 = self._cliente("Com processo", estado="MG")
        self._processo("P1", cliente=c1)

        resposta = self._get()

        self.assertEqual(resposta.context["total_clientes_localidade"], 1)

    def test_respeita_escopo_somente_meus(self):
        outro = User.objects.create_user("outro_resp3", password="testpass")
        cliente_meu = self._cliente("Meu cliente", estado="MG")
        cliente_de_outro = self._cliente("Cliente de outro", estado="BA")
        self._processo("Meu processo", cliente=cliente_meu)
        self._processo("Processo de outro", responsavel=outro, cliente=cliente_de_outro)

        resposta = self._get(escopo="somente_seus")

        self.assertEqual(resposta.context["total_clientes_localidade"], 1)

    def test_mesmo_cliente_em_varios_processos_conta_uma_vez(self):
        cliente = self._cliente("C1", estado="SP")
        self._processo("P1", cliente=cliente)
        self._processo("P2", cliente=cliente)

        resposta = self._get()

        self.assertEqual(resposta.context["total_clientes_localidade"], 1)


class TestAnalisePatrocinio(AnaliseBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_patrocinio"

    def setUp(self):
        super().setUp()
        self._autorizar_processos(NIVEL_TODOS)
        self.client.force_login(self.usuario)

    def test_casa_por_cpf_cnpj_e_identifica_polo(self):
        cliente = Cliente.objects.create(
            nome_razao_social="Cliente Autor", tipo="PF",
            cpf_cnpj="111.111.111-11", responsavel=self.usuario,
        )
        processo = self._processo("Processo com parte casada", cliente=cliente)
        ParteProcesso.objects.create(
            processo=processo, papel="autor", nome="Cliente Autor", cpf_cnpj="111.111.111-11",
        )

        resposta = self._get()

        barras = {b["valor"]: b["total"] for b in resposta.context["patrocinio_barras"]}
        self.assertEqual(barras.get("polo_ativo"), 1)

    def test_sem_correspondencia_entra_como_nao_identificado(self):
        self._processo("Processo sem parte casada")

        resposta = self._get()

        barras = {b["valor"]: b["total"] for b in resposta.context["patrocinio_barras"]}
        self.assertEqual(barras.get("__na__"), 1)


class TestAnaliseTempoEResultados(AnaliseBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_dashboard_analise_tempo"

    def setUp(self):
        super().setUp()
        self._autorizar_processos(NIVEL_TODOS)
        self.client.force_login(self.usuario)

    def test_sem_processos_elegiveis_nao_quebra(self):
        resposta = self._get()

        self.assertEqual(resposta.status_code, 200)
        self.assertIsNone(resposta.context["tempo_vida_medio"])
        self.assertIsNone(resposta.context["tempo_entre_andamentos"])

    def test_contagem_de_julgados(self):
        self._processo("Ganho", status="encerrado", resultado_sentenca="procedente")
        self._processo("Ganho parcial", status="encerrado", resultado_sentenca="parcialmente_procedente")
        self._processo("Perdido", status="encerrado", resultado_sentenca="improcedente")
        self._processo("Ainda sem sentença", status="ativo")

        resposta = self._get()

        self.assertEqual(resposta.context["julgados_procedente"], 1)
        self.assertEqual(resposta.context["julgados_parcial"], 1)
        self.assertEqual(resposta.context["julgados_improcedente"], 1)

    def test_tempo_medio_entre_andamentos(self):
        processo = self._processo("Com andamentos", status="ativo")
        agora = timezone.now()
        MovimentacaoProcessual.objects.create(processo=processo, data=agora - timedelta(days=20))
        MovimentacaoProcessual.objects.create(processo=processo, data=agora - timedelta(days=10))
        MovimentacaoProcessual.objects.create(processo=processo, data=agora)

        resposta = self._get()

        self.assertEqual(resposta.context["tempo_entre_andamentos"], "10 dias")
