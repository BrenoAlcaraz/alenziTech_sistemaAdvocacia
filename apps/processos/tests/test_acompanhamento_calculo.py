"""
Acompanhamento DJEN — regras puras (PDR-0037): motor de dias úteis,
extração do prazo do texto da intimação e número CNJ válido.
"""

from datetime import date

from django.test import SimpleTestCase, override_settings

from apps.processos.acompanhamento import numero_cnj_valido
from apps.processos.dias_uteis import (
    data_publicacao_djen,
    eh_dia_util,
    vencimento_intimacao_djen,
)
from apps.processos.extracao_prazo import PrazoExtraido, extrair_prazo


class TestDiasUteis(SimpleTestCase):
    def test_exemplo_da_spec_01_10_2026_com_15_dias_vence_26_10_2026(self):
        # Publicada 02/10; conta de 05/10 pulando o feriado de 12/10.
        self.assertEqual(data_publicacao_djen(date(2026, 10, 1)), date(2026, 10, 2))
        self.assertEqual(vencimento_intimacao_djen(date(2026, 10, 1), 15), date(2026, 10, 26))

    def test_recesso_nao_muda_publicacao_e_suspende_a_contagem(self):
        self.assertEqual(data_publicacao_djen(date(2026, 12, 22)), date(2026, 12, 23))
        self.assertEqual(vencimento_intimacao_djen(date(2026, 12, 22), 1), date(2027, 1, 21))

    def test_dias_corridos_contam_fim_de_semana_e_feriado(self):
        # Publicada 02/10 (sexta); 3 dias corridos: 03, 04, 05/10.
        self.assertEqual(vencimento_intimacao_djen(date(2026, 10, 1), 3, corridos=True), date(2026, 10, 5))

    def test_sexta_feira_santa_e_feriado_movel(self):
        self.assertFalse(eh_dia_util(date(2027, 3, 26)))
        self.assertTrue(eh_dia_util(date(2027, 3, 25)))

    @override_settings(FERIADOS_NACIONAIS=[], FERIADOS_AVULSOS=["2026-10-05"])
    def test_lista_de_feriados_vem_da_configuracao(self):
        self.assertTrue(eh_dia_util(date(2026, 10, 12)))
        self.assertFalse(eh_dia_util(date(2026, 10, 5)))


class TestExtracaoDoPrazo(SimpleTestCase):
    def test_um_prazo_em_dias(self):
        texto = "<p>Intime-se a parte autora para, no prazo de 15 (quinze) dias, manifestar-se.</p>"
        self.assertEqual(extrair_prazo(texto), PrazoExtraido(dias=15))

    def test_mesmo_prazo_repetido_conta_uma_vez(self):
        texto = "Prazo de 5 dias. Decorrido o prazo de 5 (cinco) dias, conclusos."
        self.assertEqual(extrair_prazo(texto), PrazoExtraido(dias=5))

    def test_periodo_que_nao_e_prazo_nao_atrapalha(self):
        # Trecho de intimação real do DJEN (TJSP, 24/09/2026).
        texto = (
            "apresente os extratos bancários relativos aos últimos três meses e os três "
            "últimos demonstrativos de vencimentos. Prazo: 10 dias, sob pena de indeferimento."
        )
        self.assertEqual(extrair_prazo(texto), PrazoExtraido(dias=10))

    def test_dias_corridos_expresso(self):
        self.assertEqual(extrair_prazo("no prazo de 10 dias corridos"), PrazoExtraido(dias=10, corridos=True))

    def test_casos_que_ficam_a_definir(self):
        for texto in [
            "Vistos. Cite-se.",
            "Manifestem-se em 15 dias; após, réplica em 10 dias.",
            "Cumpra-se em 48 horas.",
            "Recolha as custas no prazo legal.",
            "Manifeste-se no prazo de lei.",
            "Cumpra-se imediatamente.",
            "Prazo de 2 meses para juntada.",
            "Manifeste-se em cinco dias.",
        ]:
            with self.subTest(texto=texto):
                self.assertIsNone(extrair_prazo(texto))


class TestNumeroCnj(SimpleTestCase):
    def test_digito_verificador(self):
        self.assertTrue(numero_cnj_valido("4001054-83.2026.8.26.0595"))
        self.assertTrue(numero_cnj_valido("40010548320268260595"))
        self.assertFalse(numero_cnj_valido("4001054-84.2026.8.26.0595"))
        self.assertFalse(numero_cnj_valido("123"))
        self.assertFalse(numero_cnj_valido(""))
