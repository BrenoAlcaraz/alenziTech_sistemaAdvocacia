from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.models import Equipe
from apps.atividade.models import LogAtividade
from apps.accounts.permissoes import (
    nivel_acesso_modulo,
    nomes_papeis_usuario,
    tem_habilitacao,
    tem_permissao_modulo,
)
from apps.accounts.permissoes_constants import (
    HAB_GERIR_CRIAR_USUARIO,
    MODULO_AGENDA,
    MODULO_CLIENTES,
    MODULO_FINANCEIRO,
    MODULO_GERIR,
    MODULO_PAINEL,
    MODULO_PROCESSOS,
    MODULO_TAREFAS,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_DADOS_TODOS,
    NIVEL_SOLICITACOES,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.processos.models import Intimacao, MovimentacaoProcessual, Processo
from apps.processos.services import patrocinio_do_processo, responsaveis_elegiveis
from apps.tarefas.models import Tarefa
from apps.agenda.models import Compromisso, ParticipanteCompromisso
from apps.financeiro.models import LancamentoFinanceiro, SolicitacaoFinanceira
from apps.financeiro.services import (
    custas_em_debito,
    honorarios_do_mes,
    pendencias_do_dia,
    resumo_solicitacoes_abertas,
    saldo_previsto,
    totais_do_mes,
)


User = get_user_model()

_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}
_NIVEIS_FINANCEIRO_DADOS = {NIVEL_DADOS_PROPRIOS, NIVEL_DADOS_TODOS}
_NIVEIS_FINANCEIRO_VALIDOS = {NIVEL_SOLICITACOES, *_NIVEIS_FINANCEIRO_DADOS}
_NAO_INFORMADO = "__na__"
DIAS_SOLICITACOES_PAGAS = 7


def _nivel_escopo(user, modulo):
    """Nível somente_seus/todos do usuário no módulo, com fallback restritivo."""
    nivel = nivel_acesso_modulo(user, modulo)
    if nivel not in _ESCOPOS_VALIDOS:
        return NIVEL_SOMENTE_SEUS
    return nivel


def _nivel_financeiro(user):
    nivel = nivel_acesso_modulo(user, MODULO_FINANCEIRO)
    if nivel not in _NIVEIS_FINANCEIRO_VALIDOS:
        return NIVEL_SOLICITACOES
    return nivel


def _tem_acesso_dados_financeiro(user):
    return _nivel_financeiro(user) in _NIVEIS_FINANCEIRO_DADOS


def _pode_ver_painel_gestor(user):
    """Administrador do escritório ou quem tem o módulo `gerir`
    habilitado — specs/dashboard-painel-do-gestor.md."""
    return usuario_admin_escritorio(user) or tem_permissao_modulo(user, MODULO_GERIR)


def _formatar_moeda(valor):
    valor = valor or Decimal("0")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _compromissos_confirmados(user, hoje):
    """
    Compromissos dos próximos 7 dias onde `user` é responsável ou
    participante confirmado — sempre pessoal, independente do nível
    somente_seus/todos do módulo Agenda (só rege a tela de Agenda).
    """
    return Compromisso.objects.filter(
        status="agendado",
        data_hora_inicio__date__gte=hoje,
        data_hora_inicio__date__lte=hoje + timedelta(days=7),
    ).filter(
        Q(responsavel=user)
        | Q(
            participacoes__usuario=user,
            participacoes__status=ParticipanteCompromisso.STATUS_CONFIRMADO,
        )
    ).distinct()


# ── Painéis derivados de Processos (Visão geral) ────────────────────────────

def _processos_escopo_ativos(user, escopo):
    """Processos não arquivados no escopo somente_seus/todos do usuário."""
    qs = Processo.objects.exclude(status="arquivado").prefetch_related("clientes")
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(responsavel=user)
    return qs


