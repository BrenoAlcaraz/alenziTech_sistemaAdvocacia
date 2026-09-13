from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.financeiro.models import CustaJudicial, LancamentoFinanceiro, SolicitacaoFinanceira


@receiver(post_delete, sender=SolicitacaoFinanceira)
@receiver(post_delete, sender=LancamentoFinanceiro)
@receiver(post_delete, sender=CustaJudicial)
def excluir_anexo_do_registro(sender, instance, **kwargs):
    """Remove o arquivo do storage protegido ao excluir o registro —
    signal cobre qualquer caminho de exclusão (view futura, cascata ou
    Django Admin), não só um ponto específico."""
    if instance.anexo:
        instance.anexo.delete(save=False)
