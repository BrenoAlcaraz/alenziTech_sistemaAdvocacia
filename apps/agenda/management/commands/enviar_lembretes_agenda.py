"""
Job periódico (PDR-0016, parte Agenda): notifica o responsável de todo
Compromisso agendado que esteja por volta de 15 minutos antes de
`data_hora_inicio` e ainda não tenha gerado lembrete. Disparo periódico
concreto (cron do SO, Windows Task Scheduler etc.) é externo a este
comando.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.agenda.models import Compromisso
from apps.notificacoes.models import Notificacao
from apps.saas_tenants.models import Escritorio

MINUTOS_ANTECEDENCIA = 15


class Command(BaseCommand):
    help = (
        "Gera notificação de lembrete para compromissos de Agenda a "
        f"partir de {MINUTOS_ANTECEDENCIA} minutos antes do horário marcado."
    )

    def handle(self, *args, **options):
        limite = timezone.now() + timedelta(minutes=MINUTOS_ANTECEDENCIA)
        for escritorio in Escritorio.objects.filter(ativo=True):
            with schema_context(escritorio.schema_name):
                self._notificar_tenant(limite)

    def _notificar_tenant(self, limite):
        elegiveis = Compromisso.objects.filter(
            status="agendado",
            responsavel__isnull=False,
            lembrete_enviado=False,
            data_hora_inicio__lte=limite,
        )
        for compromisso in elegiveis:
            self._notificar_compromisso(compromisso)

    def _notificar_compromisso(self, compromisso):
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
