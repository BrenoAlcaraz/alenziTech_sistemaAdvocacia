"""
Testes do padrão "Código · Título — Número" + busca (combobox) em todo campo de
seleção de Processo do sistema (specs/processos-seletor-busca-formularios.md).
"""

from apps.agenda.forms import CompromissoForm
from apps.financeiro.forms import (
    CreditarCustaForm,
    CustaJudicialForm,
    HonorarioForm,
    LancamentoFinanceiroForm,
    SolicitacaoFinanceiraForm,
)
from apps.processos.forms import (
    AdicionarApensoForm,
    IntimacaoForm,
    ProcessoChoiceField,
)
from apps.processos.models import Processo
from apps.processos.services import rotulo_processo
from apps.processos.tests.test_escopo import ProcessosEscopoBase
from apps.tarefas.forms import TarefaForm


class TestRotuloProcesso(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "seletor_processo_rotulo"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_rotulo")

    def test_com_numero_exibe_codigo_titulo_traco_numero(self):
        processo = self._processo(self.user, None, "Ação de Cobrança")
        Processo.objects.filter(pk=processo.pk).update(numero="0000001-00.2026.8.00.0001")
        processo.refresh_from_db()
        self.assertEqual(rotulo_processo(processo), "P1 · Ação de Cobrança — 0000001-00.2026.8.00.0001")

    def test_sem_numero_exibe_codigo_e_titulo(self):
        processo = self._processo(self.user, None, "Ação sem número ainda")
        self.assertEqual(rotulo_processo(processo), "P1 · Ação sem número ainda")


class TestSeletorProcessoEmTodosOsFormularios(ProcessosEscopoBase):
    """Cobre o critério de aceite: nenhum campo de Processo continua sendo
    um <select> sem busca, em nenhum formulário do sistema."""

    @classmethod
    def get_test_schema_name(cls):
        return "seletor_processo_formularios"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_seletor")
        self.cliente = self._cliente(self.user, "Cliente seletor")
        self.processo = self._processo(self.user, self.cliente, "Processo seletor")

    def _assert_campo_busca(self, form, campo):
        field = form.fields[campo]
        self.assertIsInstance(field, ProcessoChoiceField)
        self.assertEqual(field.widget.attrs.get("data-processo-busca"), "1")
        self.assertEqual(field.label_from_instance(self.processo), rotulo_processo(self.processo))

    def test_intimacao(self):
        form = IntimacaoForm(processos_queryset=Processo.objects.all())
        self._assert_campo_busca(form, "processo")

    def test_adicionar_apenso(self):
        form = AdicionarApensoForm(
            processo_origem=self.processo,
            processos_queryset=Processo.objects.all(),
        )
        self._assert_campo_busca(form, "processo_apenso")

    def test_lancamento_financeiro(self):
        self._assert_campo_busca(LancamentoFinanceiroForm(), "processo")

    def test_custa_judicial(self):
        self._assert_campo_busca(CustaJudicialForm(), "processo")

    def test_creditar_custa(self):
        self._assert_campo_busca(CreditarCustaForm(cliente=self.cliente), "processo")

    def test_honorario(self):
        self._assert_campo_busca(HonorarioForm(), "processo")

    def test_solicitacao_financeira(self):
        self._assert_campo_busca(SolicitacaoFinanceiraForm(), "processo")

    def test_compromisso_agenda(self):
        self._assert_campo_busca(CompromissoForm(), "processo")

    def test_tarefa(self):
        self._assert_campo_busca(TarefaForm(), "processo")
