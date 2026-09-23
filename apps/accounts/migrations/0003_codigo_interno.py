from django.db import migrations, models


def numerar_usuarios_existentes(apps, schema_editor):
    """Numera perfis comuns já existentes pela ordem de criação e abre a
    sequência de cada entidade (Processo e Cliente continuam do total
    que suas próprias migrations numerarem)."""
    PerfilUsuario = apps.get_model("accounts", "PerfilUsuario")
    SequenciaCodigoInterno = apps.get_model("accounts", "SequenciaCodigoInterno")
    numero = 0
    for perfil in PerfilUsuario.objects.filter(is_admin_escritorio=False).order_by("pk"):
        numero += 1
        perfil.numero_interno = numero
        perfil.save(update_fields=["numero_interno"])
    SequenciaCodigoInterno.objects.create(entidade="usuario", ultimo_numero=numero)
    SequenciaCodigoInterno.objects.get_or_create(entidade="processo")
    SequenciaCodigoInterno.objects.get_or_create(entidade="cliente")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_seed_papel_limitado"),
    ]

    operations = [
        migrations.CreateModel(
            name="SequenciaCodigoInterno",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entidade", models.CharField(choices=[("processo", "Processo"), ("cliente", "Cliente"), ("usuario", "Usuário")], max_length=20, unique=True)),
                ("ultimo_numero", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Sequência de código interno",
                "verbose_name_plural": "Sequências de código interno",
            },
        ),
        migrations.AddField(
            model_name="perfilusuario",
            name="numero_interno",
            field=models.PositiveIntegerField(blank=True, editable=False, help_text="Número do código interno U. Vazio para o Administrador (ADM).", null=True, unique=True),
        ),
        migrations.RunPython(numerar_usuarios_existentes, migrations.RunPython.noop),
    ]
