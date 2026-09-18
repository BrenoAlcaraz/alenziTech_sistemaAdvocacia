"""
Testes do catálogo de andamentos por área + prazo como atributo
(specs/catalogo-andamentos-por-area-prazo-atributo.md, já implementada e
apagada — comportamento promovido para docs/modules/processos.md).

Cobre: catálogo de `tipo` agrupado por área no formulário, remoção de
"prazo" como tipo selecionável, `data_prazo`/`origem_prazo` no andamento,
recálculo automático de `Processo.prazo_proximo` e a aba "Prazos".
"""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_PROCESSOS_ANDAMENTO_ADICIONAR,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)
from apps.processos.models import MovimentacaoProcessual, Processo
from apps.processos.services import recalcular_prazo_proximo


class MovimentacoesBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass", is_active=True)

    def _autorizar(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS
        )
        HabilitacaoPapel.objects.create(
            papel=papel,
            tipo_conta=None,
            modulo=MODULO_PROCESSOS,
            item=HAB_PROCESSOS_ANDAMENTO_ADICIONAR,
            ativo=True,
        )
        return papel

    def _processo(self, *, responsavel, **kwargs):
        defaults = {"titulo": "Processo Teste Movimentações"}
        defaults.update(kwargs)
        return Processo.objects.create(responsavel=responsavel, **defaults)


