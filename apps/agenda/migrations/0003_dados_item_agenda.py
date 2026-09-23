from datetime import timedelta

from django.db import migrations
from django.db.models import F
from django.utils import timezone


TIPOS_AFAZER_COM_HORARIO_ANTIGO = ["prazo", "protocolo", "retorno"]
STATUS_TAREFA = {
    "a_fazer": "a_fazer",
    "em_andamento": "em_andamento",
    "concluida": "concluido",
    "cancelada": "cancelado",
}


def _content_type_item(apps):
    """ContentType de ItemAgenda, reapontando convites que ainda estejam
    no de Compromisso (caso o rename automático de content types não
    tenha rodado neste schema)."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    ConviteDelegacao = apps.get_model("accounts", "ConviteDelegacao")
    novo, _ = ContentType.objects.get_or_create(app_label="agenda", model="itemagenda")
    antigo = ContentType.objects.filter(app_label="agenda", model="compromisso").first()
    if antigo is not None:
        ConviteDelegacao.objects.filter(content_type=antigo).update(content_type=novo)
    return novo


def converter_compromissos(apps):
    ItemAgenda = apps.get_model("agenda", "ItemAgenda")
    ItemAgenda.objects.filter(status="agendado").update(status="a_fazer")
    # "Outro" saiu do catálogo; o compromisso tem horário, então vira Evento.
    ItemAgenda.objects.filter(tipo="outro").update(tipo="reuniao")
    ItemAgenda.objects.filter(atribuidor__isnull=True).update(
        atribuidor=F("criado_por"), atribuido_em=F("criado_em")
    )
    # Prazo/Protocolo/Retorno viram Afazer: o início vira a data (e hora)
    # para fazer; em Prazo, também a data fatal.
    for item in ItemAgenda.objects.filter(
        tipo__in=TIPOS_AFAZER_COM_HORARIO_ANTIGO, data_hora_inicio__isnull=False
    ):
        inicio = timezone.localtime(item.data_hora_inicio)
        item.data_para_fazer = inicio.date()
        item.hora_para_fazer = None if item.dia_inteiro else inicio.time().replace(second=0, microsecond=0)
        if item.tipo == "prazo":
            item.data_fatal = inicio.date()
        item.data_hora_inicio = None
        item.data_hora_fim = None
        item.dia_inteiro = False
        item.save(update_fields=[
            "data_para_fazer", "hora_para_fazer", "data_fatal",
            "data_hora_inicio", "data_hora_fim", "dia_inteiro",
        ])


def _tabela_existe(cursor, nome):
    cursor.execute("SELECT to_regclass(quote_ident(current_schema()) || '.' || %s)", [nome])
    return cursor.fetchone()[0] is not None


def importar_tarefas(apps, schema_editor):
    """Tarefas viram itens tipo Tarefa (PDR-0034). Lidas por SQL porque
    `apps.tarefas` já não está instalado; schema novo não tem a tabela."""
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if not _tabela_existe(cursor, "tarefas_tarefa"):
            return
        cursor.execute(
            "SELECT id, titulo, descricao, status, prioridade, responsavel_id, criador_id, "
            "atribuidor_id, atribuido_em, processo_id, cliente_id, prazo, criado_em, "
            "convite_delegacao_id FROM tarefas_tarefa ORDER BY id"
        )
        tarefas = cursor.fetchall()
        cursor.execute("SELECT tarefa_id, user_id FROM tarefas_tarefa_participantes")
        participantes = cursor.fetchall()
        cursor.execute(
            "SELECT tarefa_id, responsavel_anterior_id, responsavel_novo_id, autor_id, criado_em "
            "FROM tarefas_reatribuicaotarefa"
        )
        reatribuicoes = cursor.fetchall()

    ItemAgenda = apps.get_model("agenda", "ItemAgenda")
    ParticipanteItemAgenda = apps.get_model("agenda", "ParticipanteItemAgenda")
    ReatribuicaoItemAgenda = apps.get_model("agenda", "ReatribuicaoItemAgenda")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ConviteDelegacao = apps.get_model("accounts", "ConviteDelegacao")
    ct_item = _content_type_item(apps)
    ct_tarefa = ContentType.objects.filter(app_label="tarefas", model="tarefa").first()
    agora = timezone.now()

    item_por_tarefa = {}
    responsavel_por_tarefa = {}
    for (
        tarefa_id, titulo, descricao, status, prioridade, responsavel_id, criador_id,
        atribuidor_id, atribuido_em, processo_id, cliente_id, prazo, criado_em,
        convite_id,
    ) in tarefas:
        status_item = STATUS_TAREFA.get(status, "a_fazer")
        item = ItemAgenda.objects.create(
            tipo="tarefa",
            titulo=titulo,
            descricao=descricao,
            status=status_item,
            prioridade=prioridade,
            responsavel_id=responsavel_id,
            criado_por_id=criador_id,
            atribuidor_id=atribuidor_id,
            atribuido_em=atribuido_em,
            processo_id=processo_id,
            cliente_id=cliente_id,
            data_fatal=prazo,
            convite_delegacao_id=convite_id,
            # Data real do cancelamento não existia em Tarefa: a retenção
            # de 7 dias conta a partir da migração.
            cancelado_em=agora if status_item == "cancelado" else None,
        )
        ItemAgenda.objects.filter(pk=item.pk).update(criado_em=criado_em)
        item_por_tarefa[tarefa_id] = item.pk
        responsavel_por_tarefa[tarefa_id] = responsavel_id
        if ct_tarefa is not None:
            ConviteDelegacao.objects.filter(content_type=ct_tarefa, object_id=tarefa_id).update(
                content_type=ct_item, object_id=item.pk
            )

    ParticipanteItemAgenda.objects.bulk_create([
        ParticipanteItemAgenda(item_id=item_por_tarefa[tarefa_id], usuario_id=usuario_id)
        for tarefa_id, usuario_id in participantes
        if usuario_id != responsavel_por_tarefa[tarefa_id]
    ])

    for tarefa_id, anterior_id, novo_id, autor_id, criado_em in reatribuicoes:
        reatribuicao = ReatribuicaoItemAgenda.objects.create(
            item_id=item_por_tarefa[tarefa_id],
            responsavel_anterior_id=anterior_id,
            responsavel_novo_id=novo_id,
            autor_id=autor_id,
        )
        ReatribuicaoItemAgenda.objects.filter(pk=reatribuicao.pk).update(criado_em=criado_em)


def gerar_prazos_dos_andamentos(apps):
    """Mesma regra de `apps/agenda/services.py::sincronizar_prazo_do_andamento`,
    congelada aqui para os andamentos já existentes."""
    ItemAgenda = apps.get_model("agenda", "ItemAgenda")
    MovimentacaoProcessual = apps.get_model("processos", "MovimentacaoProcessual")
    agora = timezone.now()
    andamentos = MovimentacaoProcessual.objects.filter(
        data_prazo__isnull=False, item_agenda__isnull=True
    ).select_related("processo")
    for andamento in andamentos:
        processo = andamento.processo
        ItemAgenda.objects.create(
            tipo="prazo",
            titulo=f"Prazo — {andamento.get_tipo_display()}",
            descricao=andamento.descricao,
            data_fatal=andamento.data_prazo,
            data_para_fazer=andamento.data_prazo - timedelta(days=2),
            responsavel_id=processo.responsavel_id,
            atribuido_em=agora,
            processo=processo,
            cliente=processo.clientes.first(),
            movimentacao_origem=andamento,
        )


def migrar_dados(apps, schema_editor):
    _content_type_item(apps)
    converter_compromissos(apps)
    importar_tarefas(apps, schema_editor)
    gerar_prazos_dos_andamentos(apps)


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0002_item_agenda'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(migrar_dados, migrations.RunPython.noop),
    ]
