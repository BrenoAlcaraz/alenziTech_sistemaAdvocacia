from django.db import migrations
from django.db.models import F


def backfill_criado_por(apps, schema_editor):
    """
    Compromisso criado antes desta feature não tem `criado_por`
    registrado — não há como recuperar quem de fato criou. Usa o
    `responsavel` como melhor aproximação disponível, o que também
    evita que registros legados apareçam incorretamente na sub-aba
    "Adicionado por terceiro" (que compara `criado_por` com
    `responsavel`).
    """
    Compromisso = apps.get_model("agenda", "Compromisso")
    Compromisso.objects.filter(criado_por__isnull=True).update(
        criado_por=F("responsavel_id")
    )


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0007_compromisso_criado_por"),
    ]

    operations = [
        migrations.RunPython(backfill_criado_por, migrations.RunPython.noop),
    ]
