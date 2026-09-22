from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.financeiro.models import CustaJudicial, LancamentoFinanceiro, SolicitacaoFinanceira


@receiver(post_delete, sender=SolicitacaoFinanceira)
@receiver(post_delete, sender=LancamentoFinanceiro)
@receiver(post_delete, sender=CustaJudicial)
def excluir_anexo_do_registro(sender, instance, **kwargs):
    """Remove o(s) arquivo(s) do storage protegido ao excluir o registro —
    signal cobre qualquer caminho de exclusão (view futura, cascata ou
    Django Admin), não só um ponto específico. `comprovante_pagamento`
    só existe em LancamentoFinanceiro e SolicitacaoFinanceira."""
    if instance.anexo:
        instance.anexo.delete(save=False)
    comprovante = getattr(instance, "comprovante_pagamento", None)
    if comprovante:
        comprovante.delete(save=False)


@receiver(post_save, sender=LancamentoFinanceiro)
def sincronizar_credito_do_reembolso(sender, instance, raw=False, **kwargs):
    """Receita "Reembolso" de cliente ↔ crédito nas custas judiciais dele."""
    if raw:
        return
    from apps.financeiro.services import sincronizar_credito_de_reembolso

    sincronizar_credito_de_reembolso(instance)
