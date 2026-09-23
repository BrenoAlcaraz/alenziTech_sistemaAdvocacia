from django.db import migrations, models


def numerar_existentes(apps, schema_editor):
    """Numera os registros já existentes pela ordem de criação."""
    Modelo = apps.get_model("clientes", "Cliente")
    SequenciaCodigoInterno = apps.get_model("accounts", "SequenciaCodigoInterno")
    numero = 0
    for registro in Modelo.objects.order_by("pk"):
        numero += 1
        registro.numero_interno = numero
        registro.save(update_fields=["numero_interno"])
    SequenciaCodigoInterno.objects.update_or_create(
        entidade="cliente", defaults={"ultimo_numero": numero},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_codigo_interno"),
        ("clientes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="numero_interno",
            field=models.PositiveIntegerField(editable=False, null=True, unique=True),
        ),
        migrations.RunPython(numerar_existentes, migrations.RunPython.noop),
    ]
