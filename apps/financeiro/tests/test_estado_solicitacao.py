"""
Testes da cor do estado e da etiqueta "Vencida" de SolicitacaoFinanceira
(components/estado_solicitacao.html; regra em docs/modules/financeiro.md).

Cobre: regra `vencida` no model (limites de data e estados fechados) e a
mesma cor por estado nas três telas que exibem a solicitação.
"""

import datetime

from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.permissoes_constants import (
    MODULO_PROCESSOS,
    NIVEL_DADOS_TODOS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.financeiro.models import SolicitacaoFinanceira
from apps.financeiro.tests.test_solicitacoes import SolicitacaoFinanceiraBase
from apps.accounts.models import PermissaoPapel
from apps.processos.models import Processo

COR_BADGE = {
    "solicitada": "bg-amber-100",
    "em_analise": "bg-amber-100",
    "aprovada": "bg-blue-100",
    "rejeitada": "bg-red-100",
    "paga": "bg-green-100",
}
COR_FAIXA = {
    "solicitada": "bg-amber-400",
    "em_analise": "bg-amber-400",
    "aprovada": "bg-blue-400",
    "rejeitada": "bg-red-400",
    "paga": "bg-green-500",
}


class TestSolicitacaoVencida(SolicitacaoFinanceiraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_vencida"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Vencida"
        tenant.slug = "solicitacoes-vencida"

    def setUp(self):
        super().setUp()
        self.user = self._user("solicitante_vencida")
        self.hoje = timezone.localdate()

    def _com(self, status, vencimento):
        return self._solicitacao(solicitante=self.user, status=status, vencimento=vencimento)

    def test_estados_abertos_com_vencimento_passado_sao_vencidos(self):
        ontem = self.hoje - datetime.timedelta(days=1)
        for status in ("solicitada", "em_analise", "aprovada"):
            with self.subTest(status=status):
                self.assertTrue(self._com(status, ontem).vencida)

    def test_vencimento_hoje_nao_e_vencida(self):
        self.assertFalse(self._com("solicitada", self.hoje).vencida)

    def test_vencimento_futuro_nao_e_vencida(self):
        self.assertFalse(self._com("aprovada", self.hoje + datetime.timedelta(days=1)).vencida)

    def test_sem_vencimento_nunca_e_vencida(self):
        for status in SolicitacaoFinanceira.STATUS_ABERTOS:
            with self.subTest(status=status):
                self.assertFalse(self._com(status, None).vencida)

    def test_paga_ou_rejeitada_com_vencimento_passado_nao_e_vencida(self):
        ontem = self.hoje - datetime.timedelta(days=1)
        for status in ("paga", "rejeitada"):
            with self.subTest(status=status):
                self.assertFalse(self._com(status, ontem).vencida)

    def test_estados_abertos(self):
        self.assertEqual(
            set(SolicitacaoFinanceira.STATUS_ABERTOS), {"solicitada", "em_analise", "aprovada"}
        )


class TestCoresDoEstadoNasTelas(SolicitacaoFinanceiraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "solicitacoes_cores_estado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Solicitacoes Cores Estado"
        tenant.slug = "solicitacoes-cores-estado"

    def setUp(self):
        super().setUp()
        self.user = self._user("gestor_cores")
        papel = self._conceder_modulo(self.user, nivel=NIVEL_DADOS_TODOS)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS
        )
        self.client.force_login(self.user)
        cliente = Cliente.objects.create(
            responsavel=self.user, nome_razao_social="Cliente Cores", tipo="PF"
        )
        self.processo = Processo.objects.create(criado_por=self.user, titulo="Processo Cores")
        self.processo.clientes.add(cliente)
        self.cliente = cliente

    def _solicitacao_no_processo(self, status, **kwargs):
        return self._solicitacao(
            solicitante=self.user,
            tipo="pagamento",
            status=status,
            processo=self.processo,
            cliente=self.cliente,
            **kwargs,
        )

    def _get(self, url):
        r = self.client.get(url, HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        return r.content.decode()

    def test_componente_da_etiqueta_por_estado(self):
        for status, cor in COR_BADGE.items():
            with self.subTest(status=status):
                s = self._solicitacao_no_processo(status)
                html = render_to_string("components/estado_solicitacao.html", {"solicitacao": s})
                self.assertIn(cor, html)
                self.assertNotIn("Vencida", html)

    def test_componente_da_faixa_por_estado(self):
        for status, cor in COR_FAIXA.items():
            with self.subTest(status=status):
                s = self._solicitacao_no_processo(status)
                html = render_to_string(
                    "components/estado_solicitacao.html", {"solicitacao": s, "parte": "faixa"}
                )
                self.assertIn(cor, html)

    def test_lista_do_financeiro_usa_cor_do_estado(self):
        for status in COR_BADGE:
            self._solicitacao_no_processo(status, descricao=f"Custa {status}")
        # A lista separa pendentes/pagas/rejeitadas — junta as três.
        html = "".join(
            self._get(f"/financeiro/solicitacoes/?situacao={situacao}")
            for situacao in ("pendentes", "pagas", "rejeitadas")
        )
        for cor in {*COR_BADGE.values(), *COR_FAIXA.values()}:
            self.assertIn(cor, html)

    def test_detalhe_do_financeiro_usa_cor_do_estado(self):
        for status, cor in COR_BADGE.items():
            with self.subTest(status=status):
                s = self._solicitacao_no_processo(status)
                self.assertIn(cor, self._get(f"/financeiro/solicitacoes/{s.pk}/"))

    def test_aba_custas_do_processo_usa_cor_do_estado(self):
        for status in COR_BADGE:
            self._solicitacao_no_processo(status, descricao=f"Custa {status}")
        html = self._get(f"/processos/{self.processo.pk}/?aba=custas")
        for cor in {*COR_BADGE.values(), *COR_FAIXA.values()}:
            self.assertIn(cor, html)

    def test_vencida_aparece_nas_tres_telas_so_quando_aplicavel(self):
        ontem = timezone.localdate() - datetime.timedelta(days=1)
        vencida = self._solicitacao_no_processo("aprovada", vencimento=ontem)
        paga = self._solicitacao_no_processo("paga", vencimento=ontem)
        urls_lista = ["/financeiro/solicitacoes/", f"/processos/{self.processo.pk}/?aba=custas"]
        for url in urls_lista:
            self.assertEqual(self._get(url).count(">Vencida<"), 1, url)
        self.assertIn(">Vencida<", self._get(f"/financeiro/solicitacoes/{vencida.pk}/"))
        self.assertNotIn(">Vencida<", self._get(f"/financeiro/solicitacoes/{paga.pk}/"))
