"""
"Cancelado" só por ação, nunca escolhido no formulário, e as ações de
cancelar/encerrar pedem confirmação com o efeito calculado no backend
(specs/financeiro-cancelamento-lancamentos.md).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.financeiro.forms import LancamentoFinanceiroForm
from apps.financeiro.models import LancamentoFinanceiro


class CancelamentoBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "fin_cancelamento_lancamento"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.hoje = timezone.localdate()
        self.user = User.objects.create_user(username="fin_cancelamento", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS)
        self.client.force_login(self.user)

    def _lancamento(self, **kwargs):
        dados = {
            "tipo": "despesa", "descricao": "Aluguel", "valor": Decimal("3000.00"),
            "data_vencimento": self.hoje, "status": "pendente", "categoria": "aluguel",
        }
        dados.update(kwargs)
        return LancamentoFinanceiro.objects.create(**dados)

    def _dados(self, **extra):
        dados = {
            "tipo": "despesa", "descricao": "Aluguel", "valor": "3000.00", "categoria": "aluguel",
            "status": "pendente", "data_vencimento": self.hoje.isoformat(), "classificacao": "unica",
        }
        dados.update(extra)
        return dados


class TestStatusNoFormulario(CancelamentoBase):
    def test_criar_oferece_so_pendente_e_pago(self):
        valores = [valor for valor, _ in LancamentoFinanceiroForm().fields["status"].choices]
        self.assertEqual(valores, ["pendente", "pago"])

    def test_criar_recusa_status_cancelado(self):
        r = self.client.post("/financeiro/lancamentos/novo/", self._dados(status="cancelado"), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(LancamentoFinanceiro.objects.exists())

    def test_editar_pendente_recusa_status_cancelado(self):
        lancamento = self._lancamento()
        form = LancamentoFinanceiroForm(data=self._dados(status="cancelado"), instance=lancamento)
        self.assertIn("status", form.errors)

    def test_editar_cancelado_mantem_status_so_para_leitura(self):
        lancamento = self._lancamento(status="cancelado")
        form = LancamentoFinanceiroForm(data=self._dados(status="pendente"), instance=lancamento)
        self.assertTrue(form.fields["status"].disabled)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().status, "cancelado")


class TestConfirmacaoDeCancelamento(CancelamentoBase):
    def _recorrencia(self):
        """1 paga e 1 vencida no passado, 2 futuras pendentes e 1 futura
        já cancelada (não entra no resumo)."""
        origem = self._lancamento(
            classificacao="recorrente", periodicidade="mensal",
            data_vencimento=self.hoje - timedelta(days=60), status="pago", data_pagamento=self.hoje,
        )
        ocorrencia = {"classificacao": "recorrente", "periodicidade": "mensal", "lancamento_origem": origem}
        self._lancamento(data_vencimento=self.hoje - timedelta(days=30), **ocorrencia)
        self._lancamento(data_vencimento=self.hoje, **ocorrencia)
        self._lancamento(data_vencimento=self.hoje + timedelta(days=30), **ocorrencia)
        self._lancamento(data_vencimento=self.hoje + timedelta(days=60), status="cancelado", **ocorrencia)
        return origem

    def test_get_de_cancelar_mostra_confirmacao_sem_cancelar(self):
        lancamento = self._lancamento()
        r = self.client.get(f"/financeiro/lancamentos/{lancamento.pk}/cancelar/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Cancelar lançamento?")
        self.assertContains(r, 'method="post"')
        lancamento.refresh_from_db()
        self.assertEqual(lancamento.status, "pendente")

    def test_resumo_do_encerramento_bate_com_o_que_e_cancelado(self):
        origem = self._recorrencia()
        url = f"/financeiro/lancamentos/{origem.pk}/cancelar-recorrencia/"

        r = self.client.get(url, HTTP_HOST=self.http_host)
        resumo = r.context["resumo"]
        self.assertEqual(resumo["pagas"], 1)
        self.assertEqual(resumo["vencidas"]["quantidade"], 1)
        self.assertEqual(resumo["futuras"]["quantidade"], 2)
        self.assertEqual(resumo["futuras"]["total"], Decimal("6000.00"))
        self.assertContains(r, "Encerrar recorrência")
        self.assertEqual(LancamentoFinanceiro.objects.filter(status="cancelado").count(), 1)

        self.client.post(url, HTTP_HOST=self.http_host)
        self.assertEqual(LancamentoFinanceiro.objects.filter(status="cancelado").count(), 1 + 2)

    def test_sem_futuras_nao_oferece_confirmar(self):
        origem = self._lancamento(
            classificacao="parcelado", numero_parcelas=2, data_vencimento=self.hoje - timedelta(days=1),
        )
        r = self.client.get(f"/financeiro/lancamentos/{origem.pk}/cancelar-recorrencia/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Não há parcelas futuras pendentes para cancelar.")
        self.assertNotContains(r, 'type="submit"')

    def test_lista_abre_janela_em_vez_de_confirm_do_navegador(self):
        self._recorrencia()
        r = self.client.get("/financeiro/", HTTP_HOST=self.http_host)
        self.assertContains(r, "data-confirmar-url")
        self.assertContains(r, 'id="dlg-confirmar-lancamento"')
        self.assertNotContains(r, "confirm('As ocorrências futuras")
