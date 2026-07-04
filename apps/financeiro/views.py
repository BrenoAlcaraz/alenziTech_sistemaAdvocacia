from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

from .forms import LancamentoFinanceiroForm
from .models import LancamentoFinanceiro


# Dados temporários — custas ainda não implementadas com dados reais
CUSTAS_MOCK = [
    {
        "id": 1,
        "descricao": "Custas de citação – Unimed (adiantado pelo escritório)",
        "valor": "R$ 740,00",
        "tipo": "adiantamento",
        "negativo": True,
        "cliente": "Unimed Regional",
        "data": "02/06/2026",
        "detalhe": "Pagamento adiantado pelo escritório • Unimed Regional",
    },
]

SALDO_CLIENTES_MOCK = [
    {"cliente": "Construtora Horizonte Ltda.", "saldo": "Crédito: R$ 3.150,00", "credito": True},
    {"cliente": "Unimed Regional", "saldo": "A cobrar: R$ 740,00", "credito": False},
]

RESUMO_MOCK = {
    "a_receber": "R$ 72.000,00",
    "recebido": "R$ 25.000,00",
    "despesas": "R$ 11.500,00",
    "saldo": "R$ 13.500,00",
}

FILTROS_LANCAMENTOS_VALIDOS = {
    "todos",
    "pendentes",
    "pagos",
    "atrasados",
    "receitas",
    "despesas",
    "mes_atual",
}


def _normalizar_filtro_lancamentos(filtro):
    if filtro in FILTROS_LANCAMENTOS_VALIDOS:
        return filtro
    return "todos"


def _formatar_moeda(valor):
    valor = valor or Decimal("0")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@login_required
def index(request):
    hoje = timezone.localdate()
    filtro = _normalizar_filtro_lancamentos(request.GET.get("filtro", "todos"))

    lancamentos = LancamentoFinanceiro.objects.select_related(
        "cliente",
        "processo",
        "responsavel",
    )

    if filtro == "pendentes":
        lancamentos = lancamentos.filter(status="pendente")
    elif filtro == "pagos":
        lancamentos = lancamentos.filter(status="pago")
    elif filtro == "atrasados":
        lancamentos = lancamentos.filter(
            status="pendente",
            data_vencimento__lt=hoje,
        )
    elif filtro == "receitas":
        lancamentos = lancamentos.filter(tipo="receita")
    elif filtro == "despesas":
        lancamentos = lancamentos.filter(tipo="despesa")
    elif filtro == "mes_atual":
        lancamentos = lancamentos.filter(
            data_vencimento__year=hoje.year,
            data_vencimento__month=hoje.month,
        )

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
    recebido_mes = (
        LancamentoFinanceiro.objects.filter(
            tipo="receita",
            status="pago",
            data_pagamento__year=hoje.year,
            data_pagamento__month=hoje.month,
        )
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )
    pago_mes = (
        LancamentoFinanceiro.objects.filter(
            tipo="despesa",
            status="pago",
            data_pagamento__year=hoje.year,
            data_pagamento__month=hoje.month,
        )
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )

    resumo = {
        "a_receber": _formatar_moeda(a_receber),
        "a_pagar": _formatar_moeda(a_pagar),
        "recebido_mes": _formatar_moeda(recebido_mes),
        "pago_mes": _formatar_moeda(pago_mes),
        "saldo_previsto": _formatar_moeda(a_receber - a_pagar),
    }

    return render(request, "financeiro/index.html", {
        "resumo": resumo,
        "lancamentos": lancamentos,
        "filtro": filtro,
        "aba_ativa": "lancamentos",
        "item_ativo": "financeiro",
    })


@login_required
def custas(request):
    return render(request, "financeiro/custas.html", {
        "resumo": RESUMO_MOCK,
        "custas": CUSTAS_MOCK,
        "saldo_clientes": SALDO_CLIENTES_MOCK,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def form_lancamento(request):
    if request.method == "POST":
        form = LancamentoFinanceiroForm(request.POST)
        if form.is_valid():
            lancamento = form.save(commit=False)
            if not lancamento.responsavel:
                lancamento.responsavel = request.user
            if lancamento.processo and not lancamento.cliente:
                lancamento.cliente = lancamento.processo.cliente
            lancamento.save()
            return redirect("financeiro:index")
    else:
        form = LancamentoFinanceiroForm(initial={"responsavel": request.user})

    return render(request, "financeiro/form_lancamento.html", {
        "form": form,
        "modo": "novo",
        "aba_ativa": "lancamentos",
        "item_ativo": "financeiro",
    })


@login_required
def form_custa(request):
    return render(request, "financeiro/form_custa.html", {"item_ativo": "financeiro"})