def _movimentacao_processual(processos_qs):
    """Processos com alguma MovimentacaoProcessual nas últimas 24h/7 dias."""
    agora = timezone.now()

    def _lista(desde):
        movimentacoes = (
            MovimentacaoProcessual.objects.filter(processo__in=processos_qs, data__gte=desde)
            .select_related("processo")
            .order_by("-data")
        )
        vistos = {}
        for mov in movimentacoes:
            vistos.setdefault(mov.processo_id, {"processo": mov.processo, "movimentacao": mov})
        return list(vistos.values())

    lista_24h = _lista(agora - timedelta(hours=24))
    lista_7dias = _lista(agora - timedelta(days=7))
    return {
        "24h": {"total": len(lista_24h), "processos": lista_24h},
        "7dias": {"total": len(lista_7dias), "processos": lista_7dias},
    }


def _processos_paralisados(processos_qs, hoje):
    """Processos sem movimento há +1/+3/+6 meses (cumulativo), usando o
    último andamento ou, na ausência, a data de distribuição."""
    anotados = processos_qs.annotate(ultima_movimentacao=Max("movimentacoes__data"))
    grupos = {"1mes": [], "3meses": [], "6meses": []}
    for processo in anotados:
        if processo.ultima_movimentacao:
            referencia = timezone.localtime(processo.ultima_movimentacao).date()
        else:
            referencia = processo.data_distribuicao
        if not referencia:
            continue
        dias_parado = (hoje - referencia).days
        item = {"processo": processo, "referencia": referencia, "dias_parado": dias_parado}
        if dias_parado > 30:
            grupos["1mes"].append(item)
        if dias_parado > 90:
            grupos["3meses"].append(item)
        if dias_parado > 180:
            grupos["6meses"].append(item)
    return {chave: {"total": len(itens), "processos": itens} for chave, itens in grupos.items()}


def _prazos_a_vencer(processos_qs, hoje):
    """Processos com prazo_proximo a vencer hoje/amanhã/em até 3/5 dias (cumulativo)."""
    grupos = {"hoje": [], "amanha": [], "3dias": [], "5dias": []}
    qs = processos_qs.filter(prazo_proximo__isnull=False, prazo_proximo__gte=hoje).order_by("prazo_proximo")
    for processo in qs:
        dias = (processo.prazo_proximo - hoje).days
        if dias == 0:
            grupos["hoje"].append(processo)
        if dias == 1:
            grupos["amanha"].append(processo)
        if dias <= 3:
            grupos["3dias"].append(processo)
        if dias <= 5:
            grupos["5dias"].append(processo)
    return {chave: {"total": len(itens), "processos": itens} for chave, itens in grupos.items()}


def _moeda_e_quantidade(agregado):
    return {"total": _formatar_moeda(agregado["total"]), "quantidade": agregado["quantidade"]}


def _cards_solicitante(user, hoje):
    """Nível `solicitacoes`: só as próprias solicitações."""
    proprias = SolicitacaoFinanceira.objects.filter(solicitante=user)
    resumo = resumo_solicitacoes_abertas(proprias, hoje)
    inicio_janela = hoje - timedelta(days=DIAS_SOLICITACOES_PAGAS - 1)
    pagas = proprias.filter(status="paga", data_pagamento__gte=inicio_janela, data_pagamento__lte=hoje)
    agregado_pagas = pagas.aggregate(total=Sum("valor"), quantidade=Count("id"))
    return {
        "pendentes": {**resumo, "total": _formatar_moeda(resumo["total"])},
        "pagas": {
            **_moeda_e_quantidade(agregado_pagas),
            "query": urlencode({
                "situacao": "pagas", "pago_de": inicio_janela.isoformat(), "pago_ate": hoje.isoformat(),
            }),
        },
    }


def _cards_admin(hoje):
    """Administrador do escritório: visão do mês do escritório inteiro."""
    totais = totais_do_mes(LancamentoFinanceiro.objects.all(), hoje.year, hoje.month, incluir_custas=True)
    saldo = saldo_previsto(totais)
    realizado = totais["recebido"] - totais["pago"]
    honorarios = honorarios_do_mes(hoje.year, hoje.month)
    custas = custas_em_debito()
    return {
        "saldo_previsto": _formatar_moeda(abs(saldo)),
        "saldo_previsto_negativo": saldo < 0,
        "realizado": _formatar_moeda(abs(realizado)),
        "realizado_negativo": realizado < 0,
        "honorarios_previsto": _formatar_moeda(honorarios["previsto"]),
        "honorarios_recebido": _formatar_moeda(honorarios["recebido"]),
        "custas_a_cobrar": _moeda_e_quantidade(custas),
    }


