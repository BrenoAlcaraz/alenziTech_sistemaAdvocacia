"""Lista de lançamentos em tabela: paginação, ordenação, linha de totais
e escopo (specs/ui-05-shell-e-listas.md)."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_PROPRIOS
from apps.financeiro.models import LancamentoFinanceiro


class TestListaLancamentosTabela(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "ui05_lista_financeiro"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.hoje = timezone.localdate()
        self.user = User.objects.create_user(username="financeiro_proprios", password="testpass")
        self.outro = User.objects.create_user(username="financeiro_alheio", password="testpass")
        papel = PapelAcesso.objects.create(nome="Financeiro próprios", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_PROPRIOS,
        )
        self.client.force_login(self.user)

    def _em_massa(self, responsavel, quantidade, **campos):
        campos = {"tipo": "receita", "valor": Decimal("10.00"), "status": "pendente", **campos}
        LancamentoFinanceiro.objects.bulk_create([
            LancamentoFinanceiro(
                descricao=f"{responsavel.username} {i:03d}", data_vencimento=self.hoje,
                responsavel=responsavel, **campos,
            )
            for i in range(quantidade)
        ])

    def _get(self, query=""):
        return self.client.get(f"/financeiro/{query}", HTTP_HOST=self.http_host)

    def test_dados_proprios_pagina_e_totaliza_so_os_seus_sem_cancelados(self):
        self._em_massa(self.user, 55)
        self._em_massa(self.user, 1, tipo="despesa", valor=Decimal("30.00"))
        self._em_massa(self.user, 1, status="cancelado", valor=Decimal("999.00"))
        self._em_massa(self.outro, 55, valor=Decimal("500.00"))

        resposta = self._get("?ordem=-valor")
        pagina = resposta.context["lancamentos"]
        self.assertEqual(pagina.paginator.count, 57)
        self.assertEqual(len(pagina), 50)
        self.assertEqual(pagina[0].valor, Decimal("999.00"))
        self.assertContains(resposta, "?ordem=-valor&amp;pagina=2")
        self.assertEqual(
            resposta.context["totais_lista"],
            {"receitas": Decimal("550.00"), "despesas": Decimal("30.00"), "saldo": Decimal("520.00")},
        )

        segunda = self._get("?ordem=-valor&pagina=2").context["lancamentos"]
        self.assertEqual(len(segunda), 7)
        self.assertEqual(
            {l.responsavel_id for l in list(pagina) + list(segunda)}, {self.user.pk}
        )
