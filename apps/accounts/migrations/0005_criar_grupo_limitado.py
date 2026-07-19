from django.db import migrations


def criar_grupo_limitado(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="limitado")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_rename_departamento_equipe"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(criar_grupo_limitado, migrations.RunPython.noop),
    ]
