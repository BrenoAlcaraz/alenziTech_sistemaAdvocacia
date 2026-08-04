import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_departamento_membrodepartamento'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # Garante que clientes.0004 (FK → accounts.Departamento) roda antes do rename.
        # Sem isso, o sort topológico pode colocar este rename antes de clientes.0004,
        # invalidando a referência ao model 'accounts.departamento'.
        ('clientes', '0005_remove_cliente_departamento'),
        # Mesmo motivo para processos.0003 (FK → accounts.Departamento).
        ('processos', '0003_processo_departamento'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Departamento',
            new_name='Equipe',
        ),
        migrations.RenameModel(
            old_name='MembroDepartamento',
            new_name='MembroEquipe',
        ),
        migrations.RenameField(
            model_name='equipe',
            old_name='departamento_pai',
            new_name='equipe_pai',
        ),
        migrations.AlterField(
            model_name='equipe',
            name='equipe_pai',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='subequipes',
                to='accounts.equipe',
            ),
        ),
        migrations.RenameField(
            model_name='membroequipe',
            old_name='departamento',
            new_name='equipe',
        ),
        migrations.AlterField(
            model_name='membroequipe',
            name='usuario',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='membros_equipe',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='membroequipe',
            name='uniq_usuario_departamento',
        ),
        migrations.AddConstraint(
            model_name='membroequipe',
            constraint=models.UniqueConstraint(
                fields=['usuario', 'equipe'],
                name='uniq_usuario_equipe',
            ),
        ),
        migrations.AlterModelOptions(
            name='equipe',
            options={
                'ordering': ['nome'],
                'verbose_name': 'Equipe',
                'verbose_name_plural': 'Equipes',
            },
        ),
        migrations.AlterModelOptions(
            name='membroequipe',
            options={
                'verbose_name': 'Membro de Equipe',
                'verbose_name_plural': 'Membros de Equipe',
            },
        ),
    ]
