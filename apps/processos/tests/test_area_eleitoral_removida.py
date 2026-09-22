"""
"Eleitoral" saiu do catálogo de área do direito (specs/remover-area-eleitoral.md):
o catálogo único (`Processo.AREAS_CHOICES`, reusado por Modelos) não a oferece.
"""

from django.test import SimpleTestCase

from apps.modelos.forms import AREAS_DIREITO
from apps.processos.forms import ProcessoForm
from apps.processos.models import Processo


class TestCatalogoSemEleitoral(SimpleTestCase):
    def test_catalogo_de_processo_nao_tem_eleitoral(self):
        self.assertNotIn("ELEITORAL", dict(Processo.AREAS_CHOICES))

    def test_catalogo_de_modelos_nao_tem_eleitoral(self):
        self.assertNotIn("ELEITORAL", dict(AREAS_DIREITO))

    def test_form_de_processo_rejeita_eleitoral(self):
        form = ProcessoForm(data={
            "titulo": "Processo", "area_direito": "ELEITORAL", "fase": "conhecimento",
            "instancia": "1ª Instância", "gratuidade_justica_status": "nao_requerida",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("area_direito", form.errors)
