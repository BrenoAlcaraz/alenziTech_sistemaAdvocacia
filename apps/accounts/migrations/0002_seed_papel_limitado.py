from django.db import migrations


def criar_papel_limitado(apps, schema_editor):
    PapelAcesso = apps.get_model("accounts", "PapelAcesso")
    PapelAcesso.objects.get_or_create(
        codigo_preset="limitado",
        defaults={
            "nome": "Limitado",
            "descricao": "Papel padrão de fábrica: nenhum módulo nem habilitação liberados.",
            "protegido_sistema": True,
            "ativo": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(criar_papel_limitado, migrations.RunPython.noop),
    ]
