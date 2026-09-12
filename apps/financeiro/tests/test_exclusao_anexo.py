"""
Testes de limpeza de arquivo ao excluir SolicitacaoFinanceira com anexo.

Não há hoje uma view de exclusão de solicitação financeira nas telas do
módulo, mas o model tem FileField e é acessível pelo Django Admin — o
signal post_delete (apps/financeiro/signals.py) cobre qualquer caminho
de exclusão, não só uma view futura.

Reaproveita a fixture de apps/financeiro/tests/test_solicitacoes.py.
"""

import os

from apps.financeiro.models import SolicitacaoFinanceira
from apps.financeiro.tests.test_solicitacoes import SolicitacaoFinanceiraBase


class TestExclusaoDeAnexoDeSolicitacao(SolicitacaoFinanceiraBase):
    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_anexo_exclusao"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Financeiro Anexo Exclusao"
        tenant.slug = "financeiro-anexo-exclusao"

    def setUp(self):
        super().setUp()
        self.solicitante = self._user("solicitante_exclusao")

    def test_excluir_solicitacao_remove_arquivo_do_storage(self):
        solicitacao = self._solicitacao(solicitante=self.solicitante)
        caminho_arquivo = solicitacao.anexo.path
        self.assertTrue(os.path.exists(caminho_arquivo))

        solicitacao.delete()

        self.assertFalse(SolicitacaoFinanceira.objects.filter(pk=solicitacao.pk).exists())
        self.assertFalse(os.path.exists(caminho_arquivo))
