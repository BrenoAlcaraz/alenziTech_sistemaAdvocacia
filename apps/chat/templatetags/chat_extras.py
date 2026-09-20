from django import template

from apps.chat.mencoes import destacar_mencoes

register = template.Library()


@register.filter
def com_mencoes(texto):
    return destacar_mencoes(texto)
