from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_migrar_permissoes_tarefas_para_agenda'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='habilitacaopapel',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('item__in', ['processos_criar', 'processos_editar', 'processos_andamento_adicionar', 'processos_usar_ia', 'processos_usar_laboratorio', 'processos_atribuir_responsavel', 'processos_documento_adicionar', 'processos_documento_excluir', 'processos_excluir']), ('modulo', 'processos')), models.Q(('item__in', ['clientes_criar', 'clientes_editar', 'clientes_desativar', 'clientes_reativar', 'clientes_excluir', 'clientes_documento_adicionar', 'clientes_documento_excluir']), ('modulo', 'clientes')), models.Q(('item__in', ['modelos_criar', 'modelos_editar_estilo', 'modelos_editar_alheio', 'modelos_excluir_alheio', 'modelos_gerir_categorias']), ('modulo', 'modelos')), models.Q(('item__in', ['agenda_atribuir_outros']), ('modulo', 'agenda')), models.Q(('item__in', ['financeiro_reabrir_lancamento_pago']), ('modulo', 'financeiro')), models.Q(('item__in', ['gerir_criar_usuario', 'gerir_habilitar_usuario_processos', 'gerir_criar_equipe', 'gerir_habilitar_terceiros']), ('modulo', 'gerir')), _connector='OR'), name='chk_habilitacaopapel_modulo_item'),
        ),
        migrations.AddConstraint(
            model_name='habilitacaousuario',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('item__in', ['processos_criar', 'processos_editar', 'processos_andamento_adicionar', 'processos_usar_ia', 'processos_usar_laboratorio', 'processos_atribuir_responsavel', 'processos_documento_adicionar', 'processos_documento_excluir', 'processos_excluir']), ('modulo', 'processos')), models.Q(('item__in', ['clientes_criar', 'clientes_editar', 'clientes_desativar', 'clientes_reativar', 'clientes_excluir', 'clientes_documento_adicionar', 'clientes_documento_excluir']), ('modulo', 'clientes')), models.Q(('item__in', ['modelos_criar', 'modelos_editar_estilo', 'modelos_editar_alheio', 'modelos_excluir_alheio', 'modelos_gerir_categorias']), ('modulo', 'modelos')), models.Q(('item__in', ['agenda_atribuir_outros']), ('modulo', 'agenda')), models.Q(('item__in', ['financeiro_reabrir_lancamento_pago']), ('modulo', 'financeiro')), models.Q(('item__in', ['gerir_criar_usuario', 'gerir_habilitar_usuario_processos', 'gerir_criar_equipe', 'gerir_habilitar_terceiros']), ('modulo', 'gerir')), _connector='OR'), name='chk_habilitacaousuario_modulo_item'),
        ),
        migrations.AddConstraint(
            model_name='permissaopapel',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('modulo__in', ['processos', 'clientes', 'modelos', 'painel', 'agenda']), ('nivel__in', ['somente_seus', 'todos'])), models.Q(('modulo', 'financeiro'), ('nivel__in', ['solicitacoes', 'dados_proprios', 'dados_todos'])), models.Q(('modulo__in', ['chat', 'gerir']), ('nivel', '')), _connector='OR'), name='chk_permissaopapel_nivel'),
        ),
        migrations.AddConstraint(
            model_name='permissaousuario',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('modulo__in', ['processos', 'clientes', 'modelos', 'painel', 'agenda']), ('nivel__in', ['somente_seus', 'todos'])), models.Q(('modulo', 'financeiro'), ('nivel__in', ['solicitacoes', 'dados_proprios', 'dados_todos'])), models.Q(('modulo__in', ['chat', 'gerir']), ('nivel', '')), _connector='OR'), name='chk_permissaousuario_nivel'),
        ),
    ]
