# Passo 1/3 da divisão do nível "dados" de Financeiro em dois
# (dados_proprios/dados_todos — ver specs/escopo-financeiro-lancamentos.md).
#
# Amplia a constraint para aceitar, temporariamente, o valor legado
# "dados" junto dos dois novos valores — necessário porque o Postgres
# valida a CHECK constraint contra as linhas já existentes no momento
# do ALTER TABLE. A migration de dados (0020) move as linhas de
# "dados" para "dados_todos"; a migration seguinte (0021) remove
# "dados" da constraint.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_alter_perfilusuario_avatar'),
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
        migrations.AlterField(
            model_name='permissaopapel',
            name='nivel',
            field=models.CharField(blank=True, choices=[('somente_seus', 'Somente os seus'), ('todos', 'Todos'), ('solicitacoes', 'Apenas solicitações'), ('dados_proprios', 'Dados — só os meus lançamentos'), ('dados_todos', 'Dados — todos os lançamentos')], default='', help_text='Vazio para módulos sem escopo de dados (chat, gerir).', max_length=30, verbose_name='Nível de acesso'),
        ),
        migrations.AlterField(
            model_name='permissaousuario',
            name='nivel',
            field=models.CharField(blank=True, choices=[('somente_seus', 'Somente os seus'), ('todos', 'Todos'), ('solicitacoes', 'Apenas solicitações'), ('dados_proprios', 'Dados — só os meus lançamentos'), ('dados_todos', 'Dados — todos os lançamentos')], default='', help_text='Vazio para módulos sem escopo de dados (chat, gerir).', max_length=30, verbose_name='Nível de acesso'),
        ),
        migrations.AddConstraint(
            model_name='permissaopapel',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('modulo__in', ['processos', 'clientes', 'tarefas', 'modelos', 'painel', 'agenda']), ('nivel__in', ['somente_seus', 'todos'])), models.Q(('modulo', 'financeiro'), ('nivel__in', ['solicitacoes', 'dados', 'dados_proprios', 'dados_todos'])), models.Q(('modulo__in', ['chat', 'gerir']), ('nivel', '')), _connector='OR'), name='chk_permissaopapel_nivel'),
        ),
        migrations.AddConstraint(
            model_name='permissaousuario',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('modulo__in', ['processos', 'clientes', 'tarefas', 'modelos', 'painel', 'agenda']), ('nivel__in', ['somente_seus', 'todos'])), models.Q(('modulo', 'financeiro'), ('nivel__in', ['solicitacoes', 'dados', 'dados_proprios', 'dados_todos'])), models.Q(('modulo__in', ['chat', 'gerir']), ('nivel', '')), _connector='OR'), name='chk_permissaousuario_nivel'),
        ),
    ]
