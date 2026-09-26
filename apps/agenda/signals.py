from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.processos.models import MovimentacaoProcessual, Processo

from .services import sincronizar_prazo_do_andamento, sincronizar_responsaveis_dos_prazos


@receiver(post_save, sender=MovimentacaoProcessual)
def sincronizar_prazo(sender, instance, raw=False, **kwargs):
    """Signal, e não a view de andamento, para valer em qualquer origem do
    andamento (manual hoje, integração no futuro). A remoção do andamento
    remove o Prazo por CASCADE."""
    if raw:
        return
    sincronizar_prazo_do_andamento(instance)


@receiver(m2m_changed, sender=Processo.responsaveis.through)
def acompanhar_responsaveis_do_processo(sender, instance, action, reverse=False, **kwargs):
    """Qualquer mudança nos responsáveis (card, formulário, perda de
    acesso) reflete nos Prazos gerados em aberto."""
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    processos = [instance] if not reverse else Processo.objects.filter(pk__in=kwargs.get("pk_set") or [])
    for processo in processos:
        sincronizar_responsaveis_dos_prazos(processo)
