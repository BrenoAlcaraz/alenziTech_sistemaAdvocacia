"""
Ajustes da revisão de 2026-09-19 em Clientes: nome em maiúsculas, nome
fantasia e empresa estrangeira (PJ), RG sem máscara e "Clientes
relacionados" também por processo em comum.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.clientes.forms import ClienteForm
from apps.clientes.models import Cliente
from apps.clientes.services import clientes_relacionados
from apps.processos.models import Processo


class TestFormularioAjustes(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_ajustes_revisao"

    def _dados_pj(self, **overrides):
        dados = {
            "tipo": "PJ",
            "nome_razao_social": "Empresa Teste LTDA",
            "nome_fantasia": "Loja Teste",
            "cpf_cnpj": "11.222.333/0001-81",
        }
        dados.update(overrides)
        return dados

    def test_nome_do_cliente_e_gravado_em_maiusculas(self):
        form = ClienteForm(data={"tipo": "PF", "nome_razao_social": "  maria da Silva "})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["nome_razao_social"], "MARIA DA SILVA")

    def test_pj_guarda_nome_fantasia_em_maiusculas(self):
        form = ClienteForm(data=self._dados_pj())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["nome_fantasia"], "LOJA TESTE")

    def test_pf_descarta_nome_fantasia(self):
        form = ClienteForm(data={
            "tipo": "PF", "nome_razao_social": "Fulano", "nome_fantasia": "Qualquer",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["nome_fantasia"], "")

    def test_pj_estrangeira_aceita_documento_que_nao_e_cnpj(self):
        form = ClienteForm(data=self._dados_pj(estrangeiro="on", cpf_cnpj="DE-123456789"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["estrangeiro"])

    def test_pj_brasileira_continua_validando_cnpj(self):
        form = ClienteForm(data=self._dados_pj(cpf_cnpj="DE-123456789"))
        self.assertFalse(form.is_valid())
        self.assertIn("cpf_cnpj", form.errors)

    def test_rg_e_guardado_como_digitado_sem_formatacao(self):
        form = ClienteForm(data={
            "tipo": "PF", "nome_razao_social": "Fulano", "rg": "MG-12.345.678",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["rg"], "MG-12.345.678")


class TestClientesRelacionadosPorProcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_relacionados_proc"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="resp_rel", password="x")

    def _cliente(self, nome, **kw):
        return Cliente.objects.create(nome_razao_social=nome, responsavel=self.user, **kw)

    def test_clientes_no_mesmo_processo_sao_relacionados(self):
        a, b, c = self._cliente("A"), self._cliente("B"), self._cliente("C")
        processo = Processo.objects.create(criado_por=self.user, titulo="Processo Teste")
        processo.clientes.add(a, b)
        self.assertEqual(clientes_relacionados(a), [b])
        self.assertEqual(clientes_relacionados(b), [a])
        self.assertEqual(clientes_relacionados(c), [])

    def test_base_restringe_o_universo_visivel(self):
        a, b = self._cliente("A"), self._cliente("B")
        processo = Processo.objects.create(criado_por=self.user, titulo="Processo Teste")
        processo.clientes.add(a, b)
        self.assertEqual(
            clientes_relacionados(a, base=Cliente.objects.filter(pk=a.pk)), [],
        )