def _cards_financeiros(user, hoje, *, acesso_dados):
    """Cards financeiros da Visão geral por nível de acesso
    (specs/painel-cards-financeiros.md). Cada número usa a mesma regra
    do filtro do Financeiro para onde o card leva."""
    if not acesso_dados:
        return {"solicitante": _cards_solicitante(user, hoje)}
    escopo = LancamentoFinanceiro.objects.all()
    if _nivel_financeiro(user) == NIVEL_DADOS_PROPRIOS:
        escopo = escopo.filter(responsavel=user)
    pendencias = pendencias_do_dia(escopo, hoje)
    fila = resumo_solicitacoes_abertas(SolicitacaoFinanceira.objects.all(), hoje)
    cards = {
        "pendencias": {
            chave: {janela: _moeda_e_quantidade(valores) for janela, valores in grupo.items()}
            for chave, grupo in pendencias.items()
        },
        "fila_solicitacoes": fila,
    }
    if usuario_admin_escritorio(user):
        cards["admin"] = _cards_admin(hoje)
    return cards


@login_required
def painel(request):
    if not tem_permissao_modulo(request.user, MODULO_PAINEL):
        raise PermissionDenied

    hoje = timezone.localdate()

    acesso_clientes = tem_permissao_modulo(request.user, MODULO_CLIENTES)
    acesso_processos = tem_permissao_modulo(request.user, MODULO_PROCESSOS)
    acesso_tarefas = tem_permissao_modulo(request.user, MODULO_TAREFAS)
    acesso_agenda = tem_permissao_modulo(request.user, MODULO_AGENDA)
    acesso_financeiro = (
        tem_permissao_modulo(request.user, MODULO_FINANCEIRO)
        and _tem_acesso_dados_financeiro(request.user)
    )
    # Perfil "solicitações": sem acesso ao caixa geral, só com os cards das
    # solicitações financeiras que ele mesmo abriu.
    acesso_financeiro_solicitacoes = (
        tem_permissao_modulo(request.user, MODULO_FINANCEIRO)
        and not acesso_financeiro
        and _nivel_financeiro(request.user) == NIVEL_SOLICITACOES
    )
    acesso_usuarios_ativos = tem_habilitacao(request.user, MODULO_GERIR, HAB_GERIR_CRIAR_USUARIO)

    resumo = {}

    if acesso_clientes:
        qs_clientes = Cliente.objects.filter(ativo=True)
        if _nivel_escopo(request.user, MODULO_CLIENTES) == NIVEL_SOMENTE_SEUS:
            qs_clientes = qs_clientes.filter(responsavel=request.user)
        resumo["clientes_ativos"] = qs_clientes.count()

    escopo_processos = _nivel_escopo(request.user, MODULO_PROCESSOS) if acesso_processos else None
    if acesso_processos:
        qs_processos = Processo.objects.filter(status="ativo")
        if escopo_processos == NIVEL_SOMENTE_SEUS:
            qs_processos = qs_processos.filter(responsavel=request.user)
        resumo["processos_ativos"] = qs_processos.count()

    escopo_tarefas = _nivel_escopo(request.user, MODULO_TAREFAS) if acesso_tarefas else None
    if acesso_tarefas:
        qs_tarefas = Tarefa.objects.exclude(status__in=["concluida", "cancelada"])
        if escopo_tarefas == NIVEL_SOMENTE_SEUS:
            qs_tarefas = qs_tarefas.filter(responsavel=request.user)
        resumo["tarefas_pendentes"] = qs_tarefas.count()

    if acesso_agenda:
        resumo["compromissos_proximos"] = _compromissos_confirmados(request.user, hoje).count()

    cards_financeiros = None
    if acesso_financeiro or acesso_financeiro_solicitacoes:
        cards_financeiros = _cards_financeiros(request.user, hoje, acesso_dados=acesso_financeiro)

    if acesso_usuarios_ativos:
        resumo["usuarios_ativos"] = User.objects.filter(is_active=True).count()

    tarefas_dashboard = Tarefa.objects.none()
    if acesso_tarefas:
        tarefas_dashboard = Tarefa.objects.select_related(
            "cliente", "processo", "responsavel"
        ).exclude(status__in=["concluida", "cancelada"])
        if escopo_tarefas == NIVEL_SOMENTE_SEUS:
            tarefas_dashboard = tarefas_dashboard.filter(responsavel=request.user)
        tarefas_dashboard = tarefas_dashboard.order_by("prazo", "-prioridade")[:5]

    compromissos_dashboard = Compromisso.objects.none()
    compromissos_pendentes_dashboard = ParticipanteCompromisso.objects.none()
    if acesso_agenda:
        compromissos_dashboard = _compromissos_confirmados(request.user, hoje).select_related(
            "cliente", "processo", "responsavel"
        ).order_by("data_hora_inicio")[:5]

        compromissos_pendentes_dashboard = ParticipanteCompromisso.objects.select_related(
            "compromisso", "compromisso__cliente", "compromisso__processo"
        ).filter(
            usuario=request.user,
            status=ParticipanteCompromisso.STATUS_PENDENTE,
            compromisso__status="agendado",
        ).order_by("compromisso__data_hora_inicio")

    financeiro_dashboard = LancamentoFinanceiro.objects.none()
    if acesso_financeiro:
        financeiro_dashboard = LancamentoFinanceiro.objects.select_related(
            "cliente", "processo", "responsavel"
        ).filter(status="pendente")
        if _nivel_financeiro(request.user) == NIVEL_DADOS_PROPRIOS:
            financeiro_dashboard = financeiro_dashboard.filter(responsavel=request.user)
        financeiro_dashboard = financeiro_dashboard.order_by("data_vencimento")[:5]

    movimentacao = None
    paralisados = None
    prazos = None
    intimacoes = None
    if acesso_processos:
        processos_escopo = _processos_escopo_ativos(request.user, escopo_processos)
        movimentacao = _movimentacao_processual(processos_escopo)
        paralisados = _processos_paralisados(processos_escopo, hoje)
        prazos = _prazos_a_vencer(processos_escopo, hoje)
        intimacoes = Intimacao.objects.filter(
            status="pendente", processo__in=processos_escopo
        ).select_related("processo").order_by("prazo_manifestacao")

    assinatura = getattr(request.tenant, "assinatura", None)
    plano_nome = assinatura.plano.nome if assinatura else None

    return render(request, "dashboard/painel.html", {
        "resumo": resumo,
        "tarefas_dashboard": tarefas_dashboard,
        "compromissos_dashboard": compromissos_dashboard,
        "compromissos_pendentes_dashboard": compromissos_pendentes_dashboard,
        "financeiro_dashboard": financeiro_dashboard,
        "cards_financeiros": cards_financeiros,
        "movimentacao": movimentacao,
        "paralisados": paralisados,
        "prazos": prazos,
        "intimacoes": intimacoes,
        "acesso_clientes": acesso_clientes,
        "acesso_processos": acesso_processos,
        "acesso_tarefas": acesso_tarefas,
        "acesso_agenda": acesso_agenda,
        "acesso_financeiro": acesso_financeiro,
        "acesso_financeiro_solicitacoes": acesso_financeiro_solicitacoes,
        "acesso_usuarios_ativos": acesso_usuarios_ativos,
        "acesso_gestor": _pode_ver_painel_gestor(request.user),
        "plano_nome": plano_nome,
        "item_ativo": "painel",
        "aba_ativa": "geral",
    })


