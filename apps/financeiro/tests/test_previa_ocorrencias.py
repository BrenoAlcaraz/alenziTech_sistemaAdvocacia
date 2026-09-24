"""
Prévia das cobranças de parcelado/recorrente nos formulários de
lançamento e de honorário (specs/recorrencia-rotulos-e-previa.md): o
texto tem de bater com o que `gerar_ocorrencias` de fato gera.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from apps.financeiro.models import LancamentoFinanceiro
from apps.financeiro.services import gerar_ocorrencias
from apps.financeiro.tests.test_classificacao_recorrencia import ClassificacaoRecorrenciaBase

URL_PREVIA = "/financeiro/previa-ocorrencias/"


class PreviaBase(ClassificacaoRecorrenciaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_previa_ocorrencias"

    def _previa(self, **params):
        resposta = self.client.get(URL_PREVIA, params, HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        return resposta.json()["texto"]

    def _gerado(self, **campos):
        origem = self._lancamento(**campos)
        gerar_ocorrencias(origem)
        grupo = [origem, *origem.ocorrencias.all()]
        return sorted((l.data_vencimento, Decimal(str(l.valor))) for l in grupo)


class TestPreviaBateComGeracao(PreviaBase):
    def test_parcelado_com_residuo_na_ultima(self):
        texto = self._previa(
            classificacao="parcelado", valor="1000.00", data_vencimento="2026-10-10", numero_parcelas="3",
        )
        self.assertEqual(
            texto, "3 parcelas de R$ 333,33 (a última de R$ 333,34), de 10/10/2026 a 10/12/2026 — total R$ 1.000,00.",
        )
        self.assertEqual(
            self._gerado(classificacao="parcelado", valor="1000.00", data_vencimento=date(2026, 10, 10), numero_parcelas=3),
            [
                (date(2026, 10, 10), Decimal("333.33")),
                (date(2026, 11, 10), Decimal("333.33")),
                (date(2026, 12, 10), Decimal("333.34")),
            ],
        )

    def test_recorrente_mensal_apos_n_cobrancas(self):
        texto = self._previa(
            classificacao="recorrente", valor="3000", data_vencimento="2026-10-10",
            periodicidade="mensal", duracao_tipo="quantidade", duracao_quantidade="12",
        )
        self.assertEqual(texto, "12 cobranças de R$ 3.000,00, de 10/10/2026 a 10/09/2027 — total R$ 36.000,00.")
        gerado = self._gerado(
            classificacao="recorrente", valor="3000.00", data_vencimento=date(2026, 10, 10),
            periodicidade="mensal", duracao_tipo="quantidade", duracao_quantidade=12,
        )
        self.assertEqual(len(gerado), 12)
        self.assertEqual(gerado[-1][0], date(2027, 9, 10))

    def test_recorrente_anual_ate_uma_data(self):
        texto = self._previa(
            classificacao="recorrente", valor="1200", data_vencimento="2026-03-31",
            periodicidade="anual", duracao_tipo="data_final", duracao_data_final="2029-03-01",
        )
        self.assertEqual(texto, "3 cobranças de R$ 1.200,00, de 31/03/2026 a 31/03/2028 — total R$ 3.600,00.")
        gerado = self._gerado(
            classificacao="recorrente", valor="1200.00", data_vencimento=date(2026, 3, 31),
            periodicidade="anual", duracao_tipo="data_final", duracao_data_final=date(2029, 3, 1),
        )
        self.assertEqual([d for d, _ in gerado], [date(2026, 3, 31), date(2027, 3, 31), date(2028, 3, 31)])

    def test_primeiro_vencimento_no_dia_31(self):
        texto = self._previa(
            classificacao="recorrente", valor="100", data_vencimento="2027-01-31",
            periodicidade="mensal", duracao_tipo="quantidade", duracao_quantidade="3",
        )
        self.assertEqual(texto, "3 cobranças de R$ 100,00, de 31/01/2027 a 31/03/2027 — total R$ 300,00.")
        gerado = self._gerado(
            classificacao="recorrente", valor="100.00", data_vencimento=date(2027, 1, 31),
            periodicidade="mensal", duracao_tipo="quantidade", duracao_quantidade=3,
        )
        self.assertEqual([d for d, _ in gerado], [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31)])

    def test_sem_data_de_termino_nao_mostra_total(self):
        texto = self._previa(
            classificacao="recorrente", valor="500", data_vencimento="2026-10-10",
            periodicidade="mensal", duracao_tipo="indeterminado",
        )
        self.assertEqual(texto, "R$ 500,00 por mês, sem data de término, a partir de 10/10/2026.")

    def test_uma_unica_cobranca(self):
        texto = self._previa(
            classificacao="recorrente", valor="500", data_vencimento="2026-10-10",
            periodicidade="mensal", duracao_tipo="quantidade", duracao_quantidade="1",
        )
        self.assertEqual(texto, "1 cobrança de R$ 500,00, em 10/10/2026.")


class TestPreviaDadosInvalidos(PreviaBase):
    def test_dados_incompletos_ou_invalidos_nao_geram_previa(self):
        casos = [
            {"classificacao": "unica", "valor": "100", "data_vencimento": "2026-10-10"},
            {"classificacao": "parcelado", "valor": "100", "data_vencimento": "2026-10-10", "numero_parcelas": "1"},
            {"classificacao": "parcelado", "valor": "", "data_vencimento": "2026-10-10", "numero_parcelas": "3"},
            {"classificacao": "parcelado", "valor": "abc", "data_vencimento": "2026-10-10", "numero_parcelas": "3"},
            {"classificacao": "recorrente", "valor": "100", "data_vencimento": "2026-10-10",
             "periodicidade": "mensal", "duracao_tipo": "data_final", "duracao_data_final": "2026-10-01"},
            {"classificacao": "recorrente", "valor": "100", "data_vencimento": "2026-10-10",
             "periodicidade": "semanal", "duracao_tipo": "indeterminado"},
            {"classificacao": "recorrente", "valor": "100", "data_vencimento": "2026-10-10",
             "periodicidade": "mensal", "duracao_tipo": "quantidade", "duracao_quantidade": "999999999"},
        ]
        for params in casos:
            with self.subTest(params=params):
                self.assertEqual(self._previa(**params), "")

    def test_sem_permissao_no_financeiro_e_recusado(self):
        User.objects.create_user(username="sem_financeiro", password="x")
        self.client.logout()
        self.client.login(username="sem_financeiro", password="x")
        resposta = self.client.get(URL_PREVIA, {"classificacao": "parcelado"}, HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 403)

    def test_previa_nao_grava_nada(self):
        self._previa(classificacao="parcelado", valor="1000", data_vencimento="2026-10-10", numero_parcelas="3")
        self.assertFalse(LancamentoFinanceiro.objects.exists())


class TestRotulosDosFormularios(PreviaBase):
    def test_lancamento_novo_mostra_rotulos_e_previa(self):
        html = self.client.get("/financeiro/lancamentos/novo/", HTTP_HOST=self.http_host).content.decode()
        for texto in ("Valor de cada cobrança (R$)", "Sem data de término", "Termina em uma data",
                      "Termina após N cobranças", "Número de cobranças", 'id="previa-ocorrencias"'):
            self.assertIn(texto, html)

    def test_lancamento_editado_nao_mostra_previa(self):
        lancamento = self._lancamento()
        html = self.client.get(
            f"/financeiro/lancamentos/{lancamento.pk}/editar/", HTTP_HOST=self.http_host,
        ).content.decode()
        self.assertIn("Valor desta cobrança (R$)", html)
        self.assertNotIn('id="previa-ocorrencias"', html)

    def test_honorario_novo_mostra_rotulos_e_previa(self):
        resposta = self.client.get("/financeiro/honorarios/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(resposta.status_code, 200)
        html = resposta.content.decode()
        for texto in ("Valor total (R$)", "Valor de cada cobrança (R$)", "Termina após N cobranças",
                      "Número de cobranças", 'id="previa-ocorrencias"'):
            self.assertIn(texto, html)
