"""
Motor de dias úteis do cálculo de prazo processual — único, compartilhado
entre o prazo pelo texto da intimação (PDR-0037) e o futuro cálculo por
catálogo legal. Dias não úteis: fins de semana, feriados nacionais
(settings) e, só na contagem, o recesso forense. Feriado local e
suspensão do tribunal ficam fora.
"""

from datetime import date, datetime, timedelta
from functools import lru_cache

from django.conf import settings


def _pascoa(ano):
    # Algoritmo de Meeus/Jones/Butcher (calendário gregoriano).
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def _dia_mes(texto):
    dia, mes = texto.strip().split("/")
    return int(mes), int(dia)


@lru_cache(maxsize=64)
def _feriados_do_ano(ano, fixos, avulsos):
    feriados = {date(ano, mes, dia) for mes, dia in (_dia_mes(f) for f in fixos if f.strip())}
    feriados.add(_pascoa(ano) - timedelta(days=2))
    feriados.update(d for d in (datetime.strptime(a.strip(), "%Y-%m-%d").date() for a in avulsos) if d.year == ano)
    return frozenset(feriados)


def eh_feriado(data):
    return data in _feriados_do_ano(
        data.year, tuple(settings.FERIADOS_NACIONAIS), tuple(settings.FERIADOS_AVULSOS)
    )


def eh_dia_util(data):
    return data.weekday() < 5 and not eh_feriado(data)


def em_recesso(data):
    inicio, fim = (_dia_mes(p) for p in settings.RECESSO_FORENSE.split("-"))
    atual = (data.month, data.day)
    # O recesso atravessa a virada do ano (20/12 a 20/1).
    return atual >= inicio or atual <= fim


def proximo_dia_util(data):
    data += timedelta(days=1)
    while not eh_dia_util(data):
        data += timedelta(days=1)
    return data


def data_publicacao_djen(disponibilizacao):
    """Publicação = 1º dia útil após a disponibilização; o recesso não
    muda a publicação, só suspende a contagem."""
    return proximo_dia_util(disponibilizacao)


def contar_prazo(termo_inicial, dias, *, corridos=False):
    """Último dia do prazo: a contagem começa no dia seguinte ao termo
    inicial e não corre no recesso; em dias úteis também pula fins de
    semana e feriados."""
    data = termo_inicial
    contados = 0
    while contados < dias:
        data += timedelta(days=1)
        if em_recesso(data):
            continue
        if corridos or eh_dia_util(data):
            contados += 1
    return data


def vencimento_intimacao_djen(disponibilizacao, dias, *, corridos=False):
    return contar_prazo(data_publicacao_djen(disponibilizacao), dias, corridos=corridos)
