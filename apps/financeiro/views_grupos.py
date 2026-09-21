"""Custas judiciais por grupo de clientes: extrato, Creditar, membros e o
aviso de saldo do formulário de débito. Mesma autorização das demais
rotas de custas (módulo Financeiro + nível de dados)."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO
from apps.clientes.models import Cliente

from .forms import CreditarCustaForm, GrupoCustasForm, MembroGrupoCustasForm
from .models import CustaJudicial, GrupoCustas, MembroGrupoCustas
from .services import (
    adicionar_membro_ao_grupo,
    excluir_grupo,
    registrar_credito_grupo,
    remover_membro_do_grupo,
    saldo_de_custas_do,
    saldo_do_grupo,
)
from .views import _exige_nivel_dados, _formatar_moeda, _formatar_saldo


def _exige_acesso_custas(user):
    if not tem_permissao_modulo(user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(user)


def _voltar_ao_grupo(grupo):
    return redirect("financeiro:extrato_custas_grupo", grupo_id=grupo.pk)


@login_required
def novo_grupo(request):
    _exige_acesso_custas(request.user)
    if request.method == "POST":
        form = GrupoCustasForm(request.POST)
        if form.is_valid():
            return _voltar_ao_grupo(form.save())
    else:
        form = GrupoCustasForm()
    return render(request, "financeiro/form_grupo_custas.html", {
        "form": form,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def extrato_custas_grupo(request, grupo_id):
    _exige_acesso_custas(request.user)
    grupo = get_object_or_404(GrupoCustas, pk=grupo_id)
    custas_grupo = list(
        CustaJudicial.objects.filter(grupo=grupo)
        .select_related("cliente", "processo").order_by("-data", "-criado_em")
    )
    lancamentos = [c for c in custas_grupo if c.tipo in ("adiantamento", "paga_pelo_cliente")]
    creditos = [c for c in custas_grupo if c.tipo == "deposito_cliente"]
    saldo = saldo_do_grupo(grupo)
    membros_com_lancamentos = {c.cliente_id for c in custas_grupo if c.cliente_id}

    return render(request, "financeiro/extrato_custas_grupo.html", {
        "grupo": grupo,
        "lancamentos": lancamentos,
        "creditos": creditos,
        "membros": list(grupo.membros.select_related("cliente").order_by("cliente__nome_razao_social")),
        "membros_com_lancamentos": membros_com_lancamentos,
        "pode_apagar": not custas_grupo,
        "form_membro": MembroGrupoCustasForm(),
        "saldo": _formatar_saldo(saldo),
        "saldo_positivo": saldo >= 0,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def form_creditar_custa_grupo(request, grupo_id):
    _exige_acesso_custas(request.user)
    grupo = get_object_or_404(GrupoCustas, pk=grupo_id)
    if request.method == "POST":
        form = CreditarCustaForm(request.POST, request.FILES)
        if form.is_valid():
            dados = form.cleaned_data
            registrar_credito_grupo(
                grupo=grupo, valor=dados["valor"], data=dados["data"],
                descricao=dados["descricao"], anexo=dados.get("anexo"),
                responsavel=request.user,
            )
            return _voltar_ao_grupo(grupo)
    else:
        form = CreditarCustaForm(initial={"data": timezone.localdate()})

    return render(request, "financeiro/form_creditar_custa.html", {
        "form": form,
        "grupo": grupo,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
@require_POST
def adicionar_membro_grupo(request, grupo_id):
    _exige_acesso_custas(request.user)
    grupo = get_object_or_404(GrupoCustas, pk=grupo_id)
    form = MembroGrupoCustasForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Selecione um cliente que ainda não pertença a um grupo.")
        return _voltar_ao_grupo(grupo)
    try:
        adicionar_membro_ao_grupo(grupo, form.cleaned_data["cliente"])
    except ValueError as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, "Membro adicionado ao grupo.")
    return _voltar_ao_grupo(grupo)


@login_required
@require_POST
def remover_membro_grupo(request, grupo_id, cliente_id):
    _exige_acesso_custas(request.user)
    membro = get_object_or_404(MembroGrupoCustas, grupo_id=grupo_id, cliente_id=cliente_id)
    try:
        remover_membro_do_grupo(membro)
    except ValueError as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, "Membro removido do grupo.")
    return _voltar_ao_grupo(membro.grupo)


@login_required
@require_POST
def apagar_grupo(request, grupo_id):
    _exige_acesso_custas(request.user)
    grupo = get_object_or_404(GrupoCustas, pk=grupo_id)
    try:
        excluir_grupo(grupo)
    except ValueError as erro:
        messages.error(request, str(erro))
        return _voltar_ao_grupo(grupo)
    messages.success(request, "Grupo apagado.")
    return redirect("financeiro:custas")


@login_required
def aviso_saldo_custa(request):
    """Saldo atual e saldo após o débito, para o aviso do formulário de
    lançar débito ("Adiantado pelo escritório"). Só informativo."""
    _exige_acesso_custas(request.user)
    cliente_id = request.GET.get("cliente") or ""
    cliente = Cliente.objects.filter(pk=cliente_id, ativo=True).first() if cliente_id.isdigit() else None
    grupo_id = request.GET.get("grupo") or ""
    grupo = GrupoCustas.objects.filter(pk=grupo_id).first() if grupo_id.isdigit() else None
    dono, saldo = saldo_de_custas_do(cliente=cliente, grupo=grupo)
    if dono is None:
        return JsonResponse({"visivel": False})

    try:
        valor = Decimal(request.GET.get("valor") or "0")
    except InvalidOperation:
        valor = Decimal("0")
    if not valor.is_finite() or valor < 0:
        valor = Decimal("0")
    depois = saldo - valor
    return JsonResponse({
        "visivel": True,
        "origem": f"Grupo {dono.nome}" if isinstance(dono, GrupoCustas) else dono.nome_razao_social,
        "atual": _formatar_saldo(saldo),
        "depois": _formatar_saldo(depois),
        "atual_negativo": saldo < 0,
        "depois_negativo": depois < 0,
        "valor_informado": valor > 0,
        "valor": _formatar_moeda(valor),
    })
