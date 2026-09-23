from django.utils import timezone

from .models import STATUS_ENCERRADOS, TIPO_PRAZO, ItemAgenda, ReatribuicaoItemAgenda


def titulo_prazo_do_andamento(andamento):
    return f"Prazo — {andamento.get_tipo_display()}"


def sincronizar_prazo_do_andamento(andamento):
    """Mantém exatamente um Prazo por andamento com `data_prazo`
    (PDR-0034): cria, acompanha a data fatal ou remove. Retorna o item
    (ou None quando o andamento não tem prazo)."""
    item = ItemAgenda.objects.filter(movimentacao_origem=andamento).first()
    if andamento.data_prazo is None:
        if item is not None:
            item.delete()
        return None

    if item is None:
        processo = andamento.processo
        return ItemAgenda.objects.create(
            tipo=TIPO_PRAZO,
            titulo=titulo_prazo_do_andamento(andamento),
            descricao=andamento.descricao,
            data_fatal=andamento.data_prazo,
            data_para_fazer=ItemAgenda.data_para_fazer_padrao(andamento.data_prazo),
            responsavel=processo.responsavel,
            atribuido_em=timezone.now(),
            processo=processo,
            cliente=processo.clientes.first(),
            movimentacao_origem=andamento,
        )

    if item.data_fatal != andamento.data_prazo:
        # Data para fazer ajustada à mão é preservada, desde que continue
        # antes da nova fatal.
        manteve_padrao = item.data_para_fazer in (None, ItemAgenda.data_para_fazer_padrao(item.data_fatal))
        if manteve_padrao or item.data_para_fazer > andamento.data_prazo:
            item.data_para_fazer = ItemAgenda.data_para_fazer_padrao(andamento.data_prazo)
        item.data_fatal = andamento.data_prazo
        item.save(update_fields=["data_fatal", "data_para_fazer"])
    return item


def transferir_prazos_gerados(processo, novo_responsavel):
    """Prazos gerados por andamento ainda abertos acompanham o novo
    responsável do processo; concluído/cancelado guarda o histórico."""
    itens = (
        ItemAgenda.objects.filter(movimentacao_origem__processo=processo)
        .exclude(status__in=STATUS_ENCERRADOS)
        .exclude(responsavel=novo_responsavel)
    )
    agora = timezone.now()
    for item in itens:
        ReatribuicaoItemAgenda.objects.create(
            item=item, responsavel_anterior=item.responsavel, responsavel_novo=novo_responsavel,
        )
        item.responsavel = novo_responsavel
        item.atribuido_em = agora
        item.save(update_fields=["responsavel", "atribuido_em"])

