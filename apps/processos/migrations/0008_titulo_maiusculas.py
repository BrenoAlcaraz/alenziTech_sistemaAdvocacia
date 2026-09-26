from django.db import migrations


def titulos_em_maiusculas(apps, schema_editor):
    # Mesmo `str.upper()` do formulário, para o título gravado antes e
    # depois da regra ficar idêntico.
    Processo = apps.get_model("processos", "Processo")
    for processo in Processo.objects.only("pk", "titulo").iterator():
        titulo = processo.titulo.strip().upper()
        if titulo != processo.titulo:
            Processo.objects.filter(pk=processo.pk).update(titulo=titulo)


class Migration(migrations.Migration):

    dependencies = [
        ("processos", "0007_avisos_complementares_acompanhamento"),
    ]

    operations = [
        migrations.RunPython(titulos_em_maiusculas, migrations.RunPython.noop),
    ]
