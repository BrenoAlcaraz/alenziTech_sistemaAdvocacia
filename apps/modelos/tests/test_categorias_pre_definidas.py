"""
Testes do catálogo pré-definido de "Tipo de peça"
(specs/modelos-catalogo-tipos-pre-definido.md).

Cobre: tenant novo já nasce com os 15 tipos; tenant existente recebe os
15 tipos ao rodar a migration sem duplicar categoria já existente com o
mesmo nome; cada tipo pré-cadastrado é editável/excluível como qualquer
categoria criada manualmente.
"""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
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


class TestMigrationNaoDuplicaCategoriaExistente(TenantTestCase):
    """Roda a migration 0006 sobre um tenant que já tem, manualmente,
    uma categoria com o mesmo nome de uma das pré-definidas — não deve
    duplicar (regra de negócio: `nome` é único)."""

    @classmethod
    def get_test_schema_name(cls):
        return "modelos_catalogo_sem_duplicar"

    def test_categoria_ja_existente_nao_duplica_ao_rodar_migration(self):
        executor = MigrationExecutor(connection)
        alvo_antes = [("modelos", "0005_unificar_area_direito_processo")]
        executor.migrate(alvo_antes)

        executor = MigrationExecutor(connection)
        estado = executor.loader.project_state(alvo_antes).apps
        CategoriaHistorica = estado.get_model("modelos", "CategoriaModeloPeca")
        CategoriaHistorica.objects.create(nome="Contestação")

        executor = MigrationExecutor(connection)
        alvo_depois = [("modelos", "0006_seed_categorias_pre_definidas")]
        executor.migrate(alvo_depois)

        self.assertEqual(
            CategoriaModeloPeca.objects.filter(nome="Contestação").count(), 1
        )
        self.assertEqual(CategoriaModeloPeca.objects.count(), len(CATEGORIAS_ESPERADAS))
