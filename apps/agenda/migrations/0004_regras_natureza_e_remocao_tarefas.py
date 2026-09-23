from django.db import migrations, models


class Migration(migrations.Migration):
    """Regras por natureza no banco (dados já convertidos em 0003) e
    remoção das tabelas de `apps.tarefas`, já importadas em 0003."""

    dependencies = [
        ('agenda', '0003_dados_item_agenda'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='itemagenda',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('tipo', 'prazo'), _negated=True), ('data_fatal__isnull', False), _connector='OR'), name='agenda_prazo_exige_data_fatal'),
        ),
        migrations.AddConstraint(
            model_name='itemagenda',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('tipo__in', ['audiencia', 'reuniao', 'pericia', 'julgamento']), _negated=True), ('data_hora_inicio__isnull', False), _connector='OR'), name='agenda_evento_exige_inicio'),
        ),
        migrations.AddConstraint(
            model_name='itemagenda',
            constraint=models.CheckConstraint(condition=models.Q(models.Q(('tipo__in', ['audiencia', 'reuniao', 'pericia', 'julgamento']), _negated=True), models.Q(('status', 'em_andamento'), _negated=True), _connector='OR'), name='agenda_evento_sem_em_andamento'),
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS tarefas_reatribuicaotarefa, tarefas_tarefa_participantes, tarefas_tarefa",
            migrations.RunSQL.noop,
        ),
    ]
