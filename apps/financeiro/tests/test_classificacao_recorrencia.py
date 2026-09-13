"""
Testes da classificação Única/Parcelado/Recorrente em
LancamentoFinanceiro (PDR-0021,
specs/financeiro-visao-grafica-navegacao-temporal.md).

Segue o mesmo padrão de fixtures de
apps/financeiro/tests/test_autorizacao.py sobre
django_tenants.test.cases.TenantTestCase.
"""

from datetime import date

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.financeiro.forms import LancamentoFinanceiroForm
from apps.financeiro.models import LancamentoFinanceiro
from apps.financeiro.services import cancelar_ocorrencias_futuras, gerar_ocorrencias


class ClassificacaoRecorrenciaBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "financeiro_classificacao_recorrencia"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"
        self.user = User.objects.create_user(username="financeiro_user", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Financeiro", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(self.user)

    def _lancamento(self, **kwargs):
        defaults = {
            "tipo": "despesa",
            "descricao": "Aluguel",
            "valor": "1000.00",
            "data_vencimento": date(2026, 1, 15),
            "status": "pendente",
        }
        defaults.update(kwargs)
        return LancamentoFinanceiro.objects.create(**defaults)


class TestGeracaoDeParcelas(ClassificacaoRecorrenciaBase):
    def test_parcelado_gera_ocorrencias_mensais_vinculadas_a_origem(self):
        origem = self._lancamento(classificacao="parcelado", numero_parcelas=3)
        gerar_ocorrencias(origem)
        origem.refresh_from_db()

        ocorrencias = list(origem.ocorrencias.order_by("data_vencimento"))
        self.assertEqual(len(ocorrencias), 2)
        self.assertEqual(ocorrencias[0].data_vencimento, date(2026, 2, 15))
        self.assertEqual(ocorrencias[1].data_vencimento, date(2026, 3, 15))
        for ocorrencia in ocorrencias:
            self.assertEqual(ocorrencia.lancamento_origem_id, origem.pk)
            self.assertEqual(ocorrencia.status, "pendente")
            self.assertEqual(ocorrencia.valor, origem.valor)

    def test_gerar_ocorrencias_e_idempotente(self):
        origem = self._lancamento(classificacao="parcelado", numero_parcelas=3)
        gerar_ocorrencias(origem)
        gerar_ocorrencias(origem)
        self.assertEqual(origem.ocorrencias.count(), 2)


class TestGeracaoDeRecorrencia(ClassificacaoRecorrenciaBase):
    def test_recorrente_mensal_por_quantidade(self):
        origem = self._lancamento(
            classificacao="recorrente", periodicidade="mensal",
            duracao_tipo="quantidade", duracao_quantidade=4,
        )
        gerar_ocorrencias(origem)
        datas = list(origem.ocorrencias.order_by("data_vencimento").values_list("data_vencimento", flat=True))
        self.assertEqual(datas, [date(2026, 2, 15), date(2026, 3, 15), date(2026, 4, 15)])

    def test_recorrente_anual_por_data_final(self):
        origem = self._lancamento(
            classificacao="recorrente", periodicidade="anual",
            duracao_tipo="data_final", duracao_data_final=date(2029, 1, 15),
        )
        gerar_ocorrencias(origem)
        datas = list(origem.ocorrencias.order_by("data_vencimento").values_list("data_vencimento", flat=True))
        self.assertEqual(datas, [date(2027, 1, 15), date(2028, 1, 15), date(2029, 1, 15)])

    def test_recorrente_indeterminado_usa_horizonte_fixo(self):
        origem = self._lancamento(
            classificacao="recorrente", periodicidade="mensal", duracao_tipo="indeterminado",
        )
        gerar_ocorrencias(origem)
        self.assertEqual(origem.ocorrencias.count(), 23)

    def test_ocorrencia_gerada_nao_gera_suas_proprias_ocorrencias(self):
        origem = self._lancamento(
            classificacao="recorrente", periodicidade="mensal",
            duracao_tipo="quantidade", duracao_quantidade=3,
        )
        gerar_ocorrencias(origem)
        ocorrencia = origem.ocorrencias.first()
        gerar_ocorrencias(ocorrencia)
        self.assertEqual(ocorrencia.ocorrencias.count(), 0)


class TestCancelarRecorrenciaFutura(ClassificacaoRecorrenciaBase):
    def setUp(self):
        super().setUp()
        self.origem = self._lancamento(
            classificacao="recorrente", periodicidade="mensal",
            duracao_tipo="quantidade", duracao_quantidade=4,
            data_vencimento=date(2020, 1, 15),  # já no passado
        )
        gerar_ocorrencias(self.origem)
        self.ocorrencias = list(self.origem.ocorrencias.order_by("data_vencimento"))

    def test_cancelar_recorrencia_nao_afeta_ocorrencia_ja_paga(self):
        paga = self.ocorrencias[0]
        paga.status = "pago"
        paga.data_pagamento = paga.data_vencimento
        paga.save(update_fields=["status", "data_pagamento"])

        cancelar_ocorrencias_futuras(self.origem)

        paga.refresh_from_db()
        self.assertEqual(paga.status, "pago")

    def test_cancelar_recorrencia_nao_afeta_pendente_ja_vencida(self):
        vencida = self.ocorrencias[1]  # continua pendente, mas no passado
        cancelar_ocorrencias_futuras(self.origem)
        vencida.refresh_from_db()
        self.assertEqual(vencida.status, "pendente")

    def test_cancelar_recorrencia_cancela_pendente_futura(self):
        futura = self._lancamento(
            classificacao="recorrente", periodicidade="mensal",
            data_vencimento=date(2099, 1, 1), lancamento_origem=self.origem,
        )
        cancelar_ocorrencias_futuras(self.origem)
        futura.refresh_from_db()
        self.assertEqual(futura.status, "cancelado")

    def test_cancelar_a_partir_de_uma_ocorrencia_afeta_o_grupo_todo(self):
        futura = self._lancamento(
            classificacao="recorrente", periodicidade="mensal",
            data_vencimento=date(2099, 1, 1), lancamento_origem=self.origem,
        )
        outra_ocorrencia_qualquer = self.ocorrencias[1]
        cancelar_ocorrencias_futuras(outra_ocorrencia_qualquer)
        futura.refresh_from_db()
        self.assertEqual(futura.status, "cancelado")


class TestFormValidaClassificacao(ClassificacaoRecorrenciaBase):
    def _dados_base(self, **extra):
        dados = {
            "tipo": "despesa",
            "descricao": "Teste",
            "valor": "100.00",
            "data_vencimento": "2026-01-15",
            "categoria": "outro",
            "status": "pendente",
            "classificacao": "unica",
        }
        dados.update(extra)
        return dados

    def test_parcelado_exige_ao_menos_duas_parcelas(self):
        form = LancamentoFinanceiroForm(data=self._dados_base(classificacao="parcelado", numero_parcelas=1))
        self.assertFalse(form.is_valid())
        self.assertIn("numero_parcelas", form.errors)

    def test_recorrente_exige_periodicidade(self):
        form = LancamentoFinanceiroForm(data=self._dados_base(
            classificacao="recorrente", duracao_tipo="indeterminado",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("periodicidade", form.errors)

    def test_recorrente_por_data_final_exige_data_posterior_ao_vencimento(self):
        form = LancamentoFinanceiroForm(data=self._dados_base(
            classificacao="recorrente", periodicidade="mensal",
            duracao_tipo="data_final", duracao_data_final="2026-01-01",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("duracao_data_final", form.errors)

    def test_recorrente_valido_e_aceito(self):
        form = LancamentoFinanceiroForm(data=self._dados_base(
            classificacao="recorrente", periodicidade="mensal", duracao_tipo="indeterminado",
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_editar_ocorrencia_gerada_nao_exige_duracao(self):
        origem = self._lancamento(
            classificacao="recorrente", periodicidade="mensal",
            duracao_tipo="quantidade", duracao_quantidade=3,
        )
        gerar_ocorrencias(origem)
        ocorrencia = origem.ocorrencias.first()

        form = LancamentoFinanceiroForm(
            data=self._dados_base(
                classificacao="recorrente",
                data_vencimento=ocorrencia.data_vencimento.isoformat(),
                descricao="Descrição editada",
            ),
            instance=ocorrencia,
        )
        self.assertTrue(form.is_valid(), form.errors)
