from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

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

    clientes_ativos = Cliente.objects.filter(ativo=True).count()

    processos_ativos = Processo.objects.filter(status="ativo").count()

    tarefas_pendentes = Tarefa.objects.exclude(status="concluida").count()

    compromissos_proximos = Compromisso.objects.filter(
        status="agendado",
        data_hora_inicio__date__gte=hoje,
        data_hora_inicio__date__lte=hoje + timedelta(days=7),
    ).count()

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

    resumo = {
        "clientes_ativos": clientes_ativos,
        "processos_ativos": processos_ativos,
        "tarefas_pendentes": tarefas_pendentes,
        "compromissos_proximos": compromissos_proximos,
        "a_receber": _formatar_moeda(a_receber),
        "a_pagar": _formatar_moeda(a_pagar),
    }

    tarefas_dashboard = (
        Tarefa.objects.select_related("cliente", "processo", "responsavel")
        .exclude(status="concluida")
        .order_by("prazo", "-prioridade")[:5]
    )

    compromissos_dashboard = (
        Compromisso.objects.select_related("cliente", "processo", "responsavel")
        .filter(
            status="agendado",
            data_hora_inicio__date__gte=hoje,
            data_hora_inicio__date__lte=hoje + timedelta(days=7),
        )
        .order_by("data_hora_inicio")[:5]
    )

    financeiro_dashboard = (
        LancamentoFinanceiro.objects.select_related("cliente", "processo", "responsavel")
        .filter(status="pendente")
        .order_by("data_vencimento")[:5]
    )

    return render(request, "dashboard/painel.html", {
        "resumo": resumo,
        "tarefas_dashboard": tarefas_dashboard,
        "compromissos_dashboard": compromissos_dashboard,
        "financeiro_dashboard": financeiro_dashboard,
        "plano_nome": "Mestre",
        "item_ativo": "painel",
    })
