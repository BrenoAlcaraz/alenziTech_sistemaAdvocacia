"""
Testes do extrato de custas por cliente (drill-down) e da regra de
saldo do PDR-0005, incluindo o terceiro tipo "paga_pelo_cliente"
(specs/financeiro-visao-grafica-navegacao-temporal.md).

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_autorizacao.py sobre
django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.clientes.models import Cliente
from apps.financeiro.models import CustaJudicial


class ExtratoCustasBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_extrato_custas"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"
        self.user = User.objects.create_user(username="financeiro_user", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(nome_razao_social="Cliente Teste", tipo="PF", responsavel=self.user)

    def _custa(self, **kwargs):
        defaults = {
            "descricao": "Custa Teste",
            "valor": "100.00",
            "data": "2026-09-01",
            "tipo": "adiantamento",
            "cliente": self.cliente,
        }
        defaults.update(kwargs)
        return CustaJudicial.objects.create(**defaults)


class TestSaldoComTresTipos(ExtratoCustasBase):
    def test_deposito_soma_e_adiantamento_subtrai(self):
        self._custa(tipo="deposito_cliente", valor="500.00")
        self._custa(tipo="adiantamento", valor="200.00")

        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        saldo = next(s for s in r.context["saldo_clientes"] if s["cliente_id"] == self.cliente.pk)
        self.assertEqual(saldo["saldo"], "Crédito: R$ 300,00")
        self.assertTrue(saldo["credito"])

    def test_paga_pelo_cliente_nao_altera_saldo(self):
        self._custa(tipo="deposito_cliente", valor="500.00")
        self._custa(tipo="paga_pelo_cliente", valor="9999.00")

        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        saldo = next(s for s in r.context["saldo_clientes"] if s["cliente_id"] == self.cliente.pk)
        self.assertEqual(saldo["saldo"], "Crédito: R$ 500,00")

    def test_cliente_so_com_paga_pelo_cliente_aparece_na_lista_com_saldo_zero(self):
        self._custa(tipo="paga_pelo_cliente", valor="300.00")

        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        saldo = next(s for s in r.context["saldo_clientes"] if s["cliente_id"] == self.cliente.pk)
        self.assertEqual(saldo["saldo"], "Sem saldo pendente")


class TestExtratoPorCliente(ExtratoCustasBase):
    def test_extrato_lista_custas_nas_abas_corretas(self):
        adiantamento = self._custa(tipo="adiantamento", descricao="Diligência")
        paga_cliente = self._custa(tipo="paga_pelo_cliente", descricao="Taxa recursal")
        deposito = self._custa(tipo="deposito_cliente", descricao="Depósito inicial")

        r = self.client.get(f"/financeiro/custas/cliente/{self.cliente.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        lancamentos = list(r.context["lancamentos"])
        creditos = list(r.context["creditos"])
        self.assertIn(adiantamento, lancamentos)
        self.assertIn(paga_cliente, lancamentos)
        self.assertNotIn(deposito, lancamentos)
        self.assertIn(deposito, creditos)

    def test_extrato_exibe_saldo_calculado(self):
        self._custa(tipo="deposito_cliente", valor="800.00")
        self._custa(tipo="adiantamento", valor="300.00")

        r = self.client.get(f"/financeiro/custas/cliente/{self.cliente.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.context["saldo"], "+ R$ 500,00")
        self.assertTrue(r.context["saldo_positivo"])

    def test_cliente_inexistente_e_404(self):
        r = self.client.get("/financeiro/custas/cliente/99999/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_lista_de_custas_tem_link_clicavel_para_o_extrato(self):
        self._custa()
        r = self.client.get("/financeiro/custas/", HTTP_HOST=self.http_host)
        self.assertContains(r, f"/financeiro/custas/cliente/{self.cliente.pk}/")


class TestFormCustaPrefillCliente(ExtratoCustasBase):
    def test_get_com_cliente_na_querystring_preenche_o_campo(self):
        r = self.client.get(f"/financeiro/custas/nova/?cliente={self.cliente.pk}", HTTP_HOST=self.http_host)
        self.assertEqual(r.context["form"].initial.get("cliente"), str(self.cliente.pk))

    def test_post_com_cliente_redireciona_para_o_extrato(self):
        r = self.client.post(
            "/financeiro/custas/nova/",
            {
                "tipo": "adiantamento",
                "descricao": "Custa via extrato",
                "valor": "150.00",
                "data": "2026-09-05",
                "cliente": self.cliente.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/financeiro/custas/cliente/{self.cliente.pk}/", fetch_redirect_response=False,
        )
