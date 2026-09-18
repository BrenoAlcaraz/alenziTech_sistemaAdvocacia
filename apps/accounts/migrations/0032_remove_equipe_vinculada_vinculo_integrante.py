# Equipe como atalho de seleção (PDR-0028): remove o vínculo dinâmico de
# Equipe. As pessoas já materializadas continuam nas listas reais
# (integrantes_habilitados, participantes de Tarefa/Compromisso), então
# nenhuma migração de dados é necessária.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0031_remove_equipe_pai'),
    ]

    operations = [
        migrations.DeleteModel(
            name='VinculoIntegrante',
        ),
        migrations.DeleteModel(
            name='EquipeVinculada',
        ),
    ]
