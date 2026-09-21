"""
Testes do navegador de mês e do card "Saldo atual do mês" na aba
Lançamentos (specs/financeiro-visao-grafica-navegacao-temporal.md).

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_autorizacao.py sobre
django_tenants.test.cases.TenantTestCase. Usa datas relativas a
`timezone.localdate()` (nunca uma data fixa) para não depender do mês
em que os testes são executados.
"""

from datetime import date

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.financeiro.models import LancamentoFinanceiro


def _mes_menos(data, meses):
    """Primeiro dia do mês `meses` antes do mês de `data` — sem
    depender de biblioteca externa de datas."""
    indice = data.year * 12 + (data.month - 1) - meses
    return date(indice // 12, indice % 12 + 1, 1)


class NavegacaoMensalBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_navegacao_mensal"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"
        self.hoje = timezone.localdate()
        self.user = User.objects.create_user(username="financeiro_user", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(self.user)

    def _lancamento(self, **kwargs):
        defaults = {
            "tipo": "receita",
            "descricao": "Lançamento Teste",
            "valor": "1000.00",
            "data_vencimento": self.hoje,
            "status": "pendente",
        }
        defaults.update(kwargs)
        return LancamentoFinanceiro.objects.create(**defaults)

    def _get(self, ano=None, mes=None):
        params = {}
        if ano is not None:
            params["ano"] = ano
        if mes is not None:
            params["mes"] = mes
        return self.client.get("/financeiro/", params, HTTP_HOST=self.http_host)


class TestListaEResumoEscopadosPorMes(NavegacaoMensalBase):
    def test_lancamento_de_outro_mes_nao_aparece_no_mes_atual(self):
        do_mes = self._lancamento(descricao="Deste mês", data_vencimento=self.hoje)
        mes_passado = _mes_menos(self.hoje, 2)
        de_outro_mes = self._lancamento(descricao="De outro mês", data_vencimento=mes_passado)

        r = self._get()
        lancamentos = list(r.context["lancamentos"])
        self.assertIn(do_mes, lancamentos)
        self.assertNotIn(de_outro_mes, lancamentos)

    def test_a_receber_soma_so_pendentes_com_vencimento_no_mes_exibido(self):
        self._lancamento(valor="300.00", status="pendente", data_vencimento=self.hoje)
        mes_passado = _mes_menos(self.hoje, 1)
        self._lancamento(valor="9999.00", status="pendente", data_vencimento=mes_passado)

        r = self._get()
        self.assertEqual(r.context["resumo"]["a_receber"], "R$ 300,00")

    def test_navegar_para_mes_anterior_mostra_lancamento_daquele_mes(self):
        mes_passado = _mes_menos(self.hoje, 1)
        lancamento_passado = self._lancamento(descricao="Do mês passado", data_vencimento=mes_passado)
        lancamento_atual = self._lancamento(descricao="Do mês atual", data_vencimento=self.hoje)

        r = self._get(ano=mes_passado.year, mes=mes_passado.month)
        lancamentos = list(r.context["lancamentos"])
        self.assertIn(lancamento_passado, lancamentos)
        self.assertNotIn(lancamento_atual, lancamentos)


class TestTagMesAtual(NavegacaoMensalBase):
    def test_tag_mes_atual_aparece_sem_parametro_de_navegacao(self):
        r = self._get()
        self.assertTrue(r.context["mes_atual"])

    def test_tag_mes_atual_nao_aparece_ao_navegar_para_outro_mes(self):
        mes_passado = _mes_menos(self.hoje, 1)
        r = self._get(ano=mes_passado.year, mes=mes_passado.month)
        self.assertFalse(r.context["mes_atual"])


class TestSaldoAtualDoMes(NavegacaoMensalBase):
    def test_saldo_atual_do_mes_e_recebido_menos_pago(self):
        self._lancamento(
            tipo="receita", valor="1500.00", status="pago",
            data_vencimento=self.hoje, data_pagamento=self.hoje,
        )
        self._lancamento(
            tipo="despesa", valor="400.00", status="pago",
            data_vencimento=self.hoje, data_pagamento=self.hoje,
        )

        r = self._get()
        self.assertEqual(r.context["resumo"]["saldo_atual_mes"], "+ R$ 1.100,00")
        self.assertTrue(r.context["resumo"]["saldo_atual_mes_positivo"])

    def test_saldo_atual_do_mes_negativo_quando_pago_supera_recebido(self):
        self._lancamento(
            tipo="receita", valor="100.00", status="pago",
            data_vencimento=self.hoje, data_pagamento=self.hoje,
        )
        self._lancamento(
            tipo="despesa", valor="900.00", status="pago",
            data_vencimento=self.hoje, data_pagamento=self.hoje,
        )

        r = self._get()
        self.assertEqual(r.context["resumo"]["saldo_atual_mes"], "− R$ 800,00")
        self.assertFalse(r.context["resumo"]["saldo_atual_mes_positivo"])
