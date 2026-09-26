"""
Sub-aba Precatório de Honorários: sucumbências pagas pela Fazenda, com
sugestão de regime (RPV/precatório) por esfera e teto, e regime gravado só
por escolha do usuário.
"""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from apps.financeiro.models import Honorario
from apps.financeiro.precatorio import sugerir_regime
from apps.processos.forms import ParteProcessoForm
from apps.processos.models import ParteProcesso

from .test_honorario_sucumbencial import HonorarioSucumbencialBase

DATA_2026 = date(2026, 6, 1)
SALARIO_2026 = Decimal("1621.00")


class TestSugestaoDeRegime(SimpleTestCase):
    def test_federal_acima_de_60_salarios_sugere_precatorio(self):
        s = sugerir_regime(esferas=["federal"], valor=SALARIO_2026 * 60 + 1, data=DATA_2026)
        self.assertEqual(s["regime"], "precatorio")
        self.assertEqual(s["limite"], SALARIO_2026 * 60)

    def test_federal_no_teto_exato_sugere_rpv(self):
        s = sugerir_regime(esferas=["federal"], valor=SALARIO_2026 * 60, data=DATA_2026)
        self.assertEqual(s["regime"], "rpv")

    def test_estadual_usa_40_salarios_com_aviso_de_lei_propria(self):
        s = sugerir_regime(esferas=["estadual"], valor=SALARIO_2026 * 40 + 1, data=DATA_2026)
        self.assertEqual(s["regime"], "precatorio")
        self.assertIn("lei própria", s["motivo"])

    def test_municipal_nao_sugere(self):
        s = sugerir_regime(esferas=["municipal"], valor=Decimal("1000000"), data=DATA_2026)
        self.assertIsNone(s["regime"])

    def test_sem_esfera_pede_para_informar(self):
        s = sugerir_regime(esferas=[], valor=Decimal("1000000"), data=DATA_2026)
        self.assertIsNone(s["regime"])
        self.assertIn("Informe a esfera", s["motivo"])

    def test_mais_de_uma_esfera_nao_sugere(self):
        s = sugerir_regime(esferas=["estadual", "federal"], valor=Decimal("1"), data=DATA_2026)
        self.assertIsNone(s["regime"])

    def test_ano_sem_tabela_usa_o_ultimo_salario_conhecido(self):
        s = sugerir_regime(esferas=["federal"], valor=Decimal("1"), data=date(2030, 1, 1))
        self.assertEqual(s["limite"], SALARIO_2026 * 60)


class TestAbaPrecatorio(HonorarioSucumbencialBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_precatorio"

    def _parte_publica(self, esfera, papel="reu"):
        return ParteProcesso.objects.create(processo=self.processo, papel=papel, nome="Ente", ente_publico=esfera)

    def _lista(self):
        r = self.client.get("/financeiro/honorarios/?aba=precatorio", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        return r.context["honorarios_precatorio"]

    def test_lista_so_sucumbencia_contra_ente_publico(self):
        contra_ente = self._honorario()
        self._parte_publica("federal")
        outro_processo = self.processo.__class__.objects.create(criado_por=self.user, titulo="Privado")
        self._honorario(processo=outro_processo)
        Honorario.objects.create(tipo="contratual", valor_estimado=Decimal("10"), processo=self.processo)
        self._honorario(status="cancelado")
        self.assertEqual([h.pk for h in self._lista()], [contra_ente.pk])

    def test_devedor_ente_estatal_entra_mesmo_sem_parte_marcada(self):
        h = self._honorario(devedor_tipo="ente_estatal", indice_correcao="selic", data_juros=None)
        [item] = self._lista()
        self.assertEqual(item.pk, h.pk)
        self.assertIsNone(item.sugestao_regime["regime"])

    def test_parte_publica_em_outros_nao_conta(self):
        self._honorario()
        self._parte_publica("federal", papel="ministerio_publico")
        self.assertEqual(self._lista(), [])

    def test_valor_comparado_e_so_a_sucumbencia(self):
        self._honorario()
        self._parte_publica("federal")
        Honorario.objects.create(
            tipo="contratual", modalidade="exito", valor_estimado=Decimal("0"), exito_percentual=Decimal("20"),
            exito_base="ganho", processo=self.processo, cliente=self.cliente,
        )
        [item] = self._lista()
        self.assertEqual(item.valor_precatorio, item.calculo["sucumbencia"])
        self.assertLess(item.valor_precatorio, item.calculo["total"])

    def test_regime_so_muda_por_escolha_do_usuario(self):
        h = self._honorario()
        self._parte_publica("federal")
        self._lista()
        h.refresh_from_db()
        self.assertEqual(h.regime_pagamento, "")

        r = self.client.post(
            f"/financeiro/honorarios/{h.pk}/regime/", {"regime_pagamento": "precatorio"}, HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, "/financeiro/honorarios/?aba=precatorio", fetch_redirect_response=False)
        h.refresh_from_db()
        self.assertEqual(h.regime_pagamento, "precatorio")

        self.client.post(f"/financeiro/honorarios/{h.pk}/regime/", {"regime_pagamento": "xyz"}, HTTP_HOST=self.http_host)
        h.refresh_from_db()
        self.assertEqual(h.regime_pagamento, "precatorio")

    def test_formulario_da_parte_grava_ente_publico(self):
        form = ParteProcessoForm(
            {"papel": "reu", "nome": "INSS", "ente_publico": "federal"}, processo=self.processo,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.processo = self.processo
        self.assertEqual(form.save().ente_publico, "federal")
