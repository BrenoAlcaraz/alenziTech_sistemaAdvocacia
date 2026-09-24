"""Filas automáticas da lista de Lançamentos: Vencidas e A vencer em 7 dias
(docs/modules/financeiro.md)."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_FINANCEIRO,
    MODULO_PAINEL,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_TODOS,
)
from apps.financeiro.models import LancamentoFinanceiro


class TestFilasFinanceiro(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "ui06_filas_financeiro"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("filas_financeiro", password="testpass")
        self.outro = User.objects.create_user("filas_financeiro_outro", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel filas financeiro", ativo=True)
        UsuarioPapel.objects.create(usuario=self.usuario, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_PROPRIOS,
        )
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PAINEL, ativo=True, nivel=NIVEL_TODOS)
        self.client.force_login(self.usuario)
        self.hoje = timezone.localdate()

    def _lancamento(self, descricao, dias, **kwargs):
        dados = {
            "tipo": "despesa", "valor": "10.00", "status": "pendente",
            "data_vencimento": self.hoje + timedelta(days=dias), "responsavel": self.usuario,
        }
        dados.update(kwargs)
        return LancamentoFinanceiro.objects.create(descricao=descricao, **dados)

    def _fila(self, filtro):
        resposta = self.client.get(f"/financeiro/?filtro={filtro}", HTTP_HOST=self.http_host)
        descricoes = sorted(l.descricao for l in resposta.context["lancamentos"])
        return descricoes, resposta.context

    def test_vencidas_e_a_vencer_em_7_dias_com_contagem_igual_as_linhas(self):
        self._lancamento("Vencida há 40 dias", -40)
        self._lancamento("Receita vencida ontem", -1, tipo="receita")
        self._lancamento("Vence hoje", 0)
        self._lancamento("Receita em 7 dias", 7, tipo="receita")
        self._lancamento("Em 8 dias", 8)
        self._lancamento("Paga vencida", -3, status="pago", data_pagamento=self.hoje)
        self._lancamento("Cancelada vencida", -3, status="cancelado")
        self._lancamento("Alheia vencida", -3, responsavel=self.outro)
        self._lancamento("Alheia a vencer", 2, responsavel=self.outro)

        vencidas, contexto = self._fila("atrasados")
        a_vencer, _ = self._fila("vencer_7dias")

        self.assertEqual(vencidas, ["Receita vencida ontem", "Vencida há 40 dias"])
        self.assertEqual(a_vencer, ["Receita em 7 dias", "Vence hoje"])
        self.assertEqual(contexto["total_fila_vencidas"], len(vencidas))
        self.assertEqual(contexto["total_fila_a_vencer"], len(a_vencer))

    def test_vencidas_tem_o_mesmo_numero_do_painel(self):
        self._lancamento("Pagar vencida", -5)
        self._lancamento("Receber vencida", -40, tipo="receita")
        self._lancamento("Alheia vencida", -3, responsavel=self.outro)

        painel = self.client.get("/?periodo=mes", HTTP_HOST=self.http_host).context["cards_financeiros"]
        _, contexto = self._fila("atrasados")

        atrasados_painel = (
            painel["pendencias"]["a_pagar"]["atrasados"]["quantidade"]
            + painel["pendencias"]["a_receber"]["atrasados"]["quantidade"]
        )
        self.assertEqual(contexto["total_fila_vencidas"], atrasados_painel)
        self.assertEqual(atrasados_painel, 2)
