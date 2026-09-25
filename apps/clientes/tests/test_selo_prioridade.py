"""
Testes do segundo visor e do selo de prioridade idoso/menor de idade
(specs/clientes-segundo-visor-prioridade.md).

Cobre: cálculo de idade (incluindo os limiares exatos 60 e 18 anos);
PJ e cliente sem data de nascimento nunca têm idade/selo; form limpa
data_nascimento para PJ; o selo aparece na listagem/detalhe do cliente,
no processo vinculado — sem quebrar quando não há selo.
"""

from datetime import date

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    MODULO_CLIENTES,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)
from apps.clientes.forms import ClienteForm
from apps.clientes.models import Cliente
from apps.processos.models import Processo


def _data_com_idade(anos):
    """Data de nascimento (1º de janeiro) tal que, hoje, a pessoa tem
    exatamente `anos` anos completos — 1º de janeiro já passou em
    qualquer data do ano corrente, então o cálculo independe de quando
    o teste roda."""
    hoje = date.today()
    return date(hoje.year - anos, 1, 1)


class TestIdadeESeloModel(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_selo_prioridade_model"

    def test_pf_menos_de_18_anos_recebe_selo_menor_de_idade(self):
        cliente = Cliente(tipo="PF", data_nascimento=_data_com_idade(10))
        self.assertEqual(cliente.idade, 10)
        self.assertEqual(cliente.selo_prioridade, "menor_idade")

    def test_pf_17_anos_recebe_selo_menor_de_idade(self):
        cliente = Cliente(tipo="PF", data_nascimento=_data_com_idade(17))
        self.assertEqual(cliente.selo_prioridade, "menor_idade")

    def test_pf_18_anos_nao_recebe_nenhum_selo(self):
        cliente = Cliente(tipo="PF", data_nascimento=_data_com_idade(18))
        self.assertEqual(cliente.idade, 18)
        self.assertIsNone(cliente.selo_prioridade)

    def test_pf_59_anos_nao_recebe_nenhum_selo(self):
        cliente = Cliente(tipo="PF", data_nascimento=_data_com_idade(59))
        self.assertIsNone(cliente.selo_prioridade)

    def test_pf_60_anos_recebe_selo_idoso(self):
        cliente = Cliente(tipo="PF", data_nascimento=_data_com_idade(60))
        self.assertEqual(cliente.idade, 60)
        self.assertEqual(cliente.selo_prioridade, "idoso")

    def test_pf_mais_de_60_anos_recebe_selo_idoso(self):
        cliente = Cliente(tipo="PF", data_nascimento=_data_com_idade(85))
        self.assertEqual(cliente.selo_prioridade, "idoso")

    def test_pf_sem_data_nascimento_nao_tem_idade_nem_selo(self):
        cliente = Cliente(tipo="PF", data_nascimento=None)
        self.assertIsNone(cliente.idade)
        self.assertIsNone(cliente.selo_prioridade)

    def test_pj_nunca_tem_idade_nem_selo_mesmo_com_data(self):
        cliente = Cliente(tipo="PJ", data_nascimento=_data_com_idade(70))
        self.assertIsNone(cliente.idade)
        self.assertIsNone(cliente.selo_prioridade)


class TestFormLimpaDataNascimentoParaPJ(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_selo_prioridade_form"

    def test_pj_limpa_data_nascimento_enviada_manualmente(self):
        form = ClienteForm(data={
            "tipo": "PJ",
            "nome_razao_social": "Empresa Teste LTDA",
            "data_nascimento": "1990-01-01",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["data_nascimento"])

    def test_pf_mantem_data_nascimento_informada(self):
        form = ClienteForm(data={
            "tipo": "PF",
            "nome_razao_social": "Fulano de Tal",
            "data_nascimento": "1990-05-20",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["data_nascimento"], date(1990, 5, 20))


class SeloPrioridadeViewBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_modulo(self, user, modulo, *, habilitacao=None):
        # Um papel por usuário: módulos extras entram no mesmo papel.
        vinculo = UsuarioPapel.objects.filter(usuario=user, ativo=True).first()
        if vinculo:
            papel = vinculo.papel
        else:
            papel = PapelAcesso.objects.create(nome=f"Papel {user.username}", ativo=True)
            UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=modulo, ativo=True, nivel=NIVEL_TODOS
        )
        if habilitacao:
            HabilitacaoPapel.objects.create(
                papel=papel, modulo=modulo, item=habilitacao, ativo=True
            )
        return papel


class TestSeloApareceNaListaEDetalheDoCliente(SeloPrioridadeViewBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_selo_lista_detalhe"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_clientes_selo")
        self._dar_modulo(self.user, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR)
        self.client.force_login(self.user)
        self.idoso = Cliente.objects.create(
            responsavel=self.user, tipo="PF", nome_razao_social="Cliente Idoso",
            data_nascimento=_data_com_idade(70),
        )
        self.sem_selo = Cliente.objects.create(
            responsavel=self.user, tipo="PF", nome_razao_social="Cliente Sem Selo",
            data_nascimento=_data_com_idade(40),
        )
        self.sem_data = Cliente.objects.create(
            responsavel=self.user, tipo="PF", nome_razao_social="Cliente Sem Data",
        )

    def test_lista_mostra_selo_idoso(self):
        r = self.client.get("/clientes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Idoso")

    def test_detalhe_mostra_idade_e_selo(self):
        r = self.client.get(f"/clientes/{self.idoso.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Idoso")
        self.assertContains(r, "70 anos")

    def test_detalhe_sem_data_nascimento_nao_quebra_e_nao_mostra_selo(self):
        r = self.client.get(f"/clientes/{self.sem_data.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Idoso")
        self.assertNotContains(r, "Menor de idade")

    def test_detalhe_entre_18_e_60_nao_mostra_selo(self):
        r = self.client.get(f"/clientes/{self.sem_selo.pk}/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "Idoso")
        self.assertNotContains(r, "Menor de idade")


class TestSeloApareceEmProcessoVinculado(SeloPrioridadeViewBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_selo_processo_tarefa"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_processo_tarefa_selo")
        self._dar_modulo(self.user, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR)
        self._dar_modulo(self.user, MODULO_PROCESSOS)
        self.client.force_login(self.user)
        self.menor = Cliente.objects.create(
            responsavel=self.user, tipo="PF", nome_razao_social="Cliente Menor",
            data_nascimento=_data_com_idade(10),
        )
        self.processo = Processo.objects.create(responsavel=self.user, titulo="Processo Teste Selo")
        self.processo.clientes.add(self.menor)

    def test_processo_detalhe_mostra_selo_do_cliente_vinculado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Menor de idade")

