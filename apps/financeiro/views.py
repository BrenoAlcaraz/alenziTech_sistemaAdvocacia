from collections import defaultdict
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO

from .forms import LancamentoFinanceiroForm, CustaJudicialForm
from .models import LancamentoFinanceiro, CustaJudicial


def _redirect_seguro(request):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("financeiro:index")


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
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
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
        "next_url": request.get_full_path(),
        "aba_ativa": "lancamentos",
        "item_ativo": "financeiro",
    })


@login_required
def custas(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    custas_qs = list(
        CustaJudicial.objects.select_related("cliente", "processo").order_by("-data", "-criado_em")
    )

    saldos = defaultdict(lambda: Decimal("0"))
    nomes_clientes = {}
    for c in custas_qs:
        if c.cliente_id:
            if c.tipo == "deposito_cliente":
                saldos[c.cliente_id] += c.valor
            else:
                saldos[c.cliente_id] -= c.valor
            nomes_clientes[c.cliente_id] = str(c.cliente)

    saldo_clientes = []
    for cid in sorted(nomes_clientes, key=lambda k: nomes_clientes[k]):
        saldo = saldos[cid]
        if saldo == 0:
            continue
        credito = saldo > 0
        abs_saldo = abs(saldo)
        prefixo = "Crédito: " if credito else "A cobrar: "
        saldo_clientes.append({
            "cliente": nomes_clientes[cid],
            "saldo": prefixo + _formatar_moeda(abs_saldo),
            "credito": credito,
        })

    return render(request, "financeiro/custas.html", {
        "custas": custas_qs,
        "saldo_clientes": saldo_clientes,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def form_lancamento(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
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
def editar_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)

    if request.method == "POST":
        form = LancamentoFinanceiroForm(request.POST, instance=lancamento)
        if form.is_valid():
            lancamento = form.save(commit=False)
            if not lancamento.responsavel:
                lancamento.responsavel = request.user
            if lancamento.processo and not lancamento.cliente:
                lancamento.cliente = lancamento.processo.cliente
            lancamento.save()
            return redirect("financeiro:index")
    else:
        form = LancamentoFinanceiroForm(instance=lancamento)

    return render(request, "financeiro/form_lancamento.html", {
        "form": form,
        "modo": "editar",
        "lancamento": lancamento,
        "aba_ativa": "lancamentos",
        "item_ativo": "financeiro",
    })


@login_required
def marcar_pago(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    if request.method == "POST":
        lancamento.status = "pago"
        lancamento.data_pagamento = timezone.localdate()
        lancamento.save(update_fields=["status", "data_pagamento"])
    return _redirect_seguro(request)


@login_required
def cancelar_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    if request.method == "POST":
        lancamento.status = "cancelado"
        lancamento.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def reabrir_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    if request.method == "POST":
        lancamento.status = "pendente"
        lancamento.data_pagamento = None
        lancamento.save(update_fields=["status", "data_pagamento"])
    return _redirect_seguro(request)


@login_required
def excluir_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    if request.method == "POST":
        lancamento.delete()
    return _redirect_seguro(request)


@login_required
def form_custa(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    if request.method == "POST":
        form = CustaJudicialForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("financeiro:custas")
    else:
        form = CustaJudicialForm(initial={"data": timezone.localdate()})

    return render(request, "financeiro/form_custa.html", {
        "form": form,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })
