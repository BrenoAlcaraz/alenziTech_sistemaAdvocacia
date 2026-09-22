"""Localidade do processo (cidade/comarca/vara) e do cliente sempre em
maiúsculas — "CABO FRIO" e "Cabo Frio" não podem virar duas cidades."""

from django_tenants.test.cases import TenantTestCase

from apps.clientes.forms import ClienteForm
from apps.processos.forms import ProcessoForm


class TestLocalidadeEmMaiusculas(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "processos_localidade_maiusculas"

    def test_formulario_do_processo_normaliza_cidade_comarca_e_vara(self):
        form = ProcessoForm(data={
            "titulo": "P", "area_direito": "CÍVEL", "cidade": " Cabo Frio ", "comarca": "cabo frio",
            "vara": "1ª vara cível", "fase": "conhecimento", "gratuidade_justica_status": "nao_requerida",
        })
        form.is_valid()
        self.assertEqual(form.cleaned_data["cidade"], "CABO FRIO")
        self.assertEqual(form.cleaned_data["comarca"], "CABO FRIO")
        self.assertEqual(form.cleaned_data["vara"], "1ª VARA CÍVEL")

    def test_formulario_do_cliente_normaliza_cidade_e_bairro(self):
        form = ClienteForm(data={"tipo": "PF", "nome_razao_social": "x", "cidade": "Cabo Frio", "bairro": "centro"})
        form.is_valid()
        self.assertEqual(form.cleaned_data["cidade"], "CABO FRIO")
        self.assertEqual(form.cleaned_data["bairro"], "CENTRO")
