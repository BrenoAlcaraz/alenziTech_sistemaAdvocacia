from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.chat.models import Mensagem


@receiver(post_delete, sender=Mensagem)
def excluir_anexo_da_mensagem(sender, instance, **kwargs):
    """Remove o arquivo do storage protegido ao excluir o registro —
    inclusive em cascata (Conversa excluída) e via Django Admin, já que
    signal cobre qualquer caminho de exclusão, não só uma view."""
    if instance.anexo:
        instance.anexo.delete(save=False)
