"""
patrocinio_do_processo — casamento best-effort entre Processo.cliente e
ParteProcesso por CPF/CNPJ, usado pelo Dashboard (Análise de dados) —
specs/dashboard-abas-visao-geral-analise-dados.md.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.clientes.models import Cliente
from apps.processos.models import ParteProcesso, Processo
from apps.processos.services import patrocinio_do_processo


class TestPatrocinioDoProcesso(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_processos_patrocinio"

    def setUp(self):
        super().setUp()
        self.responsavel = User.objects.create_user("resp_patrocinio", password="testpass")

    def _processo(self, cliente=None):
        processo = Processo.objects.create(
            titulo="Processo teste", criado_por=self.responsavel
        )
        if cliente is not None:
            processo.clientes.add(cliente)
        return processo

    def test_sem_cliente_retorna_none(self):
        processo = self._processo(cliente=None)
        self.assertIsNone(patrocinio_do_processo(processo))

    def test_cliente_sem_cpf_cnpj_retorna_none(self):
        cliente = Cliente.objects.create(
            nome_razao_social="Cliente sem doc", tipo="PF", responsavel=self.responsavel
        )
        processo = self._processo(cliente=cliente)
        self.assertIsNone(patrocinio_do_processo(processo))

    def test_casamento_por_documento_normalizado_retorna_grupo_visual(self):
        cliente = Cliente.objects.create(
            nome_razao_social="Cliente Réu", tipo="PF",
            cpf_cnpj="222.222.222-22", responsavel=self.responsavel,
        )
        processo = self._processo(cliente=cliente)
        ParteProcesso.objects.create(
            processo=processo, papel="reu", nome="Cliente Réu", cpf_cnpj="22222222222",
        )
        self.assertEqual(patrocinio_do_processo(processo), "polo_passivo")

    def test_sem_parte_correspondente_retorna_none(self):
        cliente = Cliente.objects.create(
            nome_razao_social="Cliente Autor", tipo="PF",
            cpf_cnpj="333.333.333-33", responsavel=self.responsavel,
        )
        processo = self._processo(cliente=cliente)
        ParteProcesso.objects.create(
            processo=processo, papel="reu", nome="Parte não relacionada", cpf_cnpj="999.999.999-99",
        )
        self.assertIsNone(patrocinio_do_processo(processo))
