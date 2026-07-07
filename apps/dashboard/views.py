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


# Dados temporários apenas para layout — substituir na Mini-etapa 3
CASOS_MOCK = [
    {"titulo": "Construtora Horizonte vs. Município", "numero": "0801234-55.2024.8.19.0001", "area": "CÍVEL", "adm_count": 1},
    {"titulo": "Unimed – Contencioso de Massa", "numero": "0805678-99.2024.8.19.0001", "area": "CONSUMIDOR", "adm_count": 0},
    {"titulo": "Inventário Família Andrade", "numero": "0809999-11.2024.8.19.0001", "area": "SUCESSÕES", "adm_count": 1},
]


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

    return render(request, "dashboard/painel.html", {
        "resumo": resumo,
        "casos": CASOS_MOCK,
        "plano_nome": "Mestre",
        "item_ativo": "painel",
    })
