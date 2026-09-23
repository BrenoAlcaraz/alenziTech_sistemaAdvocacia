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

        self.assertEqual(self._descricoes("filtro=apagar_hoje"), ["Pagar hoje"])
        self.assertEqual(self._descricoes("filtro=areceber_hoje"), ["Receber hoje"])
        self.assertEqual(self._descricoes("filtro=apagar_atrasados"), ["Pagar atrasado"])
        self.assertEqual(self._descricoes("filtro=areceber_atrasados"), ["Receber atrasado"])

    def test_solicitacoes_filtradas_por_vencimento(self):
        for descricao, vencimento, status in (
            ("Vencida", self.hoje - timedelta(days=1), "aprovada"),
            ("Vence hoje", self.hoje, "solicitada"),
            ("Futura", self.hoje + timedelta(days=1), "solicitada"),
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
        self.assertEqual(descricoes("hoje"), ["Vence hoje"])
