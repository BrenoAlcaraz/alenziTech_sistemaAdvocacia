"""
Job diário do acompanhamento automático (DJEN): em cada escritório
ativo, dentro do próprio schema, traz as publicações dos processos
acompanhados como andamento sugerido. Deve rodar uma vez por dia antes
das 7h; o disparo (cron do SO, Task Scheduler) é externo a este
comando. Rodar de novo não duplica nada.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.processos.acompanhamento import executar_acompanhamento
from apps.saas_tenants.models import Escritorio

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Acompanha no DJEN os processos de cada escritório e traz andamentos e prazos sugeridos."

    def handle(self, *args, **options):
        hoje = timezone.localdate()
        for escritorio in Escritorio.objects.filter(ativo=True):
            try:
                with schema_context(escritorio.schema_name):
                    execucao = executar_acompanhamento(hoje)
            except Exception:  # noqa: BLE001 — um escritório não interrompe os demais
                logger.exception("Acompanhamento falhou no escritório %s", escritorio.schema_name)
                self.stderr.write(f"{escritorio.schema_name}: falhou")
                continue
            self.stdout.write(f"{escritorio.schema_name}: {execucao.falhas} falha(s)")
