"""
Testes dos helpers de filtro de Processo por Cliente usados pelos
formulários de financeiro, tarefas e agenda (specs/filtro-processo-por-cliente.md).
"""

from apps.processos.services import processo_pertence_ao_cliente, processos_do_cliente
from apps.processos.tests.test_escopo import ProcessosEscopoBase


class TestProcessosDoCliente(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "filtro_processos_do_cliente"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_filtro")
        self.cliente_a = self._cliente(self.user, "Cliente A")
        self.cliente_b = self._cliente(self.user, "Cliente B")
        self.processo_a = self._processo(self.user, self.cliente_a, "Processo A")
        self.processo_arquivado = self._processo(
            self.user, self.cliente_a, "Processo Arquivado", status="arquivado"
        )
        self.processo_b = self._processo(self.user, self.cliente_b, "Processo B")

    def test_retorna_apenas_processos_ativos_do_cliente(self):
        resultado = list(processos_do_cliente(self.cliente_a.id))
        self.assertEqual(resultado, [self.processo_a])

    def test_ignora_processo_arquivado(self):
        resultado = list(processos_do_cliente(self.cliente_a.id))
        self.assertNotIn(self.processo_arquivado, resultado)

    def test_cliente_sem_id_retorna_vazio(self):
        self.assertFalse(processos_do_cliente(None).exists())
        self.assertFalse(processos_do_cliente("").exists())

    def test_cliente_id_invalido_retorna_vazio_sem_lancar_erro(self):
        self.assertFalse(processos_do_cliente("abc").exists())


class TestProcessoPertenceAoCliente(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "filtro_processo_pertence_cliente"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_pertence")
        self.cliente_a = self._cliente(self.user, "Cliente A")
        self.cliente_b = self._cliente(self.user, "Cliente B")
        self.processo_a = self._processo(self.user, self.cliente_a, "Processo A")

    def test_verdadeiro_quando_cliente_ausente(self):
        self.assertTrue(processo_pertence_ao_cliente(None, self.processo_a))

    def test_verdadeiro_quando_processo_ausente(self):
        self.assertTrue(processo_pertence_ao_cliente(self.cliente_a, None))

    def test_verdadeiro_quando_processo_e_do_cliente(self):
        self.assertTrue(processo_pertence_ao_cliente(self.cliente_a, self.processo_a))

    def test_falso_quando_processo_e_de_outro_cliente(self):
        self.assertFalse(processo_pertence_ao_cliente(self.cliente_b, self.processo_a))
