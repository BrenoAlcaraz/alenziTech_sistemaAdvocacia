"""Montagem das visões da tela Agenda Jurídica (Meu dia, Calendário e
Kanban) a partir de uma única lista de itens já filtrada e autorizada
pela view — aqui só se agrupa e ordena, nunca se amplia o que é visto."""

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from .models import (
    STATUS_A_FAZER,
    STATUS_CONCLUIDO,
    STATUS_EM_ANDAMENTO,
    STATUS_ENCERRADOS,
    ItemAgenda,
)


MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
DIAS_SEMANA = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]

# Cor sólida de cada tipo (ponto do calendário e marca do card).
CORES_TIPO = {
    "tarefa": "#2563eb",
    "prazo": "#b45309",
    "protocolo": "#6b7280",
    "retorno": "#0d9488",
    "audiencia": "#dc2626",
    "reuniao": "#15803d",
    "pericia": "#a21caf",
    "julgamento": "#292524",
}

ORDENS_KANBAN = [
    ("prazo_proximo", "Prazo mais próximo"),
    ("prazo_distante", "Prazo mais distante"),
    ("prioridade_alta", "Prioridade mais alta"),
    ("prioridade_baixa", "Prioridade mais baixa"),
    ("mais_recentes", "Mais recentes"),
    ("mais_antigas", "Mais antigas"),
]
ORDEM_KANBAN_PADRAO = "prazo_proximo"
_PESO_PRIORIDADE = {"alta": 0, "media": 1, "baixa": 2}


def legenda_tipos():
    return [
        {"tipo": tipo, "rotulo": rotulo, "cor": CORES_TIPO[tipo]}
        for tipo, rotulo in ItemAgenda.TIPO_CHOICES
    ]


# ── Meu dia / Semana ─────────────────────────────────────────────────────


def grupos_meu_dia(itens, hoje):
    """Atrasados · Hoje · Amanhã · Próximos 7 dias · Sem data — cada item
    num só grupo. Concluído já passado e item além de 7 dias ficam só no
    calendário/kanban; afazer sem data encerrado fica só no kanban."""
    grupos = {chave: [] for chave in ("atrasados", "hoje", "amanha", "proximos", "sem_data")}
    amanha = hoje + timedelta(days=1)
    limite = hoje + timedelta(days=7)
    for item in itens:
        data = item.data_referencia
        if item.atrasado:
            grupos["atrasados"].append(item)
        elif data is None:
            if item.status not in STATUS_ENCERRADOS:
                grupos["sem_data"].append(item)
        elif data == hoje:
            grupos["hoje"].append(item)
        elif data == amanha:
            grupos["amanha"].append(item)
        elif amanha < data <= limite:
            grupos["proximos"].append(item)
    rotulos = [
        ("atrasados", "Atrasados"),
        ("hoje", "Hoje"),
        ("amanha", "Amanhã"),
        ("proximos", "Próximos 7 dias"),
        ("sem_data", "Sem data"),
    ]
    return [{"chave": chave, "rotulo": rotulo, "itens": grupos[chave]} for chave, rotulo in rotulos]


# ── Calendário mensal ────────────────────────────────────────────────────


def mes_adjacente(ano, mes, delta):
    indice = (ano * 12 + (mes - 1)) + delta
    return indice // 12, indice % 12 + 1


def grade_do_mes(ano, mes):
    """(offset a partir de domingo, dias no mês) — célula vazia só antes
    do dia 1."""
    _, dias_no_mes = monthrange(ano, mes)
    offset_domingo = (date(ano, mes, 1).weekday() + 1) % 7
    return offset_domingo, dias_no_mes


def calendario(itens, ano, mes, dia_selecionado, hoje):
    """Afazer cai na data para fazer (ou na fatal, se só houver ela) e
    evento no início; o dia da fatal de um afazer aberto ganha marcador
    próprio. Afazer sem data nunca entra."""
    offset_domingo, dias_no_mes = grade_do_mes(ano, mes)
    tipos_presentes = defaultdict(set)
    dias_com_fatal = set()
    itens_do_dia = []
    data_selecionada = date(ano, mes, dia_selecionado)
    for item in itens:
        data = item.data_referencia
        if data and (data.year, data.month) == (ano, mes):
            tipos_presentes[data.day].add(item.tipo)
            if data == data_selecionada:
                itens_do_dia.append(item)
        fatal = item.data_fatal
        if fatal and (fatal.year, fatal.month) == (ano, mes) and item.status not in STATUS_ENCERRADOS:
            dias_com_fatal.add(fatal.day)

    dias = [
        {
            "numero": numero,
            "hoje": date(ano, mes, numero) == hoje,
            "selecionado": numero == dia_selecionado,
            "fatal": numero in dias_com_fatal,
            "tipos": [
                {"tipo": tipo, "cor": CORES_TIPO[tipo]}
                for tipo, _ in ItemAgenda.TIPO_CHOICES
                if tipo in tipos_presentes[numero]
            ],
        }
        for numero in range(1, dias_no_mes + 1)
    ]
    ano_anterior, mes_anterior = mes_adjacente(ano, mes, -1)
    ano_seguinte, mes_seguinte = mes_adjacente(ano, mes, 1)
    return {
        "cal_ano": ano,
        "cal_mes": mes,
        "cal_mes_nome": MESES[mes - 1],
        "cal_offset_domingo": range(offset_domingo),
        "cal_dias": dias,
        "cal_ano_anterior": ano_anterior,
        "cal_mes_anterior": mes_anterior,
        "cal_ano_seguinte": ano_seguinte,
        "cal_mes_seguinte": mes_seguinte,
        "cal_hoje_ano": hoje.year,
        "cal_hoje_mes": hoje.month,
        "cal_data_selecionada_label": (
            f"{dia_selecionado} de {MESES[mes - 1].lower()} — "
            f"{DIAS_SEMANA[data_selecionada.weekday()]}"
        ),
        "itens_dia": itens_do_dia,
    }


# ── Kanban ───────────────────────────────────────────────────────────────


def _prazo(item):
    return item.data_fatal or item.data_para_fazer


def _chave_ordem(ordem):
    if ordem == "prazo_distante":
        return lambda i: (_prazo(i) is None, -(_prazo(i).toordinal()) if _prazo(i) else 0, i.titulo)
    if ordem == "prioridade_alta":
        return lambda i: (_PESO_PRIORIDADE.get(i.prioridade, 1), i.titulo)
    if ordem == "prioridade_baixa":
        return lambda i: (-_PESO_PRIORIDADE.get(i.prioridade, 1), i.titulo)
    if ordem == "mais_recentes":
        return lambda i: -i.criado_em.timestamp()
    if ordem == "mais_antigas":
        return lambda i: i.criado_em.timestamp()
    return lambda i: (_prazo(i) is None, _prazo(i) or date.min, i.titulo)


def colunas_kanban(itens, ordem):
    """Só afazeres, uma coluna por status operacional (cancelado fica na
    página Cancelados)."""
    afazeres = sorted((i for i in itens if not i.eh_evento), key=_chave_ordem(ordem))
    colunas = [
        (STATUS_A_FAZER, "A fazer"),
        (STATUS_EM_ANDAMENTO, "Em andamento"),
        (STATUS_CONCLUIDO, "Concluído"),
    ]
    return [
        {"status": status, "rotulo": rotulo, "itens": [i for i in afazeres if i.status == status]}
        for status, rotulo in colunas
    ]
