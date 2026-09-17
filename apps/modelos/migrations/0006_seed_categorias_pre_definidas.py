from django.db import migrations

# Catálogo inicial de "Tipo de peça" (spec
# modelos-catalogo-tipos-pre-definido) — tipos mais comuns, para o
# escritório não precisar criar do zero. "Procuração" também serve de
# base ao botão "Gerar procuração" de Clientes (spec
# clientes-gerar-procuracao).
CATEGORIAS_PRE_DEFINIDAS = [
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


def popular_categorias(apps, schema_editor):
    CategoriaModeloPeca = apps.get_model("modelos", "CategoriaModeloPeca")
    for nome in CATEGORIAS_PRE_DEFINIDAS:
        CategoriaModeloPeca.objects.get_or_create(nome=nome)


def reverter(apps, schema_editor):
    CategoriaModeloPeca = apps.get_model("modelos", "CategoriaModeloPeca")
    CategoriaModeloPeca.objects.filter(
        nome__in=CATEGORIAS_PRE_DEFINIDAS, modelos__isnull=True, versaomodelopeca__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("modelos", "0005_unificar_area_direito_processo"),
    ]

    operations = [
        migrations.RunPython(popular_categorias, reverter),
    ]