# ── Análise de dados ─────────────────────────────────────────────────────────

def _rotulo_estado(valor):
    if valor == _NAO_INFORMADO:
        return "Não informado"
    return dict(Processo.UF_CHOICES).get(valor, valor)


def _rotulo_simples(valor):
    return "Não informado" if valor == _NAO_INFORMADO else valor


def _agrupar_por_campo(processos, campo):
    grupos = defaultdict(list)
    for processo in processos:
        valor = getattr(processo, campo) or _NAO_INFORMADO
        grupos[valor].append(processo)
    return grupos


def _barras(grupos, rotulador, total_geral):
    total_geral = total_geral or 1
    barras = [
        {
            "valor": valor,
            "label": rotulador(valor),
            "total": len(itens),
            "pct": round(len(itens) / total_geral * 100),
            "processos": itens,
        }
        for valor, itens in grupos.items()
    ]
    barras.sort(key=lambda b: -b["total"])
    return barras


_GRUPO_PATROCINIO_LABELS = {
    "polo_ativo": "Polo ativo (cliente autor/recorrente)",
    "polo_passivo": "Polo passivo (cliente réu/recorrido)",
    "outros": "Outros (terceiro/MP/etc.)",
    _NAO_INFORMADO: "Não identificado",
}


def _formatar_periodo(dias):
    if dias is None:
        return None
    dias = round(dias)
    meses, resto = divmod(dias, 30)
    if meses and resto:
        return f"{meses} {'mês' if meses == 1 else 'meses'} e {resto} dia{'s' if resto != 1 else ''}"
    if meses:
        return f"{meses} {'mês' if meses == 1 else 'meses'}"
    return f"{resto} dia{'s' if resto != 1 else ''}"


