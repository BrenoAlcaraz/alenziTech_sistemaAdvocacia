"""
Testes do catálogo pré-definido de "Tipo de peça"
(specs/modelos-catalogo-tipos-pre-definido.md).

Cobre: tenant novo já nasce com os 15 tipos; cada tipo pré-cadastrado é
editável/excluível como qualquer categoria criada manualmente.
"""

from django_tenants.test.cases import TenantTestCase

from apps.modelos.models import CategoriaModeloPeca

CATEGORIAS_ESPERADAS = [
    "Petição inicial",
    "Contestação",
    "Réplica",
    "Alegações finais",
    "Apelação",
    "Embargos de declaração",
    "Agravo de instrumento",
    "Agravo interno",
    "Recurso especial",
    "Recurso extraordinário",
    "Quesitos técnicos",
    "Petição de mero andamento",
    "Exceção de pré-executividade",
    "Embargos infringentes",
    "Procuração",
]


class TestTenantNovoJaNasceComCatalogo(TenantTestCase):
    """TenantTestCase cria o schema já rodando todas as migrations —
    equivale ao provisionamento de um tenant novo."""

    @classmethod
    def get_test_schema_name(cls):
        return "modelos_catalogo_tenant_novo"

    def test_lista_os_15_tipos_sem_acao_manual(self):
        nomes = set(CategoriaModeloPeca.objects.values_list("nome", flat=True))
        for esperado in CATEGORIAS_ESPERADAS:
            self.assertIn(esperado, nomes)
        self.assertEqual(CategoriaModeloPeca.objects.count(), len(CATEGORIAS_ESPERADAS))

    def test_categoria_pre_cadastrada_pode_ser_editada_e_excluida(self):
        categoria = CategoriaModeloPeca.objects.get(nome="Réplica")
        categoria.nome = "Réplica (renomeada)"
        categoria.save()
        self.assertTrue(
            CategoriaModeloPeca.objects.filter(nome="Réplica (renomeada)").exists()
        )
        categoria.delete()
        self.assertFalse(
            CategoriaModeloPeca.objects.filter(pk=categoria.pk).exists()
        )
