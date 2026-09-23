"""
Código interno C de Cliente (specs/codigos-internos-processo-cliente-usuario.md).
"""

from apps.accounts.permissoes_constants import MODULO_CLIENTES
from apps.clientes.tests.test_escopo import ClientesEscopoBase


class TestCodigoInternoCliente(ClientesEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "codigo_interno_cliente"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_codigo_cliente")

    def _clientes(self, quantidade):
        return [
            self._cliente(responsavel=self.user, nome_razao_social=f"Cliente {i}")
            for i in range(1, quantidade + 1)
        ]

    def test_criacao_atribui_codigos_sequenciais_e_texto_padrao(self):
        primeiro, segundo = self._clientes(2)
        self.assertEqual(primeiro.codigo, "C1")
        self.assertEqual(segundo.codigo, "C2")
        self.assertEqual(str(primeiro), "C1 · Cliente 1")

    def test_numero_excluido_nunca_e_reutilizado(self):
        _, ultimo = self._clientes(2)
        ultimo.delete()
        novo = self._cliente(responsavel=self.user, nome_razao_social="Depois da exclusão")
        self.assertEqual(novo.codigo, "C3")

    def test_busca_por_codigo_e_exata(self):
        self._pp(self._new_papel_autorizado(), MODULO_CLIENTES)
        clientes = self._clientes(10)
        self.client.force_login(self.user)

        resposta = self.client.get("/clientes/", {"busca": "c1"}, HTTP_HOST=self.http_host)
        self.assertEqual(list(resposta.context["clientes"]), [clientes[0]])

    def test_numero_sem_prefixo_nao_e_codigo(self):
        self._pp(self._new_papel_autorizado(), MODULO_CLIENTES)
        self._cliente(responsavel=self.user, nome_razao_social="Sem dígito no nome")
        self.client.force_login(self.user)
        resposta = self.client.get("/clientes/", {"busca": "1"}, HTTP_HOST=self.http_host)
        self.assertEqual(list(resposta.context["clientes"]), [])

    def _new_papel_autorizado(self):
        papel = self._new_papel("Papel código cliente")
        self._assign_papel(self.user, papel)
        return papel