@login_required
def analise(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied

    hoje = timezone.localdate()
    nivel_maximo = nivel_acesso_modulo(request.user, MODULO_PROCESSOS)
    if nivel_maximo not in _ESCOPOS_VALIDOS:
        nivel_maximo = NIVEL_SOMENTE_SEUS

    mostrar_seletor_escopo = nivel_maximo == NIVEL_TODOS
    escopo_solicitado = request.GET.get("escopo")
    if mostrar_seletor_escopo and escopo_solicitado in _ESCOPOS_VALIDOS:
        escopo = escopo_solicitado
    else:
        escopo = nivel_maximo

    processos_qs = Processo.objects.select_related("equipe", "responsavel").prefetch_related(
        "partes", "movimentacoes", "clientes"
    )
    if escopo == NIVEL_SOMENTE_SEUS:
        processos_qs = processos_qs.filter(responsavel=request.user)

    cliente_id = request.GET.get("cliente") or ""
    equipe_id = request.GET.get("equipe") or ""
    usuario_id = request.GET.get("usuario") or ""
    mostrar_filtro_usuario = escopo == NIVEL_TODOS

    if cliente_id:
        processos_qs = processos_qs.filter(clientes__id=cliente_id)
    if equipe_id:
        processos_qs = processos_qs.filter(equipe_id=equipe_id)
    if mostrar_filtro_usuario and usuario_id:
        processos_qs = processos_qs.filter(responsavel_id=usuario_id)

    processos = list(processos_qs)
    total = len(processos)

    # Natureza
    grupos_natureza = _agrupar_por_campo(processos, "area_direito")
    natureza_barras = _barras(
        grupos_natureza,
        lambda v: dict(Processo.AREAS_CHOICES).get(v, v),
        total,
    )

    # Status
    grupos_status = _agrupar_por_campo(processos, "status")
    status_barras = _barras(
        grupos_status,
        lambda v: dict(Processo.STATUS_CHOICES).get(v, v),
        total,
    )

    # Fase do processo (Processo.fase já existente — Painel #3, specs/
    # painel-novos-recortes-analise.md — só expõe como bloco novo aqui).
    grupos_fase = _agrupar_por_campo(processos, "fase")
    fase_barras = _barras(
        grupos_fase,
        lambda v: dict(Processo.FASE_CHOICES).get(v, v),
        total,
    )

    # Fase do andamento atual (Painel #2) — só o campo manual; sugestão
    # automática por tipo de andamento fica pendente de validação do
    # sócio advogado (ver "Retomada desta spec" no arquivo da spec).
    grupos_fase_andamento = _agrupar_por_campo(processos, "fase_andamento_atual")
    fase_andamento_barras = _barras(
        grupos_fase_andamento,
        lambda v: "Não informado" if v == _NAO_INFORMADO else dict(Processo.FASE_ANDAMENTO_CHOICES).get(v, v),
        total,
    )

    # Patrocínio (best-effort por CPF/CNPJ)
    grupos_patrocinio = defaultdict(list)
    for processo in processos:
        grupo = patrocinio_do_processo(processo, partes=processo.partes.all())
        grupos_patrocinio[grupo or _NAO_INFORMADO].append(processo)
    patrocinio_barras = _barras(
        grupos_patrocinio,
        lambda v: _GRUPO_PATROCINIO_LABELS.get(v, v),
        total,
    )

    # Localidade hierárquica: Estado → Cidade → Comarca → Vara, com auto-skip
    loc_estado_qs = request.GET.get("loc_estado")
    loc_cidade_qs = request.GET.get("loc_cidade")
    loc_comarca_qs = request.GET.get("loc_comarca")

    grupos_estado = _agrupar_por_campo(processos, "estado")
    estado_opcoes = None
    if len(grupos_estado) <= 1:
        estado_ativo = next(iter(grupos_estado), None)
    elif loc_estado_qs in grupos_estado:
        estado_ativo = loc_estado_qs
    else:
        estado_ativo = None
        estado_opcoes = _barras(grupos_estado, _rotulo_estado, total)

    cidade_opcoes = None
    cidade_ativa = None
    grupos_cidade = {}
    if estado_ativo is not None:
        grupos_cidade = _agrupar_por_campo(grupos_estado[estado_ativo], "cidade")
        if len(grupos_cidade) <= 1:
            cidade_ativa = next(iter(grupos_cidade), None)
        elif loc_cidade_qs in grupos_cidade:
            cidade_ativa = loc_cidade_qs
        else:
            cidade_opcoes = _barras(grupos_cidade, _rotulo_simples, len(grupos_estado[estado_ativo]))

    comarca_opcoes = None
    comarca_ativa = None
    grupos_comarca = {}
    if cidade_ativa is not None:
        grupos_comarca = _agrupar_por_campo(grupos_cidade[cidade_ativa], "comarca")
        if len(grupos_comarca) <= 1:
            comarca_ativa = next(iter(grupos_comarca), None)
        elif loc_comarca_qs in grupos_comarca:
            comarca_ativa = loc_comarca_qs
        else:
            comarca_opcoes = _barras(grupos_comarca, _rotulo_simples, len(grupos_cidade[cidade_ativa]))

    vara_barras = []
    if comarca_ativa is not None:
        grupos_vara = _agrupar_por_campo(grupos_comarca[comarca_ativa], "vara")
        vara_barras = _barras(grupos_vara, _rotulo_simples, len(grupos_comarca[comarca_ativa]))

    breadcrumb = []
    if estado_ativo is not None:
        breadcrumb.append({
            "label": _rotulo_estado(estado_ativo),
            "clicavel": len(grupos_estado) > 1,
        })
    if cidade_ativa is not None:
        breadcrumb.append({
            "label": _rotulo_simples(cidade_ativa),
            "clicavel": len(grupos_cidade) > 1,
        })
    if comarca_ativa is not None:
        breadcrumb.append({
            "label": _rotulo_simples(comarca_ativa),
            "clicavel": len(grupos_comarca) > 1,
        })

    # Clientes por localidade: Estado → Cidade → Bairro, com auto-skip
    # (Painel #1, specs/painel-novos-recortes-analise.md) — espelha o
    # padrão de "Processos por localidade" acima, mas usa o endereço do
    # Cliente e fica restrito aos clientes vinculados aos processos já
    # filtrados pelo escopo/filtros desta página.
    clientes_vistos = {}
    for processo in processos:
        for cliente in processo.clientes.all():
            clientes_vistos[cliente.pk] = cliente
    clientes_localidade = list(clientes_vistos.values())
    total_clientes_localidade = len(clientes_localidade)

    cloc_estado_qs = request.GET.get("cloc_estado")
    cloc_cidade_qs = request.GET.get("cloc_cidade")

    grupos_cliente_estado = _agrupar_por_campo(clientes_localidade, "estado")
    cliente_estado_opcoes = None
    if len(grupos_cliente_estado) <= 1:
        cliente_estado_ativo = next(iter(grupos_cliente_estado), None)
    elif cloc_estado_qs in grupos_cliente_estado:
        cliente_estado_ativo = cloc_estado_qs
    else:
        cliente_estado_ativo = None
        cliente_estado_opcoes = _barras(grupos_cliente_estado, _rotulo_estado, total_clientes_localidade)

    cliente_cidade_opcoes = None
    cliente_cidade_ativa = None
    grupos_cliente_cidade = {}
    if cliente_estado_ativo is not None:
        grupos_cliente_cidade = _agrupar_por_campo(grupos_cliente_estado[cliente_estado_ativo], "cidade")
        if len(grupos_cliente_cidade) <= 1:
            cliente_cidade_ativa = next(iter(grupos_cliente_cidade), None)
        elif cloc_cidade_qs in grupos_cliente_cidade:
            cliente_cidade_ativa = cloc_cidade_qs
        else:
            cliente_cidade_opcoes = _barras(
                grupos_cliente_cidade, _rotulo_simples, len(grupos_cliente_estado[cliente_estado_ativo])
            )

    cliente_bairro_barras = []
    if cliente_cidade_ativa is not None:
        grupos_cliente_bairro = _agrupar_por_campo(grupos_cliente_cidade[cliente_cidade_ativa], "bairro")
        cliente_bairro_barras = _barras(
            grupos_cliente_bairro, _rotulo_simples, len(grupos_cliente_cidade[cliente_cidade_ativa])
        )

    cliente_loc_breadcrumb = []
    if cliente_estado_ativo is not None:
        cliente_loc_breadcrumb.append({
            "label": _rotulo_estado(cliente_estado_ativo),
            "clicavel": len(grupos_cliente_estado) > 1,
        })
    if cliente_cidade_ativa is not None:
        cliente_loc_breadcrumb.append({
            "label": _rotulo_simples(cliente_cidade_ativa),
            "clicavel": len(grupos_cliente_cidade) > 1,
        })

    # Tempo e resultados
    processos_ativos_tempo_vida = [
        p for p in processos if p.status == "ativo" and p.data_distribuicao
    ]
    if processos_ativos_tempo_vida:
        media_dias_vida = sum(
            (hoje - p.data_distribuicao).days for p in processos_ativos_tempo_vida
        ) / len(processos_ativos_tempo_vida)
    else:
        media_dias_vida = None

    medias_entre_andamentos = []
    for processo in processos:
        datas = sorted(m.data for m in processo.movimentacoes.all())
        if len(datas) < 2:
            continue
        intervalos = [(datas[i + 1] - datas[i]).days for i in range(len(datas) - 1)]
        medias_entre_andamentos.append(sum(intervalos) / len(intervalos))
    media_geral_entre_andamentos = (
        sum(medias_entre_andamentos) / len(medias_entre_andamentos)
        if medias_entre_andamentos else None
    )

    julgados = Counter(p.resultado_sentenca for p in processos if p.resultado_sentenca)

    filtros_querystring = urlencode({
        "escopo": escopo,
        "cliente": cliente_id,
        "equipe": equipe_id,
        "usuario": usuario_id,
    })

    contexto = {
        "item_ativo": "painel",
        "aba_ativa": "analise",
        "acesso_processos": True,
        "acesso_gestor": _pode_ver_painel_gestor(request.user),
        "mostrar_seletor_escopo": mostrar_seletor_escopo,
        "escopo_atual": escopo,
        "mostrar_filtro_usuario": mostrar_filtro_usuario,
        "cliente_id": cliente_id,
        "equipe_id": equipe_id,
        "usuario_id": usuario_id,
        "clientes_opcoes": Cliente.objects.filter(ativo=True).order_by("nome_razao_social"),
        "equipes_opcoes": Equipe.objects.filter(ativo=True).order_by("nome"),
        "usuarios_opcoes": responsaveis_elegiveis() if mostrar_filtro_usuario else User.objects.none(),
        "total_processos": total,
        "natureza_barras": natureza_barras,
        "status_barras": status_barras,
        "fase_barras": fase_barras,
        "fase_andamento_barras": fase_andamento_barras,
        "patrocinio_barras": patrocinio_barras,
        "loc_breadcrumb": breadcrumb,
        "loc_estado_ativo": estado_ativo,
        "loc_cidade_ativa": cidade_ativa,
        "loc_estado_opcoes": estado_opcoes,
        "loc_cidade_opcoes": cidade_opcoes,
        "loc_comarca_opcoes": comarca_opcoes,
        "loc_vara_barras": vara_barras,
        "loc_mostrando_estados": estado_opcoes is not None,
        "loc_mostrando_cidades": estado_ativo is not None and cidade_opcoes is not None,
        "loc_mostrando_comarcas": cidade_ativa is not None and comarca_opcoes is not None,
        "loc_mostrando_varas": comarca_ativa is not None,
        "total_clientes_localidade": total_clientes_localidade,
        "cloc_breadcrumb": cliente_loc_breadcrumb,
        "cloc_estado_ativo": cliente_estado_ativo,
        "cloc_cidade_ativa": cliente_cidade_ativa,
        "cloc_estado_opcoes": cliente_estado_opcoes,
        "cloc_cidade_opcoes": cliente_cidade_opcoes,
        "cloc_bairro_barras": cliente_bairro_barras,
        "cloc_mostrando_estados": cliente_estado_opcoes is not None,
        "cloc_mostrando_cidades": cliente_estado_ativo is not None and cliente_cidade_opcoes is not None,
        "cloc_mostrando_bairros": cliente_cidade_ativa is not None,
        "filtros_querystring": filtros_querystring,
        "tempo_vida_medio": _formatar_periodo(media_dias_vida),
        "tempo_entre_andamentos": _formatar_periodo(media_geral_entre_andamentos),
        "julgados_procedente": julgados.get("procedente", 0),
        "julgados_parcial": julgados.get("parcialmente_procedente", 0),
        "julgados_improcedente": julgados.get("improcedente", 0),
    }
    return render(request, "dashboard/analise.html", contexto)


# ── Painel do gestor ─────────────────────────────────────────────────────────

@login_required
def gestor(request):
    if not _pode_ver_painel_gestor(request.user):
        raise PermissionDenied

    hoje = timezone.localdate()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)
    usuarios = (
        User.objects.filter(is_active=True)
        .select_related("perfil")
        .prefetch_related("atribuicoes_papel__papel")
        .order_by("first_name", "last_name", "username")
    )
    usuarios_contexto = []
    for usuario in usuarios:
        produtivas = LogAtividade.objects.filter(usuario=usuario).exclude(
            tipo__in=LogAtividade.TIPOS_NAO_PRODUTIVOS
        )
        usuarios_contexto.append({
            "usuario": usuario,
            "papel_nome": nomes_papeis_usuario(usuario),
            "acoes_hoje": produtivas.filter(criado_em__date=hoje).count(),
            "acoes_semana": produtivas.filter(criado_em__date__gte=inicio_semana).count(),
            "acoes_mes": produtivas.filter(criado_em__date__gte=inicio_mes).count(),
        })

    return render(request, "dashboard/gestor.html", {
        "usuarios_contexto": usuarios_contexto,
        "acesso_processos": tem_permissao_modulo(request.user, MODULO_PROCESSOS),
        "acesso_gestor": True,
        "item_ativo": "painel",
        "aba_ativa": "gestor",
    })


