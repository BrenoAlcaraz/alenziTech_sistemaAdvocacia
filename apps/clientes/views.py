from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import tem_permissao_modulo, tem_habilitacao, nivel_acesso_modulo
from apps.accounts.permissoes_constants import (
    MODULO_CLIENTES,
    HAB_CLIENTES_CRIAR,
    HAB_CLIENTES_EDITAR,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from .models import Cliente
from .forms import ClienteForm, ClienteResponsavelForm

User = get_user_model()

_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}


def _resolver_escopo(request):
    """
    Resolve o escopo efetivo de LEITURA (somente_seus/todos) desta
    requisição — usado por lista/detalhe/inativos, nunca por mutação.

    Distinção obrigatória: parâmetro AUSENTE (`escopo` não está em
    `request.GET`) usa o nível máximo como padrão; parâmetro PRESENTE
    com valor inválido — incluindo string vazia (`?escopo=`) e
    "da_equipe" — é sempre negado (403), assim como um valor acima do
    máximo autorizado. `request.GET.get("escopo")` retorna `None` apenas
    quando a chave está ausente; retorna `""` quando está presente e
    vazia — essas duas situações nunca podem ser tratadas como
    equivalentes.
    Retorna (escopo_efetivo, nivel_maximo).
    """
    nivel_maximo = nivel_acesso_modulo(request.user, MODULO_CLIENTES)
    if nivel_maximo not in _ESCOPOS_VALIDOS:
        nivel_maximo = NIVEL_SOMENTE_SEUS

    solicitado = request.GET.get("escopo")
    if solicitado is None:
        return nivel_maximo, nivel_maximo

    if solicitado not in _ESCOPOS_VALIDOS:
        raise PermissionDenied
    if solicitado == NIVEL_TODOS and nivel_maximo != NIVEL_TODOS:
        raise PermissionDenied
    return solicitado, nivel_maximo


def _clientes_no_escopo(request, escopo, *, ativo):
    """
    QuerySet de LEITURA (lista/detalhe/inativos), restrito pelo escopo de
    visualização efetivo. "Todos" aqui é alcance de visualização, não
    autorização de mutação — ver `_clientes_mutaveis`.
    """
    qs = Cliente.objects.filter(ativo=ativo)
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(responsavel=request.user)
    return qs


def _clientes_mutaveis(request, *, ativo):
    """
    QuerySet usado para mutação (editar/desativar/reativar).

    "Todos" é escopo de visualização, não autorização de mutação sobre
    qualquer cliente: um usuário não-admin, mesmo com nível máximo
    `todos`, só pode mutar clientes de sua própria responsabilidade.
    Apenas o Administrador do escritório alcança qualquer cliente do
    tenant para mutação.
    """
    qs = Cliente.objects.filter(ativo=ativo)
    if not usuario_admin_escritorio(request.user):
        qs = qs.filter(responsavel=request.user)
    return qs


def _usuarios_ativos():
    return User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    clientes = _clientes_no_escopo(request, escopo, ativo=True)
    return render(request, "clientes/lista.html", {
        "clientes": clientes,
        "item_ativo": "clientes",
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
    })


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    cliente = get_object_or_404(_clientes_no_escopo(request, escopo, ativo=True), pk=pk)
    processos = cliente.processos.all()
    return render(request, "clientes/detalhe.html", {
        "cliente": cliente,
        "processos": processos,
        "aba_ativa": request.GET.get("aba", "processos"),
        "item_ativo": "clientes",
    })


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_CLIENTES, HAB_CLIENTES_CRIAR):
        raise PermissionDenied

    is_admin = usuario_admin_escritorio(request.user)
    FormClass = ClienteResponsavelForm if is_admin else ClienteForm

    if request.method == "POST":
        form_kwargs = {"usuarios_queryset": _usuarios_ativos()} if is_admin else {}
        form = FormClass(request.POST, **form_kwargs)
        if form.is_valid():
            cliente = form.save(commit=False)
            if not is_admin:
                cliente.responsavel = request.user
            cliente.save()
            return redirect("clientes:lista")
    else:
        form_kwargs = {"usuarios_queryset": _usuarios_ativos()} if is_admin else {}
        initial = {"responsavel": request.user.pk} if is_admin else {}
        form = FormClass(initial=initial, **form_kwargs)

    return render(request, "clientes/form.html", {
        "modo": "novo",
        "form": form,
        "item_ativo": "clientes",
        "is_admin": is_admin,
        "responsavel_exibido": request.user,
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_CLIENTES, HAB_CLIENTES_EDITAR):
        raise PermissionDenied

    # Mutação: "todos" é escopo de visualização, não autorização de
    # mutação — validar o parâmetro de escopo (403 em valor inválido),
    # mas carregar o objeto pelo QuerySet de mutação, restrito a
    # Administrador ou ao próprio responsável.
    _resolver_escopo(request)
    cliente = get_object_or_404(_clientes_mutaveis(request, ativo=True), pk=pk)

    is_admin = usuario_admin_escritorio(request.user)
    FormClass = ClienteResponsavelForm if is_admin else ClienteForm

    if request.method == "POST":
        form_kwargs = {"usuarios_queryset": _usuarios_ativos()} if is_admin else {}
        form = FormClass(request.POST, instance=cliente, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect("clientes:detalhe", pk=pk)
    else:
        form_kwargs = {"usuarios_queryset": _usuarios_ativos()} if is_admin else {}
        form = FormClass(instance=cliente, **form_kwargs)

    return render(request, "clientes/form.html", {
        "modo": "editar",
        "form": form,
        "item_ativo": "clientes",
        "is_admin": is_admin,
        # Não-admin sempre vê o responsável real do cliente (nunca o
        # próprio editor) — o campo é somente leitura para essa conta.
        "responsavel_exibido": cliente.responsavel,
    })


@login_required
def desativar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    _resolver_escopo(request)
    if request.method == "POST":
        cliente = get_object_or_404(_clientes_mutaveis(request, ativo=True), pk=pk)
        cliente.ativo = False
        cliente.save()
        return redirect("clientes:lista")
    return redirect("clientes:detalhe", pk=pk)


@login_required
def inativos(request):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    clientes = _clientes_no_escopo(request, escopo, ativo=False)
    return render(request, "clientes/inativos.html", {
        "clientes": clientes,
        "item_ativo": "clientes",
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
    })


@login_required
def reativar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    _resolver_escopo(request)
    if request.method == "POST":
        cliente = get_object_or_404(_clientes_mutaveis(request, ativo=False), pk=pk)
        cliente.ativo = True
        cliente.save()
        return redirect("clientes:inativos")
    return redirect("clientes:inativos")
