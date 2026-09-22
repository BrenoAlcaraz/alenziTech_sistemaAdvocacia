"""
Rótulo exibido da área do direito "CÍVEL" é "Civil" (não "Cível") —
o valor salvo no banco (`"CÍVEL"`) não muda, só o texto exibido, aqui
e em Modelos (que reusa `Processo.AREAS_CHOICES`, ver
test_area_eleitoral_removida.py).
"""

from django.test import SimpleTestCase

from apps.modelos.forms import AREAS_DIREITO
from apps.processos.models import Processo


class TestRotuloCivelViraCivil(SimpleTestCase):
    def test_rotulo_de_processo(self):
        self.assertEqual(dict(Processo.AREAS_CHOICES)["CÍVEL"], "Civil")

    def test_rotulo_reusado_em_modelos(self):
        self.assertEqual(dict(AREAS_DIREITO)["CÍVEL"], "Civil")
