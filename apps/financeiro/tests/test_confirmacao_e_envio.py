"""
Confirmação e envio em andamento (UI 3/6): o lançamento é salvo por um
formulário POST sob o guarda de envio único de static/js/formularios.js
(comportamento do duplo clique coberto em tests/js/formularios.test.js), e a
exclusão usa o diálogo compartilhado em vez da caixa nativa do navegador.
"""

from apps.financeiro.tests.test_lancamento_formulario import LancamentoFormularioBase


class TestConfirmacaoEEnvio(LancamentoFormularioBase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_confirmacao_envio"

    def test_formulario_de_lancamento_e_post_sob_o_guarda_de_envio(self):
        r = self.client.get("/financeiro/lancamentos/novo/", HTTP_HOST=self.http_host)

        self.assertContains(r, '<script src="/static/js/formularios.js"></script>', count=1)
        self.assertContains(r, 'method="post"')
        self.assertContains(r, "Criar lançamento")

    def test_excluir_lancamento_usa_o_dialogo_compartilhado(self):
        self._lancamento(descricao="Honorário março")

        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)

        self.assertContains(r, "data-dialogo-confirmacao", count=1)
        self.assertContains(r, 'data-confirmar="Excluir lançamento?"')
        self.assertContains(r, "Honorário março — vencimento")
        self.assertNotContains(r, "confirm(")
