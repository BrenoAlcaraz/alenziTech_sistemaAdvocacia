# Passo 3/3 — ver 0019_ampliar_nivel_financeiro_dados.py e
# 0020_migrar_nivel_dados_financeiro.py.
#
# Nenhuma linha deve restar com nivel="dados" em Financeiro após a
# migration de dados anterior — a constraint final não aceita mais
# esse valor legado.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_migrar_nivel_dados_financeiro'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='permissaopapel',
            name='chk_permissaopapel_nivel',
        ),
        migrations.RemoveConstraint(
            model_name='permissaousuario',
            name='chk_permissaousuario_nivel',
        ),
        migrations.AddConstraint(
            model_name='permissaopapel',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('modulo__in', ['processos', 'clientes', 'tarefas', 'modelos', 'painel', 'agenda']), ('nivel__in', ['somente_seus', 'todos'])), models.Q(('modulo', 'financeiro'), ('nivel__in', ['solicitacoes', 'dados_proprios', 'dados_todos'])), models.Q(('modulo__in', ['chat', 'gerir']), ('nivel', '')), _connector='OR'), name='chk_permissaopapel_nivel'),
        ),
        migrations.AddConstraint(
            model_name='permissaousuario',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('modulo__in', ['processos', 'clientes', 'tarefas', 'modelos', 'painel', 'agenda']), ('nivel__in', ['somente_seus', 'todos'])), models.Q(('modulo', 'financeiro'), ('nivel__in', ['solicitacoes', 'dados_proprios', 'dados_todos'])), models.Q(('modulo__in', ['chat', 'gerir']), ('nivel', '')), _connector='OR'), name='chk_permissaousuario_nivel'),
        ),
    ]