class TestCatalogoPorArea(MovimentacoesBase):
    """Catálogo agrupado exibido no <select> de tipo do formulário."""

    @classmethod
    def get_test_schema_name(cls):
        return "movimentacoes_catalogo_area"

    def setUp(self):
        super().setUp()
        self.user = self._user("resp_catalogo")
        self._autorizar(self.user)
        self.client.force_login(self.user)

    def test_processo_civel_mostra_catalogo_civel_e_genericos(self):
        processo = self._processo(responsavel=self.user, area_direito="CÍVEL")
        r = self.client.get(f"/processos/{processo.pk}/?aba=andamentos", HTTP_HOST=self.http_host)
        html = r.content.decode()
        self.assertIn('value="peticao_inicial"', html)
        self.assertIn('value="despacho"', html)
        self.assertNotIn('value="reclamacao_trabalhista"', html)
        self.assertNotIn('value="inquerito_policial_termo_circunstanciado"', html)

    def test_processo_trabalhista_mostra_catalogo_trabalhista_e_genericos(self):
        processo = self._processo(responsavel=self.user, area_direito="TRABALHISTA")
        r = self.client.get(f"/processos/{processo.pk}/?aba=andamentos", HTTP_HOST=self.http_host)
        html = r.content.decode()
        self.assertIn('value="reclamacao_trabalhista"', html)
        self.assertIn('value="despacho"', html)
        self.assertNotIn('value="peticao_inicial"', html)

    def test_processo_penal_mostra_catalogo_penal_e_genericos(self):
        processo = self._processo(responsavel=self.user, area_direito="CRIMINAL")
        r = self.client.get(f"/processos/{processo.pk}/?aba=andamentos", HTTP_HOST=self.http_host)
        html = r.content.decode()
        self.assertIn('value="inquerito_policial_termo_circunstanciado"', html)
        self.assertIn('value="pericia"', html)
        self.assertNotIn('value="peticao_inicial"', html)

    def test_area_sem_catalogo_proprio_cai_no_civel(self):
        processo = self._processo(responsavel=self.user, area_direito="CONSUMIDOR")
        r = self.client.get(f"/processos/{processo.pk}/?aba=andamentos", HTTP_HOST=self.http_host)
        html = r.content.decode()
        self.assertIn('value="peticao_inicial"', html)

    def test_prazo_nao_e_mais_opcao_de_tipo(self):
        processo = self._processo(responsavel=self.user, area_direito="CÍVEL")
        r = self.client.get(f"/processos/{processo.pk}/?aba=andamentos", HTTP_HOST=self.http_host)
        html = r.content.decode()
        self.assertNotIn('value="prazo"', html)

    def test_submeter_tipo_fora_do_catalogo_da_area_e_rejeitado(self):
        # Cível não expõe o catálogo trabalhista — POST forjado com um
        # valor de outra área não pode ser aceito (choices do form são
        # escopadas por processo em MovimentacaoProcessualForm.__init__).
        processo = self._processo(responsavel=self.user, area_direito="CÍVEL")
        r = self.client.post(
            f"/processos/{processo.pk}/movimentacoes/nova/",
            {"tipo": "reclamacao_trabalhista", "data": "2026-03-05T10:00", "descricao": "x"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(processo.movimentacoes.count(), 0)


class TestAdicionarMovimentacaoComPrazo(MovimentacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "movimentacoes_adicionar_prazo"

    def setUp(self):
        super().setUp()
        self.user = self._user("resp_adicionar")
        self._autorizar(self.user)
        self.client.force_login(self.user)
        self.processo = self._processo(responsavel=self.user, area_direito="CÍVEL")

    def _post(self, **overrides):
        dados = {
            "tipo": "despacho",
            "data": "2026-03-01T09:00",
            "descricao": "Andamento de teste",
        }
        dados.update(overrides)
        return self.client.post(
            f"/processos/{self.processo.pk}/movimentacoes/nova/",
            dados,
            HTTP_HOST=self.http_host,
        )

    def test_cria_andamento_com_data_prazo_e_atualiza_prazo_proximo(self):
        r = self._post(data_prazo="2026-03-10")
        self.assertEqual(r.status_code, 302)
        mov = MovimentacaoProcessual.objects.get(processo=self.processo)
        self.assertEqual(mov.data_prazo, date(2026, 3, 10))
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.prazo_proximo, date(2026, 3, 10))

    def test_cria_andamento_com_origem_prazo(self):
        origem = MovimentacaoProcessual.objects.create(
            processo=self.processo,
            descricao="Despacho determinando prazo de 5 dias",
            tipo="despacho",
        )
        r = self._post(
            tipo="peticao",
            data_prazo="2026-03-15",
            origem_prazo=str(origem.pk),
        )
        self.assertEqual(r.status_code, 302)
        mov = MovimentacaoProcessual.objects.get(processo=self.processo, tipo="peticao")
        self.assertEqual(mov.origem_prazo_id, origem.pk)

    def test_origem_prazo_de_outro_processo_e_rejeitada_e_nao_cria_nada(self):
        # queryset de origem_prazo é escopado ao próprio processo
        # (MovimentacaoProcessualForm.__init__) — um FK forjado apontando
        # para andamento de outro processo precisa falhar a validação,
        # não vazar/associar entre processos (IDOR via FK).
        outro_processo = self._processo(responsavel=self.user, area_direito="CÍVEL")
        andamento_alheio = MovimentacaoProcessual.objects.create(
            processo=outro_processo, descricao="Andamento de outro processo", tipo="despacho"
        )
        r = self._post(data_prazo="2026-03-15", origem_prazo=str(andamento_alheio.pk))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.processo.movimentacoes.count(), 0)

    def test_andamento_sem_data_prazo_nao_altera_prazo_proximo(self):
        self.processo.prazo_proximo = date(2026, 1, 1)
        self.processo.save(update_fields=["prazo_proximo"])
        self._post()
        self.processo.refresh_from_db()
        self.assertIsNone(self.processo.prazo_proximo)

    def test_checkbox_manual_de_prazo_nao_existe_mais_no_form(self):
        r = self.client.get(
            f"/processos/{self.processo.pk}/?aba=andamentos", HTTP_HOST=self.http_host
        )
        self.assertNotIn("atualizar_prazo_proximo", r.content.decode())


class TestAtualizarFaseAndamento(MovimentacoesBase):
    """Painel #2, specs/painel-novos-recortes-analise.md — campo
    'fase do andamento atual' do Processo, preenchido manualmente a
    partir do formulário de andamento, sem sugestão automática."""

    @classmethod
    def get_test_schema_name(cls):
        return "movimentacoes_fase_andamento"

    def setUp(self):
        super().setUp()
        self.user = self._user("resp_fase_andamento")
        self._autorizar(self.user)
        self.client.force_login(self.user)
        self.processo = self._processo(responsavel=self.user, area_direito="CÍVEL")

    def _post(self, **overrides):
        dados = {
            "tipo": "despacho",
            "data": "2026-03-01T09:00",
            "descricao": "Andamento de teste",
        }
        dados.update(overrides)
        return self.client.post(
            f"/processos/{self.processo.pk}/movimentacoes/nova/",
            dados,
            HTTP_HOST=self.http_host,
        )

    def test_atualiza_fase_andamento_quando_informada(self):
        r = self._post(atualizar_fase_andamento="prazo_contestacao")
        self.assertEqual(r.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.fase_andamento_atual, "prazo_contestacao")

    def test_nao_altera_fase_andamento_quando_nao_informada(self):
        self.processo.fase_andamento_atual = "aguardando_sentenca"
        self.processo.save(update_fields=["fase_andamento_atual"])
        self._post()
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.fase_andamento_atual, "aguardando_sentenca")

    def test_campo_nao_e_preenchido_automaticamente_por_tipo_de_andamento(self):
        # Sem sugestão automática — mesmo enviando um `tipo` que "sugeriria"
        # uma fase, o campo só muda se `atualizar_fase_andamento` vier
        # explicitamente no POST.
        r = self._post(tipo="peticao")
        self.assertEqual(r.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.fase_andamento_atual, "")


