"""
Job periódico (PDR-0016, parte Agenda): notifica o responsável e os
participantes confirmados de todo Compromisso agendado que esteja por
volta de 15 minutos antes de `data_hora_inicio` e ainda não tenha
gerado lembrete (cada um com seu próprio controle de envio — o
responsável em `Compromisso.lembrete_enviado`, cada participante em
`ParticipanteCompromisso.lembrete_enviado`). Participante pendente ou
recusado nunca recebe lembrete. Disparo periódico concreto (cron do SO,
Windows Task Scheduler etc.) é externo a este comando.

A janela é limitada também para trás (não só para a frente): um
compromisso vencido há muito tempo sem ter sido concluído/cancelado não
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

from apps.agenda.models import Compromisso, ParticipanteCompromisso
from apps.notificacoes.models import Notificacao
from apps.saas_tenants.models import Escritorio

MINUTOS_ANTECEDENCIA = 15


class Command(BaseCommand):
    help = (
        "Gera notificação de lembrete para compromissos de Agenda a "
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
            status="agendado",
            data_hora_inicio__gt=janela_inicio,
            data_hora_inicio__lte=janela_fim,
        )
        elegiveis = Compromisso.objects.filter(
            na_janela & (
                Q(responsavel__isnull=False, lembrete_enviado=False)
                | Q(
                    participacoes__status=ParticipanteCompromisso.STATUS_CONFIRMADO,
                    participacoes__lembrete_enviado=False,
                )
            )
        ).distinct()
        for compromisso in elegiveis:
            self._notificar_compromisso(compromisso)

    def _notificar_compromisso(self, compromisso):
        if compromisso.responsavel_id and not compromisso.lembrete_enviado:
            self._notificar_responsavel(compromisso)
        for participacao in compromisso.participacoes.filter(
            status=ParticipanteCompromisso.STATUS_CONFIRMADO, lembrete_enviado=False
        ).select_related("usuario"):
            self._notificar_participante(participacao, compromisso)

    def _notificar_responsavel(self, compromisso):
        with transaction.atomic():
            atualizados = Compromisso.objects.filter(
                pk=compromisso.pk, lembrete_enviado=False
            ).update(lembrete_enviado=True)
            if not atualizados:
                return
            horario = timezone.localtime(compromisso.data_hora_inicio).strftime("%d/%m %H:%M")
            Notificacao.objects.create(
                destinatario=compromisso.responsavel,
                mensagem=f'Lembrete: "{compromisso.titulo}" às {horario}',
            )

    def _notificar_participante(self, participacao, compromisso):
        with transaction.atomic():
            atualizados = ParticipanteCompromisso.objects.filter(
                pk=participacao.pk, lembrete_enviado=False
            ).update(lembrete_enviado=True)
            if not atualizados:
                return
            horario = timezone.localtime(compromisso.data_hora_inicio).strftime("%d/%m %H:%M")
            Notificacao.objects.create(
                destinatario=participacao.usuario,
                mensagem=f'Lembrete: "{compromisso.titulo}" às {horario}',
            )
