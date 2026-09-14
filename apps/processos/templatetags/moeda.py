from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def moeda_br(valor):
    """Formata um número no padrão brasileiro de valor monetário, sem o
    prefixo 'R$' (o template já escreve isso ao lado, igual ao padrão já
    usado no Financeiro) — separador de milhar '.', decimal ','.
    Ex.: 78100.89 -> '78.100,89'."""
    if valor in (None, ""):
        return "0,00"
    try:
        valor = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    negativo = valor < 0
    inteiro, _, decimal = f"{abs(valor):.2f}".partition(".")
    inteiro_com_milhar = f"{int(inteiro):,}".replace(",", ".")
    resultado = f"{inteiro_com_milhar},{decimal}"
    return f"-{resultado}" if negativo else resultado