class TestRecalcularPrazoProximo(MovimentacoesBase):
    """Unidade de apps.processos.services.recalcular_prazo_proximo —
    prazo futuro mais próximo; se todos venceram, o vencido mais
    recente; None sem nenhum data_prazo."""

    @classmethod
    def get_test_schema_name(cls):
        return "movimentacoes_recalcular_prazo"

    def setUp(self):
        super().setUp()
        self.user = self._user("resp_recalculo")
        self.processo = self._processo(responsavel=self.user, area_direito="CÍVEL")

    def _mov(self, data_prazo):
        return MovimentacaoProcessual.objects.create(
            processo=self.processo, descricao="x", tipo="despacho", data_prazo=data_prazo
        )

    def test_sem_nenhum_data_prazo_retorna_none(self):
        self._mov(None)
        self.assertIsNone(recalcular_prazo_proximo(self.processo))

    def test_prefere_o_futuro_mais_proximo(self):
        hoje = date.today()
        self._mov(hoje + timedelta(days=10))
        proximo = self._mov(hoje + timedelta(days=3))
        self._mov(hoje - timedelta(days=1))
        self.assertEqual(recalcular_prazo_proximo(self.processo), proximo.data_prazo)

    def test_todos_vencidos_retorna_o_mais_recente(self):
        hoje = date.today()
        self._mov(hoje - timedelta(days=10))
        mais_recente = self._mov(hoje - timedelta(days=1))
        self.assertEqual(recalcular_prazo_proximo(self.processo), mais_recente.data_prazo)


class TestAbaPrazos(MovimentacoesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "movimentacoes_aba_prazos"

    def setUp(self):
        super().setUp()
        self.user = self._user("resp_aba_prazos")
        self._autorizar(self.user)
        self.client.force_login(self.user)
        self.processo = self._processo(responsavel=self.user, area_direito="CÍVEL")

    def test_estado_vazio_sem_nenhum_prazo(self):
        r = self.client.get(f"/processos/{self.processo.pk}/?aba=prazos", HTTP_HOST=self.http_host)
        self.assertIn("Nenhum prazo cadastrado.", r.content.decode())
        self.assertEqual(r.context["prazos"], [])

    def test_lista_andamentos_com_data_prazo_em_ordem_cronologica(self):
        hoje = date.today()
        MovimentacaoProcessual.objects.create(
            processo=self.processo, descricao="sem prazo", tipo="despacho"
        )
        mov_distante = MovimentacaoProcessual.objects.create(
            processo=self.processo,
            descricao="prazo distante",
            tipo="despacho",
            data_prazo=hoje + timedelta(days=20),
        )
        mov_proximo = MovimentacaoProcessual.objects.create(
            processo=self.processo,
            descricao="prazo próximo",
            tipo="despacho",
            data_prazo=hoje + timedelta(days=2),
        )
        r = self.client.get(f"/processos/{self.processo.pk}/?aba=prazos", HTTP_HOST=self.http_host)
        self.assertEqual(list(r.context["prazos"]), [mov_proximo, mov_distante])

    def test_prazo_vencido_marcado_no_contexto(self):
        vencido = MovimentacaoProcessual.objects.create(
            processo=self.processo,
            descricao="venceu",
            tipo="despacho",
            data_prazo=date.today() - timedelta(days=1),
        )
        self.assertTrue(vencido.prazo_vencido)
