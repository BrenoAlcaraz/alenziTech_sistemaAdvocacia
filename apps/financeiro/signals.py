from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.financeiro.models import SolicitacaoFinanceira


@receiver(post_delete, sender=SolicitacaoFinanceira)
def excluir_anexo_da_solicitacao(sender, instance, **kwargs):
    """Remove o arquivo do storage protegido ao excluir o registro —
    signal cobre qualquer caminho de exclusão (view futura, cascata ou
    Django Admin), não só um ponto específico."""
    if instance.anexo:
        instance.anexo.delete(save=False)