@login_required
def minha_atividade(request):
    """Histórico de atividade do próprio usuário — qualquer usuário
    autenticado, independente do módulo `gerir`/Painel
    (specs/atividade-ampliar-catalogo.md). Estritamente escopado ao
    usuário logado, nunca a terceiros."""
    hoje = timezone.localdate()
    atividades = LogAtividade.objects.filter(
        usuario=request.user, criado_em__date=hoje
    ).order_by("criado_em")

    return render(request, "dashboard/minha_atividade.html", {
        "atividades": atividades,
        "item_ativo": "painel",
    })


@login_required
def gestor_usuario(request, user_pk):
    if not _pode_ver_painel_gestor(request.user):
        raise PermissionDenied

    usuario_alvo = get_object_or_404(User, pk=user_pk, is_active=True)
    hoje = timezone.localdate()
    atividades = LogAtividade.objects.filter(
        usuario=usuario_alvo, criado_em__date=hoje
    ).order_by("criado_em")

    return render(request, "dashboard/gestor_usuario.html", {
        "usuario_alvo": usuario_alvo,
        "atividades": atividades,
        "acesso_processos": tem_permissao_modulo(request.user, MODULO_PROCESSOS),
        "acesso_gestor": True,
        "item_ativo": "painel",
        "aba_ativa": "gestor",
    })
