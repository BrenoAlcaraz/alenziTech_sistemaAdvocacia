"""Lista de Clientes em tabela: busca, paginação e escopo
(specs/ui-05-shell-e-listas.md)."""

from apps.accounts.permissoes_constants import MODULO_CLIENTES, NIVEL_SOMENTE_SEUS
from apps.clientes.models import Cliente
from apps.processos.models import Processo

from .test_escopo import ClientesEscopoBase


class TestListaClientesTabela(ClientesEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "ui05_lista_clientes"

    def setUp(self):
        super().setUp()
        self.user = self._user("clientes_somente_seus")
        self.outro = self._user("clientes_alheio")
        papel = self._new_papel("Clientes só seus")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_CLIENTES, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(self.user)

    def _em_massa(self, responsavel, quantidade, *, inicio):
        Cliente.objects.bulk_create([
            Cliente(
                nome_razao_social=f"Cliente {inicio + i:04d}",
                tipo="PF",
                responsavel=responsavel,
                numero_interno=80000 + inicio + i,
            )
            for i in range(quantidade)
        ])

    def _get(self, query=""):
        return self.client.get(f"/clientes/{query}", HTTP_HOST=self.http_host)

    def test_busca_por_cpf_com_ou_sem_pontuacao_e_por_codigo(self):
        cliente = Cliente.objects.create(
            nome_razao_social="Joana Prado", tipo="PF", cpf_cnpj="123.456.789-09",
            responsavel=self.user,
        )
        # Texto com número não vira busca por dígitos do documento.
        Cliente.objects.create(nome_razao_social="Outro", tipo="PF", responsavel=self.user, cpf_cnpj="912.000.000-00")
        self.assertEqual(list(self._get("?busca=Rua 12").context["clientes"]), [])
        for termo in ("123.456", "12345678909", "joana", cliente.codigo):
            with self.subTest(termo=termo):
                self.assertEqual(list(self._get(f"?busca={termo}").context["clientes"]), [cliente])

    def test_somente_seus_nao_ve_alheios_na_contagem_nem_paginacao(self):
        self._em_massa(self.user, 55, inicio=1)
        self._em_massa(self.outro, 55, inicio=1001)
        pagina = self._get("?busca=Cliente").context["clientes"]
        self.assertEqual(pagina.paginator.count, 55)
        segunda = self._get("?busca=Cliente&ordem=-nome&pagina=2").context["clientes"]
        self.assertEqual(len(segunda), 5)
        self.assertEqual(
            {c.responsavel_id for c in list(pagina) + list(segunda)}, {self.user.pk}
        )

    def test_processos_ativos_ignora_arquivados(self):
        cliente = Cliente.objects.create(nome_razao_social="Com processos", tipo="PF", responsavel=self.user)
        for status in ("ativo", "suspenso", "arquivado"):
            Processo.objects.create(titulo=status, responsavel=self.user, status=status).clientes.add(cliente)
        linha = self._get().context["clientes"][0]
        self.assertEqual(linha.processos_ativos, 2)
