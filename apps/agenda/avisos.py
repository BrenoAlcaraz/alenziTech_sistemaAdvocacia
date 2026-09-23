"""
Notificações in-app da Agenda Jurídica ampliadas pelo PDR-0034:
atribuição/reatribuição, convite recebido, Prazo gerado pelo andamento,
data fatal alterada no andamento e os avisos por data (véspera/dia da
fatal, data para fazer de Prazo vencida). Item concluído ou cancelado nunca é avisado.
"""

from datetime import timedelta

from django.db import transaction

from apps.accounts.models import ConviteDelegacao
from apps.notificacoes.models import Notificacao

from .models import STATUS_ENCERRADOS, TIPO_PRAZO, TIPOS_AFAZER, AvisoItemAgenda, ItemAgenda

CONVITES_QUE_OCULTAM = [ConviteDelegacao.STATUS_PENDENTE, ConviteDelegacao.STATUS_RECUSADO]
_TAMANHO_MENSAGEM = Notificacao._meta.get_field("mensagem").max_length


def notificar(destinatario, mensagem):
    return Notificacao.objects.create(destinatario=destinatario, mensagem=mensagem[:_TAMANHO_MENSAGEM])


def _rotulo(item):
    return f'{item.get_tipo_display()} "{item.titulo}"'


def _nome(usuario):
    return usuario.get_full_name() or usuario.username


def avisar_atribuicao(item, autor=None):
    """Aviso ao responsável que recebeu o item (criação para outra pessoa
    ou reatribuição). `autor` nulo: troca automática pelo processo."""
    if item.status in STATUS_ENCERRADOS or item.responsavel_id is None:
        return
    if autor is not None and autor.pk == item.responsavel_id:
        return
    origem = f"{_nome(autor)} atribuiu a você" if autor else "Atribuído a você pelo processo"
    notificar(item.responsavel, f"{origem}: {_rotulo(item)}")


def avisar_convite(item, convite):
    notificar(
        convite.destinatario,
        f"{_nome(convite.delegante)} convidou você para assumir {_rotulo(item)} — aceite ou recuse na Agenda Jurídica.",
    )


def avisar_prazo_gerado(item):
    if item.responsavel_id is None:
        return
    notificar(
        item.responsavel,
        f"Novo prazo no processo {item.processo}: {_rotulo(item)} — fatal {item.data_fatal:%d/%m}",
    )


def avisar_fatal_alterada(item, fatal_anterior):
    if item.status in STATUS_ENCERRADOS or item.responsavel_id is None:
        return
    notificar(
        item.responsavel,
        f"Data fatal alterada de {fatal_anterior:%d/%m} para {item.data_fatal:%d/%m}: {_rotulo(item)}",
    )


def _avisar_uma_vez(item, motivo, referencia, mensagem):
    with transaction.atomic():
        _, criado = AvisoItemAgenda.objects.get_or_create(
            item=item, destinatario=item.responsavel, motivo=motivo, referencia=referencia,
        )
        if criado:
            notificar(item.responsavel, mensagem)
    return criado


def enviar_avisos_de_data(hoje):
    """Avisos por data dos afazeres em aberto do tenant corrente. Só o dia
    exato dispara véspera/dia da fatal (job parado não gera aviso
    atrasado); a data para fazer vencida só avisa enquanto a fatal não
    passou — depois disso os avisos da fatal já cobriram o item.
    Retorna quantos avisos foram criados."""
    abertos = (
        ItemAgenda.objects.filter(tipo__in=TIPOS_AFAZER, responsavel__isnull=False)
        .exclude(status__in=STATUS_ENCERRADOS)
        .exclude(convite_delegacao__status__in=CONVITES_QUE_OCULTAM)
        .select_related("responsavel")
    )
    enviados = 0
    for item in abertos.filter(data_fatal=hoje + timedelta(days=1)):
        enviados += _avisar_uma_vez(
            item, AvisoItemAgenda.MOTIVO_FATAL_VESPERA, item.data_fatal,
            f"Data fatal amanhã ({item.data_fatal:%d/%m}): {_rotulo(item)}",
        )
    for item in abertos.filter(data_fatal=hoje):
        enviados += _avisar_uma_vez(
            item, AvisoItemAgenda.MOTIVO_FATAL_HOJE, item.data_fatal,
            f"Data fatal hoje: {_rotulo(item)}",
        )
    for item in abertos.filter(tipo=TIPO_PRAZO, data_para_fazer__lt=hoje, data_fatal__gte=hoje):
        enviados += _avisar_uma_vez(
            item, AvisoItemAgenda.MOTIVO_PARA_FAZER_VENCIDA, item.data_para_fazer,
            f"Data para fazer vencida ({item.data_para_fazer:%d/%m}), fatal em {item.data_fatal:%d/%m}: {_rotulo(item)}",
        )
    return enviados
