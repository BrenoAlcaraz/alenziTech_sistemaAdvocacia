from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.utils import timezone

from apps.accounts.permissoes import tem_permissao_modulo, nivel_acesso_modulo
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    MODULO_CLIENTES,
    MODULO_FINANCEIRO,
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
from apps.processos.models import Processo
from apps.tarefas.models import Tarefa
from apps.agenda.models import Compromisso, ParticipanteCompromisso
from apps.financeiro.models import LancamentoFinanceiro


_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}
_NIVEIS_FINANCEIRO_DADOS = {NIVEL_DADOS_PROPRIOS, NIVEL_DADOS_TODOS}
_NIVEIS_FINANCEIRO_VALIDOS = {NIVEL_SOLICITACOES, *_NIVEIS_FINANCEIRO_DADOS}


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

    resumo = {}

    if acesso_clientes:
        qs_clientes = Cliente.objects.filter(ativo=True)
        if _nivel_escopo(request.user, MODULO_CLIENTES) == NIVEL_SOMENTE_SEUS:
            qs_clientes = qs_clientes.filter(responsavel=request.user)
        resumo["clientes_ativos"] = qs_clientes.count()

    if acesso_processos:
        qs_processos = Processo.objects.filter(status="ativo")
        if _nivel_escopo(request.user, MODULO_PROCESSOS) == NIVEL_SOMENTE_SEUS:
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

    if acesso_financeiro:
        qs_lancamentos = LancamentoFinanceiro.objects.all()
        if _nivel_financeiro(request.user) == NIVEL_DADOS_PROPRIOS:
            qs_lancamentos = qs_lancamentos.filter(responsavel=request.user)
        a_receber = (
            qs_lancamentos.filter(tipo="receita", status="pendente")
            .aggregate(total=Sum("valor"))["total"]
            or Decimal("0")
        )
        a_pagar = (
            qs_lancamentos.filter(tipo="despesa", status="pendente")
            .aggregate(total=Sum("valor"))["total"]
            or Decimal("0")
        )
        resumo["a_receber"] = _formatar_moeda(a_receber)
        resumo["a_pagar"] = _formatar_moeda(a_pagar)

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

    assinatura = getattr(request.tenant, "assinatura", None)
    plano_nome = assinatura.plano.nome if assinatura else None

    return render(request, "dashboard/painel.html", {
        "resumo": resumo,
        "tarefas_dashboard": tarefas_dashboard,
        "compromissos_dashboard": compromissos_dashboard,
        "compromissos_pendentes_dashboard": compromissos_pendentes_dashboard,
        "financeiro_dashboard": financeiro_dashboard,
        "acesso_clientes": acesso_clientes,
        "acesso_processos": acesso_processos,
        "acesso_tarefas": acesso_tarefas,
        "acesso_agenda": acesso_agenda,
        "acesso_financeiro": acesso_financeiro,
        "plano_nome": plano_nome,
        "item_ativo": "painel",
    })
