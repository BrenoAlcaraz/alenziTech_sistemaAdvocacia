import re

from django.utils.html import escape
from django.utils.safestring import mark_safe

# "@usuario" fora de e-mail (sem letra/dígito/ponto antes do @).
PADRAO_MENCAO = re.compile(r"(?<![\w@.])@([\w.+-]*\w)")


def usernames_mencionados(texto):
    """Usernames (minúsculos) chamados com @ no texto da mensagem."""
    return {m.lower() for m in PADRAO_MENCAO.findall(texto or "")}


def destacar_mencoes(texto):
    """Texto escapado com cada @usuario em destaque."""
    return mark_safe(
        PADRAO_MENCAO.sub(
            lambda m: f'<span class="font-semibold underline">@{m.group(1)}</span>',
            escape(texto or ""),
        )
    )
