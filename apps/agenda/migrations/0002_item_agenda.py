import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Compromisso evolui para ItemAgenda (PDR-0034): catálogo fixo de
    tipos, datas de afazer, prioridade, atribuição e vínculo com o
    andamento de origem. Só schema — os dados vêm em 0003."""

    dependencies = [
        ('accounts', '0003_codigo_interno'),
        ('agenda', '0001_initial'),
        ('clientes', '0001_initial'),
        ('processos', '0003_numero_interno_obrigatorio'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel('Compromisso', 'ItemAgenda'),
        migrations.RenameModel('ParticipanteCompromisso', 'ParticipanteItemAgenda'),
        migrations.RemoveConstraint(
            model_name='participanteitemagenda',
            name='agenda_participante_unico_por_compromisso',
        ),
        migrations.RenameField('participanteitemagenda', 'compromisso', 'item'),
        migrations.AlterField(
            model_name='participanteitemagenda',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participacoes', to='agenda.itemagenda'),
        ),
        migrations.AlterField(
            model_name='participanteitemagenda',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participacoes_agenda', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='participanteitemagenda',
            constraint=models.UniqueConstraint(fields=('item', 'usuario'), name='agenda_participante_unico_por_item'),
        ),
        migrations.AlterModelOptions(
            name='participanteitemagenda',
            options={'verbose_name': 'Participante do item da agenda', 'verbose_name_plural': 'Participantes do item da agenda'},
        ),
        migrations.AlterModelOptions(
            name='itemagenda',
            options={'ordering': ['data_hora_inicio', 'data_para_fazer', 'data_fatal'], 'verbose_name': 'Item da agenda', 'verbose_name_plural': 'Itens da agenda'},
        ),
        # Choices antigos continuam aceitos até a conversão em 0003 — a
        # coluna é a mesma, só o rótulo muda.
        migrations.AlterField(
            model_name='itemagenda',
            name='tipo',
            field=models.CharField(choices=[('tarefa', 'Tarefa'), ('prazo', 'Prazo'), ('protocolo', 'Protocolo'), ('retorno', 'Retorno'), ('audiencia', 'Audiência'), ('reuniao', 'Reunião'), ('pericia', 'Perícia'), ('julgamento', 'Julgamento')], default='tarefa', max_length=20),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='status',
            field=models.CharField(choices=[('a_fazer', 'A fazer'), ('em_andamento', 'Em andamento'), ('concluido', 'Concluído'), ('cancelado', 'Cancelado')], default='a_fazer', max_length=20),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='data_hora_inicio',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='responsavel',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_agenda', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='criado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_agenda_criados', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='participantes',
            field=models.ManyToManyField(blank=True, related_name='itens_agenda_participando', through='agenda.ParticipanteItemAgenda', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='processo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_agenda', to='processos.processo'),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='cliente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_agenda', to='clientes.cliente'),
        ),
        migrations.AlterField(
            model_name='itemagenda',
            name='convite_delegacao',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='item_agenda', to='accounts.convitedelegacao'),
        ),
        migrations.AddField(
            model_name='itemagenda',
            name='prioridade',
            field=models.CharField(choices=[('baixa', 'Baixa'), ('media', 'Média'), ('alta', 'Alta')], default='media', max_length=10),
        ),
        migrations.AddField(
            model_name='itemagenda',
            name='data_para_fazer',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='itemagenda',
            name='hora_para_fazer',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='itemagenda',
            name='data_fatal',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='itemagenda',
            name='atribuidor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_agenda_atribuidos', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='itemagenda',
            name='atribuido_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='itemagenda',
            name='movimentacao_origem',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='item_agenda', to='processos.movimentacaoprocessual'),
        ),
        migrations.CreateModel(
            name='ReatribuicaoItemAgenda',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reatribuicoes', to='agenda.itemagenda')),
                ('responsavel_anterior', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('responsavel_novo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Reatribuição de item da agenda',
                'verbose_name_plural': 'Reatribuições de item da agenda',
                'ordering': ['-criado_em'],
            },
        ),
    ]
