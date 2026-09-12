from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.processos.models import Documento


@receiver(post_delete, sender=Documento)
def excluir_arquivo_do_documento(sender, instance, **kwargs):
    """Remove o arquivo do storage protegido ao excluir o registro —
    inclusive em cascata (Processo excluído) e via Django Admin, já que
    signal cobre qualquer caminho de exclusão, não só a view."""
    if instance.arquivo:
        instance.arquivo.delete(save=False)
