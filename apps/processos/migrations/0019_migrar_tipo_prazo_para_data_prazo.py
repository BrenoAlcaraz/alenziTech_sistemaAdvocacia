from django.db import migrations


def migrar_prazo_para_data_prazo(apps, schema_editor):
    MovimentacaoProcessual = apps.get_model("processos", "MovimentacaoProcessual")
    for mov in MovimentacaoProcessual.objects.filter(tipo="prazo"):
        mov.data_prazo = mov.data.date()
        mov.tipo = "outro"
        mov.save(update_fields=["data_prazo", "tipo"])


def desfazer_migracao(apps, schema_editor):
    # Best-effort: não há marcador que distinga um "outro" pré-existente
    # de um migrado por esta migration — a heurística assume que todo
    # "outro" com data_prazo igual à própria data é um retorno seguro.
    MovimentacaoProcessual = apps.get_model("processos", "MovimentacaoProcessual")
    for mov in MovimentacaoProcessual.objects.filter(tipo="outro", data_prazo__isnull=False):
        if mov.data_prazo == mov.data.date():
            mov.tipo = "prazo"
            mov.data_prazo = None
            mov.save(update_fields=["tipo", "data_prazo"])


class Migration(migrations.Migration):
    dependencies = [
        ("processos", "0018_movimentacao_prazo_como_atributo"),
    ]

    operations = [
        migrations.RunPython(migrar_prazo_para_data_prazo, desfazer_migracao),
    ]
