import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_rename_departamento_equipe'),
        ('processos', '0003_processo_departamento'),
    ]

    operations = [
        migrations.RenameField(
            model_name='processo',
            old_name='departamento',
            new_name='equipe',
        ),
        migrations.AlterField(
            model_name='processo',
            name='equipe',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='processos',
                to='accounts.equipe',
                verbose_name='Equipe',
            ),
        ),
    ]
