"""
Job periódico (PDR-0016, parte Agenda): notifica o responsável e os
participantes confirmados de todo Evento da agenda em aberto que esteja
por volta de 15 minutos antes de `data_hora_inicio` e ainda não tenha
gerado lembrete (cada um com seu próprio controle de envio — o
responsável em `ItemAgenda.lembrete_enviado`, cada participante em
`ParticipanteItemAgenda.lembrete_enviado`). Participante pendente ou
recusado nunca recebe lembrete. Disparo periódico concreto (cron do SO,
Windows Task Scheduler etc.) é externo a este comando.

A janela é limitada também para trás (não só para a frente): um
item vencido há muito tempo sem ter sido concluído/cancelado não
deve gerar lembrete tardio na primeira execução do job ou após uma
pausa longa do agendador — o valor de "faltam 15 minutos" já não existe
depois desse ponto.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.agenda.models import STATUS_A_FAZER, TIPOS_EVENTO, ItemAgenda, ParticipanteItemAgenda
from apps.notificacoes.models import Notificacao
from apps.saas_tenants.models import Escritorio

MINUTOS_ANTECEDENCIA = 15


class Command(BaseCommand):
    help = (
        "Gera notificação de lembrete para items de Agenda a "
        f"partir de {MINUTOS_ANTECEDENCIA} minutos antes do horário marcado."
    )

    def handle(self, *args, **options):
        agora = timezone.now()
        janela_inicio = agora - timedelta(minutes=MINUTOS_ANTECEDENCIA)
        janela_fim = agora + timedelta(minutes=MINUTOS_ANTECEDENCIA)
        for escritorio in Escritorio.objects.filter(ativo=True):
            with schema_context(escritorio.schema_name):
                self._notificar_tenant(janela_inicio, janela_fim)

    def _notificar_tenant(self, janela_inicio, janela_fim):
        na_janela = Q(
            tipo__in=TIPOS_EVENTO,
            status=STATUS_A_FAZER,
            data_hora_inicio__gt=janela_inicio,
            data_hora_inicio__lte=janela_fim,
        )
        elegiveis = ItemAgenda.objects.filter(
            na_janela & (
                Q(responsavel__isnull=False, lembrete_enviado=False)
                | Q(
                    participacoes__status=ParticipanteItemAgenda.STATUS_CONFIRMADO,
                    participacoes__lembrete_enviado=False,
                )
            )
        ).distinct()
        for item in elegiveis:
            self._notificar_item(item)

    def _notificar_item(self, item):
        if item.responsavel_id and not item.lembrete_enviado:
            self._notificar_responsavel(item)
        for participacao in item.participacoes.filter(
            status=ParticipanteItemAgenda.STATUS_CONFIRMADO, lembrete_enviado=False
        ).select_related("usuario"):
            self._notificar_participante(participacao, item)

    def _notificar_responsavel(self, item):
        with transaction.atomic():
            atualizados = ItemAgenda.objects.filter(
                pk=item.pk, lembrete_enviado=False
            ).update(lembrete_enviado=True)
            if not atualizados:
                return
            horario = timezone.localtime(item.data_hora_inicio).strftime("%d/%m %H:%M")
            Notificacao.objects.create(
                destinatario=item.responsavel,
                mensagem=f'Lembrete: "{item.titulo}" às {horario}',
            )

    def _notificar_participante(self, participacao, item):
        with transaction.atomic():
            atualizados = ParticipanteItemAgenda.objects.filter(
                pk=participacao.pk, lembrete_enviado=False
            ).update(lembrete_enviado=True)
            if not atualizados:
                return
            horario = timezone.localtime(item.data_hora_inicio).strftime("%d/%m %H:%M")
            Notificacao.objects.create(
                destinatario=participacao.usuario,
                mensagem=f'Lembrete: "{item.titulo}" às {horario}',
            )
