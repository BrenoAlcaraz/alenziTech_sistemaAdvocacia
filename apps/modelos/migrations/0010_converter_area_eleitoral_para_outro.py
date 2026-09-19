from django.db import migrations


def converter_eleitoral_para_outro(apps, schema_editor):
    # `area_direito` de Modelo de Peças é texto livre reusando o catálogo de
    # Processo.AREAS_CHOICES; "Eleitoral" saiu do catálogo.
    for nome_modelo in ("ModeloPeca", "VersaoModeloPeca"):
        modelo = apps.get_model("modelos", nome_modelo)
        modelo.objects.filter(area_direito="ELEITORAL").update(area_direito="OUTRO")


class Migration(migrations.Migration):

    dependencies = [
        ("modelos", "0009_modelopeca_cliente"),
    ]

    operations = [
        # Reversa no-op: a informação "era Eleitoral" não é recuperável.
        migrations.RunPython(converter_eleitoral_para_outro, migrations.RunPython.noop),
    ]
