"""
Testes da contagem de solicitações pendentes na barra de abas do
Financeiro (templatetag `abas_financeiro`; regra em docs/modules/financeiro.md).

Cobre: estados que contam, tipos, total do escritório (não só do usuário),
cores do número, presença em todas as telas do módulo e não vazamento
para quem não tem acesso ao caixa geral.
"""

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.permissoes_constants import NIVEL_DADOS_TODOS, NIVEL_SOLICITACOES
from apps.financeiro.tests.test_solicitacoes import SolicitacaoFinanceiraBase

ROTULO_ZERO = "(0)"
COR_DESTAQUE = "bg-yellow-100"
COR_ZERO = "bg-gray-100 text-gray-500"

URLS_DO_MODULO = [
    "financeiro:index",
    "financeiro:grafico",
    "financeiro:custas",
    "financeiro:honorarios_lista",
    "financeiro:solicitacoes_lista",
]


class TestContagemSolicitacoesPendentes(SolicitacaoFinanceiraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_contagem"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Contagem"
        tenant.slug = "solicitacoes-contagem"

    def setUp(self):
        super().setUp()
        self.gestor = self._user("gestor_contagem")
        self._conceder_modulo(self.gestor, nivel=NIVEL_DADOS_TODOS)
        self.solicitante = self._user("solicitante_contagem")
        self._conceder_modulo(self.solicitante, nivel=NIVEL_SOLICITACOES)
        self.client.force_login(self.gestor)

    def _html(self, rota="financeiro:solicitacoes_lista"):
        r = self.client.get(reverse(rota), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        return r.content.decode()

    def _criar(self, status, **kwargs):
        return self._solicitacao(solicitante=self.solicitante, status=status, **kwargs)

    def test_conta_os_tres_estados_abertos(self):
        for status in ("solicitada", "em_analise", "aprovada"):
            self._criar(status)
        html = self._html()
        self.assertIn("(3)", html)
        self.assertIn(COR_DESTAQUE, html)

    def test_nao_conta_rejeitada_nem_paga(self):
        self._criar("rejeitada")
        self._criar("paga")
        self._criar("solicitada")
        self.assertIn("(1)", self._html())

    def test_conta_pagamento_e_reembolso(self):
        self._criar("solicitada", tipo="pagamento")
        self._criar("solicitada", tipo="reembolso")
        self.assertIn("(2)", self._html())

    def test_conta_todas_do_escritorio_nao_so_as_do_usuario(self):
        self._solicitacao(solicitante=self.gestor, status="solicitada")
        self._criar("em_analise")
        self.assertIn("(2)", self._html())

    def test_mostra_zero_em_cinza(self):
        html = self._html()
        self.assertIn(ROTULO_ZERO, html)
        self.assertIn(COR_ZERO, html)
        self.assertNotIn(COR_DESTAQUE, html)

    def test_zero_quando_so_ha_fechadas(self):
        self._criar("paga")
        self.assertIn(ROTULO_ZERO, self._html())

    def test_contagem_aparece_em_todas_as_telas_do_modulo(self):
        self._criar("solicitada")
        self._criar("aprovada")
        for rota in URLS_DO_MODULO:
            with self.subTest(rota=rota):
                self.assertIn("(2)", self._html(rota))

    def test_uma_unica_query_de_contagem_por_requisicao(self):
        self._criar("solicitada")
        with CaptureQueriesContext(connection) as ctx:
            self._html("financeiro:grafico")
        contagens = [q for q in ctx.captured_queries if "COUNT(*)" in q["sql"]
                     and "financeiro_solicitacaofinanceira" in q["sql"]]
        self.assertEqual(len(contagens), 1)

    def test_usuario_sem_acesso_ao_caixa_geral_nao_ve_aba_nem_numero(self):
        self._criar("solicitada")
        self._criar("aprovada")
        self.client.force_login(self.solicitante)
        html = self._html()
        self.assertNotIn(reverse("financeiro:grafico"), html)
        self.assertNotIn(reverse("financeiro:custas"), html)
        self.assertNotIn("(2)", html)
        self.assertNotIn(COR_DESTAQUE, html)
