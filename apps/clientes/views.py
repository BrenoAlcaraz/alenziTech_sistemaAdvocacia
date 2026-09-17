from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.views.decorators.http import require_POST
from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import tem_permissao_modulo, tem_habilitacao, nivel_acesso_modulo
from apps.accounts.permissoes_constants import (
    MODULO_CLIENTES,
    MODULO_MODELOS,
    HAB_CLIENTES_CRIAR,
    HAB_CLIENTES_EDITAR,
    HAB_CLIENTES_DESATIVAR,
    HAB_CLIENTES_REATIVAR,
    HAB_CLIENTES_EXCLUIR,
    HAB_CLIENTES_DOCUMENTO_ADICIONAR,
    HAB_CLIENTES_DOCUMENTO_EXCLUIR,
    HAB_MODELOS_CRIAR,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.modelos.models import CategoriaModeloPeca, ModeloPeca
from apps.modelos.services import montar_conteudo_procuracao, titulo_peca_procuracao
from .models import Cliente, Documento
from .forms import ClienteForm, ClienteResponsavelForm, DocumentoForm
from .services import clientes_relacionados

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


def _pode_adicionar_documento(user):
    return tem_habilitacao(user, MODULO_CLIENTES, HAB_CLIENTES_DOCUMENTO_ADICIONAR)


def _pode_excluir_documento(user):
    return tem_habilitacao(user, MODULO_CLIENTES, HAB_CLIENTES_DOCUMENTO_EXCLUIR)


def _pode_gerar_procuracao(user):
    return tem_permissao_modulo(user, MODULO_MODELOS) and tem_habilitacao(
        user, MODULO_MODELOS, HAB_MODELOS_CRIAR
    )


def _usuarios_ativos():
    return User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    clientes = _clientes_no_escopo(request, escopo, ativo=True)
    busca = (request.GET.get("busca") or "").strip()
    if busca:
        clientes = clientes.filter(
            Q(nome_razao_social__icontains=busca) | Q(cpf_cnpj__icontains=busca)
        )
    return render(request, "clientes/lista.html", {
        "clientes": clientes,
        "item_ativo": "clientes",
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "filtro_busca": busca,
    })


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    cliente = get_object_or_404(_clientes_no_escopo(request, escopo, ativo=True), pk=pk)
    processos = cliente.processos.all()
    tarefas_relacionadas_total = cliente.tarefas.count()
    tarefas_relacionadas = list(
        cliente.tarefas.select_related("responsavel")
        .exclude(status="cancelada")
        .order_by("prazo")[:5]
    )
    pode_modificar = (
        usuario_admin_escritorio(request.user)
        or cliente.responsavel_id == request.user.pk
    )
    documentos = list(cliente.documentos.select_related("autor"))
    return render(request, "clientes/detalhe.html", {
        "cliente": cliente,
        "processos": processos,
        "clientes_relacionados": clientes_relacionados(cliente),
        "tarefas_relacionadas": tarefas_relacionadas,
        "tarefas_relacionadas_total": tarefas_relacionadas_total,
        "pode_excluir_cliente": pode_modificar and tem_habilitacao(
            request.user, MODULO_CLIENTES, HAB_CLIENTES_EXCLUIR
        ),
        "documentos": documentos,
        "documentos_total": len(documentos),
        "form_documento": DocumentoForm(),
        "pode_adicionar_documento": pode_modificar and _pode_adicionar_documento(request.user),
        "pode_excluir_documento": pode_modificar and _pode_excluir_documento(request.user),
        "pode_gerar_procuracao": _pode_gerar_procuracao(request.user),
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
    if not tem_habilitacao(request.user, MODULO_CLIENTES, HAB_CLIENTES_DESATIVAR):
        raise PermissionDenied
    _resolver_escopo(request)
    if request.method == "POST":
        cliente = get_object_or_404(_clientes_mutaveis(request, ativo=True), pk=pk)
        cliente.ativo = False
        cliente.save()
        return redirect("clientes:lista")
    return redirect("clientes:detalhe", pk=pk)


@login_required
@require_POST
def excluir(request, pk):
    """Exclusão definitiva — distinta de Desativar. Remove o Cliente;
    lançamentos, custas, honorários, tarefas e compromissos vinculados
    permanecem no sistema, só perdem a referência (`on_delete=SET_NULL`,
    já é o padrão hoje nesses modelos)."""
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_CLIENTES, HAB_CLIENTES_EXCLUIR):
        raise PermissionDenied
    _resolver_escopo(request)
    qs = Cliente.objects.all()
    if not usuario_admin_escritorio(request.user):
        qs = qs.filter(responsavel=request.user)
    cliente = get_object_or_404(qs, pk=pk)
    cliente.delete()
    return redirect("clientes:lista")


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
        "pode_excluir_cliente": tem_habilitacao(request.user, MODULO_CLIENTES, HAB_CLIENTES_EXCLUIR),
    })


