from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.modelos.models import AnexoPecaGerada


@receiver(post_delete, sender=AnexoPecaGerada)
def excluir_arquivo_do_anexo(sender, instance, **kwargs):
    """Remove o arquivo do storage protegido ao excluir o anexo — inclusive
    em cascata (peça excluída)."""
    if instance.arquivo:
        instance.arquivo.delete(save=False)
