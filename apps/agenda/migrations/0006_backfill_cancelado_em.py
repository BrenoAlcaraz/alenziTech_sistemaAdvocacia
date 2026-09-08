from django.db import migrations
from django.utils import timezone


def backfill_cancelado_em(apps, schema_editor):
    """
    Compromisso cancelado antes desta feature não tem `cancelado_em`
    registrado. Sem isso, o job `expurgar_compromissos_cancelados` nunca
    os expurga (`cancelado_em__lte=limite` nunca é verdadeiro para
    NULL) — ficariam retidos para sempre, contrariando a regra de
    retenção de 7 dias. Usa o momento desta migration como início da
    janela de retenção para esses registros legados.
    """
    Compromisso = apps.get_model("agenda", "Compromisso")
    Compromisso.objects.filter(
        status="cancelado", cancelado_em__isnull=True
    ).update(cancelado_em=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0005_compromisso_cancelado_em"),
    ]

    operations = [
        migrations.RunPython(backfill_cancelado_em, migrations.RunPython.noop),
    ]
