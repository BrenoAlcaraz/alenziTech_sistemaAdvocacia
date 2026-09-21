"""
Testes da aba Gráfico (receita × despesa por mês)
(specs/financeiro-visao-grafica-navegacao-temporal.md).

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_navegacao_mensal.py sobre
django_tenants.test.cases.TenantTestCase. Usa datas relativas a
`timezone.localdate()` para não depender do mês em que os testes são
executados.
"""

from datetime import date

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_FINANCEIRO,
    NIVEL_DADOS_TODOS,
    NIVEL_SOLICITACOES,
)
from apps.financeiro.models import LancamentoFinanceiro


def _mes_menos(data, meses):
    indice = data.year * 12 + (data.month - 1) - meses
    return date(indice // 12, indice % 12 + 1, 1)


class GraficoBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_grafico"

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

    def _pago(self, *, tipo, valor, data_pagamento):
        LancamentoFinanceiro.objects.create(
            tipo=tipo, descricao="Teste", valor=valor, status="pago",
            data_vencimento=data_pagamento, data_pagamento=data_pagamento,
        )


class TestAgregacaoDoGrafico(GraficoBase):
    def test_soma_receita_e_despesa_do_mes_atual(self):
        self._pago(tipo="receita", valor="1000.00", data_pagamento=self.hoje)
        self._pago(tipo="receita", valor="500.00", data_pagamento=self.hoje)
        self._pago(tipo="despesa", valor="300.00", data_pagamento=self.hoje)

        r = self.client.get("/financeiro/grafico/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        barra_mes_atual = r.context["barras"][-1]
        self.assertEqual(barra_mes_atual["receita"], "R$ 1.500,00")
        self.assertEqual(barra_mes_atual["despesa"], "R$ 300,00")

    def test_lancamento_pendente_nao_entra_na_agregacao(self):
        LancamentoFinanceiro.objects.create(
            tipo="receita", descricao="Pendente", valor="9999.00",
            status="pendente", data_vencimento=self.hoje,
        )
        r = self.client.get("/financeiro/grafico/", HTTP_HOST=self.http_host)
        barra_mes_atual = r.context["barras"][-1]
        self.assertEqual(barra_mes_atual["receita"], "R$ 0,00")

    def test_lancamento_fora_do_intervalo_de_6_meses_nao_aparece(self):
        fora = _mes_menos(self.hoje, 8)
        self._pago(tipo="despesa", valor="777.00", data_pagamento=fora)

        r = self.client.get("/financeiro/grafico/?periodo=6meses", HTTP_HOST=self.http_host)
        total = sum(
            float(b["despesa"].replace("R$ ", "").replace(".", "").replace(",", "."))
            for b in r.context["barras"]
        )
        self.assertEqual(total, 0.0)

    def test_barras_cobrem_todos_os_meses_do_intervalo_mesmo_sem_lancamento(self):
        r = self.client.get("/financeiro/grafico/?periodo=6meses", HTTP_HOST=self.http_host)
        self.assertEqual(len(r.context["barras"]), 6)


class TestToggleDePeriodo(GraficoBase):
    def test_periodo_invalido_cai_para_6meses(self):
        r = self.client.get("/financeiro/grafico/?periodo=invalido", HTTP_HOST=self.http_host)
        self.assertEqual(r.context["periodo"], "6meses")
        self.assertEqual(len(r.context["barras"]), 6)

    def test_periodo_12meses_gera_12_barras(self):
        r = self.client.get("/financeiro/grafico/?periodo=12meses", HTTP_HOST=self.http_host)
        self.assertEqual(len(r.context["barras"]), 12)

    def test_periodo_exercicio_gera_barras_de_janeiro_ate_o_mes_atual(self):
        r = self.client.get("/financeiro/grafico/?periodo=exercicio", HTTP_HOST=self.http_host)
        self.assertEqual(len(r.context["barras"]), self.hoje.month)


class TestAutorizacaoDoGrafico(GraficoBase):
    def test_nivel_solicitacoes_e_redirecionado(self):
        user = User.objects.create_user(username="so_solicitacoes", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Solicitacoes", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_SOLICITACOES,
        )
        self.client.force_login(user)

        r = self.client.get("/financeiro/grafico/", HTTP_HOST=self.http_host)
        self.assertRedirects(r, "/financeiro/solicitacoes/")

    def test_sem_modulo_financeiro_e_negado(self):
        user = User.objects.create_user(username="sem_modulo", password="testpass")
        self.client.force_login(user)
        r = self.client.get("/financeiro/grafico/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)
