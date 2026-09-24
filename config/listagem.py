"""Ordenação e paginação das listas em tabela (Processos, Clientes,
Financeiro). Recebem o QuerySet já restrito ao escopo do usuário: a
contagem e as páginas só enxergam o que a view já filtrou."""

import re

from django.core.paginator import Paginator
from django.db.models import F, Func, Value

POR_PAGINA = 50

# Termo só com dígitos e pontuação de documento/CNJ — ex.: "0001234-56.2024",
# "123.456.789-09" ou "000123456". Texto com letras não entra.
_RE_TERMO_NUMERICO = re.compile(r"[\d.\-/\s]*\d[\d.\-/\s]*")


def ordenar(queryset, request, colunas, padrao):
    """Aplica `?ordem=<chave>` (ou `-<chave>`, decrescente).

    `colunas` mapeia a chave pública para os campos ORM; chave
    desconhecida cai no `padrao`. Devolve (queryset, ordem_efetiva).
    """
    ordem = request.GET.get("ordem") or padrao
    if ordem.lstrip("-") not in colunas:
        ordem = padrao
    decrescente = ordem.startswith("-")
    campos = colunas[ordem.lstrip("-")]
    expressoes = [
        F(campo).desc(nulls_last=True) if decrescente else F(campo).asc(nulls_last=True)
        for campo in campos
    ]
    # pk no fim deixa a ordem estável entre páginas quando há empate.
    return queryset.order_by(*expressoes, "pk"), ordem


def paginar(request, queryset, por_pagina=POR_PAGINA):
    """Página pedida em `?pagina=`; número inválido ou fora do intervalo
    cai na primeira/última página, como no `Paginator.get_page`."""
    return Paginator(queryset, por_pagina).get_page(request.GET.get("pagina"))


def digitos_da_busca(busca):
    """Dígitos do termo quando ele é só número/pontuação; senão ""."""
    if _RE_TERMO_NUMERICO.fullmatch(busca):
        return re.sub(r"\D", "", busca)
    return ""


def somente_digitos(campo):
    """Expressão SQL com só os dígitos do campo — casa CNJ/CPF/CNPJ
    digitados com ou sem pontuação."""
    return Func(F(campo), Value(r"\D"), Value(""), Value("g"), function="regexp_replace")
