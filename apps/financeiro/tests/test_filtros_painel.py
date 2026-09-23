"""
Filtros do Financeiro usados como destino dos cards do Painel —
specs/painel-cards-financeiros.md.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.financeiro.models import LancamentoFinanceiro, SolicitacaoFinanceira
from apps.financeiro.services import janela_do_periodo


class TestFiltrosDestinoDoPainel(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_financeiro_filtros_painel"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("filtros_painel", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel filtros painel", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(self.usuario)
        self.hoje = timezone.localdate()
        self.mes_anterior = self.hoje.replace(day=1) - timedelta(days=1)

    def _lancamento(self, descricao, **kwargs):
        dados = {"tipo": "despesa", "valor": "10.00", "status": "pendente", "data_vencimento": self.hoje}
        dados.update(kwargs)
        return LancamentoFinanceiro.objects.create(descricao=descricao, **dados)

    def _descricoes(self, query):
        resposta = self.client.get(f"/financeiro/?{query}", HTTP_HOST=self.http_host)
        return sorted(l.descricao for l in resposta.context["lancamentos"])

    def test_atrasados_inclui_mes_anterior_mesmo_navegando_no_mes_atual(self):
        self._lancamento("Atrasado antigo", data_vencimento=self.mes_anterior)
        self._lancamento("Hoje")

        query = f"ano={self.hoje.year}&mes={self.hoje.month}&filtro=atrasados"
        self.assertEqual(self._descricoes(query), ["Atrasado antigo"])

    def test_filtros_de_hoje_e_atrasados_por_tipo(self):
        self._lancamento("Pagar hoje")
        self._lancamento("Receber hoje", tipo="receita")
        self._lancamento("Pagar atrasado", data_vencimento=self.mes_anterior)
        self._lancamento("Receber atrasado", tipo="receita", data_vencimento=self.mes_anterior)
        self._lancamento("Pago hoje", status="pago", data_pagamento=self.hoje)

        self.assertEqual(self._descricoes("filtro=apagar_periodo&periodo=dia"), ["Pagar hoje"])
        self.assertEqual(self._descricoes("filtro=areceber_periodo&periodo=dia"), ["Receber hoje"])
        # Sem período, "vence no período" é o dia.
        self.assertEqual(self._descricoes("filtro=apagar_periodo"), ["Pagar hoje"])
        self.assertEqual(self._descricoes("filtro=apagar_atrasados"), ["Pagar atrasado"])
        self.assertEqual(self._descricoes("filtro=areceber_atrasados"), ["Receber atrasado"])

    def test_vence_no_periodo_vai_de_hoje_ao_fim_da_semana_ou_do_mes(self):
        _, fim_semana = janela_do_periodo("semana", self.hoje)
        _, fim_mes = janela_do_periodo("mes", self.hoje)
        self._lancamento("Hoje")
        self._lancamento("Fim da semana", data_vencimento=fim_semana)
        self._lancamento("Fim do mês", data_vencimento=fim_mes)
        self._lancamento("Atrasado", data_vencimento=self.mes_anterior)

        semana = self._descricoes("filtro=apagar_periodo&periodo=semana")
        mes = self._descricoes("filtro=apagar_periodo&periodo=mes")

        self.assertIn("Fim da semana", semana)
        self.assertNotIn("Atrasado", semana)
        esperado_mes = {"Hoje", "Fim do mês"} | ({"Fim da semana"} if fim_semana <= fim_mes else set())
        self.assertEqual(mes, sorted(esperado_mes))

    def test_recorte_por_periodo_no_resumo_do_financeiro(self):
        _, fim_semana = janela_do_periodo("semana", self.hoje)
        self._lancamento("Pagar hoje", valor="10.00")
        self._lancamento("Pagar fim da semana", valor="5.00", data_vencimento=fim_semana)

        dia = self.client.get("/financeiro/?periodo=dia", HTTP_HOST=self.http_host).context
        semana = self.client.get("/financeiro/?periodo=semana", HTTP_HOST=self.http_host).context

        self.assertTrue(dia["recorte_periodo"])
        esperado_dia = "R$ 15,00" if fim_semana == self.hoje else "R$ 10,00"
        self.assertEqual(dia["resumo"]["a_pagar"], esperado_dia)
        self.assertEqual(semana["resumo"]["a_pagar"], "R$ 15,00")

    def test_solicitacoes_filtradas_por_vencimento(self):
        _, fim_mes = janela_do_periodo("mes", self.hoje)
        for descricao, vencimento, status in (
            ("Vencida", self.hoje - timedelta(days=1), "aprovada"),
            ("Vence hoje", self.hoje, "solicitada"),
            ("Fora do mês", fim_mes + timedelta(days=1), "solicitada"),
            ("Paga vencida", self.hoje - timedelta(days=1), "paga"),
        ):
            SolicitacaoFinanceira.objects.create(
                tipo="pagamento", descricao=descricao, valor="10.00",
                vencimento=vencimento, status=status, solicitante=self.usuario,
            )

        def descricoes(vencimento):
            resposta = self.client.get(
                f"/financeiro/solicitacoes/?situacao=pendentes&vencimento={vencimento}",
                HTTP_HOST=self.http_host,
            )
            return [s.descricao for s in resposta.context["solicitacoes"]]

        self.assertEqual(descricoes("vencidas"), ["Vencida"])
        self.assertEqual(descricoes("dia"), ["Vence hoje"])
        self.assertEqual(descricoes("mes"), ["Vence hoje"])
