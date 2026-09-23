from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.processos.models import MovimentacaoProcessual, Processo

from .services import sincronizar_prazo_do_andamento, transferir_prazos_gerados


@receiver(post_save, sender=MovimentacaoProcessual)
def sincronizar_prazo(sender, instance, raw=False, **kwargs):
    """Signal, e não a view de andamento, para valer em qualquer origem do
    andamento (manual hoje, integração no futuro). A remoção do andamento
    remove o Prazo por CASCADE."""
    if raw:
        return
    sincronizar_prazo_do_andamento(instance)


@receiver(pre_save, sender=Processo)
def guardar_responsavel_anterior(sender, instance, raw=False, update_fields=None, **kwargs):
    instance._responsavel_anterior_id = None
    if raw or instance.pk is None:
        return
    if update_fields is not None and "responsavel" not in update_fields:
        return
    instance._responsavel_anterior_id = (
        Processo.objects.filter(pk=instance.pk).values_list("responsavel_id", flat=True).first()
    )


@receiver(post_save, sender=Processo)
def transferir_prazos_ao_trocar_responsavel(sender, instance, raw=False, **kwargs):
    anterior = getattr(instance, "_responsavel_anterior_id", None)
    if raw or anterior is None or anterior == instance.responsavel_id:
        return
    transferir_prazos_gerados(instance, instance.responsavel)
