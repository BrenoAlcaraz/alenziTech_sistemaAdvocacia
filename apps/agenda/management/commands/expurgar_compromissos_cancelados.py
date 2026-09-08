"""
Job periódico (spec `specs/agenda-participantes-confirmacao.md`, ticket
"Agenda: cancelamento consultável e indicadores de confirmação no
Dashboard"): exclui definitivamente todo Compromisso com
`status="cancelado"` cuja `cancelado_em` já passou de 7 dias — a
retenção conta a partir da data do cancelamento, não da data original
do compromisso. Mesmo padrão de disparo periódico (cron do SO, Windows
Task Scheduler etc., externo a este comando) e de iteração por tenant
de `enviar_lembretes_agenda`.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.agenda.models import Compromisso
from apps.saas_tenants.models import Escritorio

DIAS_RETENCAO = 7


class Command(BaseCommand):
    help = (
        "Exclui compromissos cancelados há mais de "
        f"{DIAS_RETENCAO} dias (retenção contada da data do cancelamento)."
    )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=DIAS_RETENCAO)
        for escritorio in Escritorio.objects.filter(ativo=True):
            with schema_context(escritorio.schema_name):
                Compromisso.objects.filter(
                    status="cancelado", cancelado_em__lte=limite
                ).delete()
