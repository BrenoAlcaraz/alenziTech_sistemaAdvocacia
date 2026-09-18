from django import template

from apps.financeiro.models import SolicitacaoFinanceira
from apps.financeiro.views import _tem_acesso_dados

register = template.Library()


@register.inclusion_tag("financeiro/_abas.html", takes_context=True)
def abas_financeiro(context):
    """Barra de abas do Financeiro. A contagem de solicitações pendentes é
    calculada aqui, uma única vez por render da barra, e só para quem tem
    acesso ao caixa geral — para os demais a barra nem é montada."""
    request = context["request"]
    if not _tem_acesso_dados(request.user):
        return {"mostrar": False}
    return {
        "mostrar": True,
        "aba_ativa": context.get("aba_ativa"),
        "solicitacoes_pendentes": SolicitacaoFinanceira.objects.filter(
            status__in=SolicitacaoFinanceira.STATUS_ABERTOS
        ).count(),
    }
