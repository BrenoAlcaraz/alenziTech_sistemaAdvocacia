from django.db import migrations

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


class Migration(migrations.Migration):

    dependencies = [
        ("modelos", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(popular_categorias, migrations.RunPython.noop),
    ]