@login_required
def reativar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_CLIENTES, HAB_CLIENTES_REATIVAR):
        raise PermissionDenied
    _resolver_escopo(request)
    if request.method == "POST":
        cliente = get_object_or_404(_clientes_mutaveis(request, ativo=False), pk=pk)
        cliente.ativo = True
        cliente.save()
        return redirect("clientes:inativos")
    return redirect("clientes:inativos")


@login_required
@require_POST
def adicionar_documento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    if not _pode_adicionar_documento(request.user):
        raise PermissionDenied
    _resolver_escopo(request)
    cliente = get_object_or_404(_clientes_mutaveis(request, ativo=True), pk=pk)
    form = DocumentoForm(request.POST, request.FILES)
    if form.is_valid():
        documento = form.save(commit=False)
        documento.cliente = cliente
        documento.autor = request.user
        documento.save()
    return redirect(f"{reverse('clientes:detalhe', args=[pk])}?aba=documentos")


@login_required
@require_POST
def excluir_documento(request, pk, documento_pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    if not _pode_excluir_documento(request.user):
        raise PermissionDenied
    _resolver_escopo(request)
    cliente = get_object_or_404(_clientes_mutaveis(request, ativo=True), pk=pk)
    documento = get_object_or_404(cliente.documentos, pk=documento_pk)
    documento.delete()
    return redirect(f"{reverse('clientes:detalhe', args=[pk])}?aba=documentos")


@login_required
def gerar_procuracao(request, pk):
    """Gera uma nova peça de Procuração no acervo de Modelos, a partir do
    modelo de Procuração cadastrado pelo escritório + dados do cliente
    (nome/CPF-CNPJ/endereço, e representante se PJ) — mesmo padrão de
    Peças repetitivas Fase 1 (gerar e depois ajustar manualmente, sem IA).

    Autorização: `modelos_criar` (é a mutação que efetivamente acontece,
    criar um ModeloPeca) combinada com poder ver o cliente (escopo de
    leitura de Clientes já aplicado) — não depende de ser responsável
    pelo cliente nem de habilitação de documento de Clientes.
    """
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    if not _pode_gerar_procuracao(request.user):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    cliente = get_object_or_404(_clientes_no_escopo(request, escopo, ativo=True), pk=pk)

    categoria_procuracao = CategoriaModeloPeca.objects.filter(nome="Procuração").first()
    modelos_procuracao = (
        categoria_procuracao.modelos.order_by("-criado_em")
        if categoria_procuracao else ModeloPeca.objects.none()
    )

    if request.method == "POST" and modelos_procuracao.exists():
        modelo_base = get_object_or_404(modelos_procuracao, pk=request.POST.get("modelo_base"))
        peca = ModeloPeca.objects.create(
            titulo=titulo_peca_procuracao(modelo_base.titulo, cliente),
            categoria=modelo_base.categoria,
            area_direito=modelo_base.area_direito,
            conteudo=montar_conteudo_procuracao(modelo_base.conteudo, cliente),
            criado_por=request.user,
        )
        return redirect("modelos:detalhe", pk=peca.pk)

    return render(request, "clientes/gerar_procuracao.html", {
        "cliente": cliente,
        "modelos_procuracao": modelos_procuracao,
        "item_ativo": "clientes",
    })


@login_required
def baixar_documento(request, documento_pk):
    if not tem_permissao_modulo(request.user, MODULO_CLIENTES):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    documento = get_object_or_404(
        Documento.objects.filter(cliente__in=_clientes_no_escopo(request, escopo, ativo=True)),
        pk=documento_pk,
    )
    if not documento.arquivo:
        raise Http404
    return FileResponse(documento.arquivo.open("rb"), filename=documento.nome_do_documento())
