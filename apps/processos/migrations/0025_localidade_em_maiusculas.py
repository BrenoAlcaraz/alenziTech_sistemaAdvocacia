from django.db import migrations
from django.db.models.functions import Trim, Upper


def para_maiusculas(apps, schema_editor):
    """Uniformiza textos de localidade/nome já gravados — a mesma cidade
    escrita de dois jeitos aparecia como duas na Análise de dados."""
    Modelo = apps.get_model("processos", "Processo")
    Modelo.objects.update(**{campo: Upper(Trim(campo)) for campo in ['cidade', 'comarca', 'vara']})


class Migration(migrations.Migration):

    dependencies = [
        ("processos", "0024_processo_status_sobrestado"),
    ]

    operations = [
        migrations.RunPython(para_maiusculas, migrations.RunPython.noop),
    ]
