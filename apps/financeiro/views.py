from collections import defaultdict
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.permissoes import nivel_acesso_modulo, tem_permissao_modulo, tem_habilitacao
from apps.accounts.permissoes_constants import (
    HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO,
    MODULO_FINANCEIRO,
    NIVEL_DADOS,
    NIVEL_SOLICITACOES,
)
from apps.notificacoes.models import Notificacao

from .forms import LancamentoFinanceiroForm, CustaJudicialForm, SolicitacaoFinanceiraForm
from .models import LancamentoFinanceiro, CustaJudicial, SolicitacaoFinanceira


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


_NIVEIS_FINANCEIRO_VALIDOS = {NIVEL_SOLICITACOES, NIVEL_DADOS}


def _nivel_financeiro(user):
    nivel = nivel_acesso_modulo(user, MODULO_FINANCEIRO)
    if nivel not in _NIVEIS_FINANCEIRO_VALIDOS:
        return NIVEL_SOLICITACOES
    return nivel


def _exige_nivel_dados(user):
    if _nivel_financeiro(user) != NIVEL_DADOS:
        raise PermissionDenied


@login_required
def index(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    if _nivel_financeiro(request.user) != NIVEL_DADOS:
        # Entrada única do módulo na sidebar — nível "solicitacoes" não
        # alcança o caixa geral, então é levado direto às solicitações.
        return redirect("financeiro:solicitacoes_lista")
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
    _exige_nivel_dados(request.user)
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
    _exige_nivel_dados(request.user)
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
    _exige_nivel_dados(request.user)
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
    _exige_nivel_dados(request.user)
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
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    if request.method == "POST":
        lancamento.status = "cancelado"
        lancamento.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def reabrir_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    origem = getattr(lancamento, "solicitacao_origem", None)
    if origem is not None and not tem_habilitacao(
        request.user, MODULO_FINANCEIRO, HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO
    ):
        raise PermissionDenied
    if request.method == "POST":
        lancamento.status = "pendente"
        lancamento.data_pagamento = None
        lancamento.save(update_fields=["status", "data_pagamento"])
        if origem is not None and origem.solicitante_id and origem.solicitante_id != request.user.id:
            Notificacao.objects.create(
                destinatario=origem.solicitante,
                mensagem=f'Lançamento reaberto: "{lancamento.descricao}"',
            )
    return _redirect_seguro(request)


@login_required
def excluir_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(LancamentoFinanceiro, pk=pk)
    if hasattr(lancamento, "solicitacao_origem"):
        raise PermissionDenied
    if request.method == "POST":
        lancamento.delete()
    return _redirect_seguro(request)


@login_required
def form_custa(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
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


def _solicitacoes_no_escopo(request):
    qs = SolicitacaoFinanceira.objects.select_related("cliente", "processo", "solicitante", "lancamento")
    if _nivel_financeiro(request.user) != NIVEL_DADOS:
        qs = qs.filter(solicitante=request.user)
    return qs


_ACOES_SOLICITACAO = {
    "analisar": "em_analise",
    "aprovar": "aprovada",
    "rejeitar": "rejeitada",
    "pagar": "paga",
}


@login_required
def solicitacoes_lista(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    return render(request, "financeiro/solicitacoes_lista.html", {
        "solicitacoes": _solicitacoes_no_escopo(request),
        "nivel": _nivel_financeiro(request.user),
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def form_solicitacao(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    if request.method == "POST":
        form = SolicitacaoFinanceiraForm(request.POST, request.FILES)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.solicitante = request.user
            if solicitacao.processo and not solicitacao.cliente:
                solicitacao.cliente = solicitacao.processo.cliente
            solicitacao.save()
            return redirect("financeiro:solicitacoes_lista")
    else:
        form = SolicitacaoFinanceiraForm()

    return render(request, "financeiro/form_solicitacao.html", {
        "form": form,
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def detalhe_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    solicitacao = get_object_or_404(_solicitacoes_no_escopo(request), pk=pk)
    return render(request, "financeiro/detalhe_solicitacao.html", {
        "solicitacao": solicitacao,
        "pode_processar": _nivel_financeiro(request.user) == NIVEL_DADOS,
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def anexo_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    solicitacao = get_object_or_404(_solicitacoes_no_escopo(request), pk=pk)
    if not solicitacao.anexo:
        raise Http404
    return FileResponse(solicitacao.anexo.open("rb"), filename=solicitacao.anexo.name.rsplit("/", 1)[-1])


@login_required
def processar_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    solicitacao = get_object_or_404(SolicitacaoFinanceira, pk=pk)
    if request.method == "POST":
        novo_status = _ACOES_SOLICITACAO.get(request.POST.get("acao"))
        if novo_status is None or not solicitacao.pode_transicionar_para(novo_status):
            raise PermissionDenied
        solicitacao.avancar_para(novo_status)
    return redirect("financeiro:detalhe_solicitacao", pk=solicitacao.pk)
