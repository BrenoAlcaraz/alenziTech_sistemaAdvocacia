import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def remover_clientes_sem_responsavel(apps, schema_editor):
    Cliente = apps.get_model("clientes", "Cliente")
    Cliente.objects.filter(responsavel__isnull=True).delete()


def noop_reverso(apps, schema_editor):
    # Não é possível recriar registros removidos ao reverter esta migration.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0005_remove_cliente_departamento'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(remover_clientes_sem_responsavel, noop_reverso),
        migrations.AlterField(
            model_name='cliente',
            name='responsavel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='clientes_responsaveis', to=settings.AUTH_USER_MODEL, verbose_name='Responsável'),
        ),
    ]
