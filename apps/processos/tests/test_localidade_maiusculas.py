"""Localidade do processo (cidade/comarca/vara) e do cliente sempre em
maiúsculas — "CABO FRIO" e "Cabo Frio" não podem virar duas cidades."""

import importlib

from django.apps import apps
from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.clientes.forms import ClienteForm
from apps.clientes.models import Cliente
from apps.processos.forms import ProcessoForm
from apps.processos.models import Processo


class TestLocalidadeEmMaiusculas(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "processos_localidade_maiusculas"

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("loc_user", password="x")

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

    def test_migracao_uniformiza_registros_existentes(self):
        Processo.objects.create(responsavel=self.user, titulo="A", cidade="Cabo Frio", comarca=" Cabo Frio")
        Processo.objects.create(responsavel=self.user, titulo="B", cidade="CABO FRIO")
        cliente = Cliente.objects.create(responsavel=self.user, nome_razao_social="x", cidade="Cabo frio")
        importlib.import_module("apps.processos.migrations.0025_localidade_em_maiusculas").para_maiusculas(apps, None)
        importlib.import_module("apps.clientes.migrations.0012_nomes_e_localidade_em_maiusculas").para_maiusculas(apps, None)
        self.assertEqual(set(Processo.objects.values_list("cidade", flat=True)), {"CABO FRIO"})
        self.assertEqual(set(Processo.objects.values_list("comarca", flat=True)), {"CABO FRIO", ""})
        cliente.refresh_from_db()
        self.assertEqual(cliente.cidade, "CABO FRIO")
