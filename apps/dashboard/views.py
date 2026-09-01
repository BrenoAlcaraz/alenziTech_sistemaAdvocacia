from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    MODULO_CLIENTES,
    MODULO_FINANCEIRO,
    MODULO_PROCESSOS,
    MODULO_TAREFAS,
)
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.tarefas.models import Tarefa
from apps.agenda.models import Compromisso
from apps.financeiro.models import LancamentoFinanceiro


def _formatar_moeda(valor):
    valor = valor or Decimal("0")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@login_required
def painel(request):
    hoje = timezone.localdate()

    acesso_clientes = tem_permissao_modulo(request.user, MODULO_CLIENTES)
    acesso_processos = tem_permissao_modulo(request.user, MODULO_PROCESSOS)
    acesso_tarefas = tem_permissao_modulo(request.user, MODULO_TAREFAS)
    acesso_agenda = tem_permissao_modulo(request.user, MODULO_AGENDA)
    acesso_financeiro = tem_permissao_modulo(request.user, MODULO_FINANCEIRO)

    resumo = {}

    if acesso_clientes:
        resumo["clientes_ativos"] = Cliente.objects.filter(ativo=True).count()

    if acesso_processos:
        resumo["processos_ativos"] = Processo.objects.filter(status="ativo").count()

    if acesso_tarefas:
        resumo["tarefas_pendentes"] = Tarefa.objects.exclude(
            status__in=["concluida", "cancelada"]
        ).count()

    if acesso_agenda:
        resumo["compromissos_proximos"] = Compromisso.objects.filter(
            status="agendado",
            data_hora_inicio__date__gte=hoje,
            data_hora_inicio__date__lte=hoje + timedelta(days=7),
        ).count()

    if acesso_financeiro:
        a_receber = (
            LancamentoFinanceiro.objects.filter(tipo="receita", status="pendente")
            .aggregate(total=Sum("valor"))["total"]
            or Decimal("0")
        )
        a_pagar = (
            LancamentoFinanceiro.objects.filter(tipo="despesa", status="pendente")
            .aggregate(total=Sum("valor"))["total"]
            or Decimal("0")
        )
        resumo["a_receber"] = _formatar_moeda(a_receber)
        resumo["a_pagar"] = _formatar_moeda(a_pagar)

    tarefas_dashboard = (
        Tarefa.objects.select_related("cliente", "processo", "responsavel")
        .exclude(status__in=["concluida", "cancelada"])
        .order_by("prazo", "-prioridade")[:5]
        if acesso_tarefas
        else Tarefa.objects.none()
    )

    compromissos_dashboard = (
        Compromisso.objects.select_related("cliente", "processo", "responsavel")
        .filter(
            status="agendado",
            data_hora_inicio__date__gte=hoje,
            data_hora_inicio__date__lte=hoje + timedelta(days=7),
        )
        .order_by("data_hora_inicio")[:5]
        if acesso_agenda
        else Compromisso.objects.none()
    )

    financeiro_dashboard = (
        LancamentoFinanceiro.objects.select_related("cliente", "processo", "responsavel")
        .filter(status="pendente")
        .order_by("data_vencimento")[:5]
        if acesso_financeiro
        else LancamentoFinanceiro.objects.none()
    )

    assinatura = getattr(request.tenant, "assinatura", None)
    plano_nome = assinatura.plano.nome if assinatura else None

    return render(request, "dashboard/painel.html", {
        "resumo": resumo,
        "tarefas_dashboard": tarefas_dashboard,
        "compromissos_dashboard": compromissos_dashboard,
        "financeiro_dashboard": financeiro_dashboard,
        "acesso_clientes": acesso_clientes,
        "acesso_processos": acesso_processos,
        "acesso_tarefas": acesso_tarefas,
        "acesso_agenda": acesso_agenda,
        "acesso_financeiro": acesso_financeiro,
        "plano_nome": plano_nome,
        "item_ativo": "painel",
    })
