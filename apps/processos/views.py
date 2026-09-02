from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.urls import reverse
from django.views.decorators.http import require_POST
from apps.accounts.escopo import equipe_padrao_para_usuario
from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import nivel_acesso_modulo, tem_habilitacao, tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
    HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL,
    MODULO_GERIR,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from .models import Processo
from .forms import (
    AdicionarApensoForm,
    AdicionarIntegranteForm,
    MovimentacaoProcessualForm,
    ParteProcessoForm,
    ProcessoForm,
    ProcessoResponsavelForm,
)
from .services import (
    ids_processos_apensos_do,
    responsaveis_elegiveis,
    vincular_processos_apensos,
    vinculos_apensos_do,
)


User = get_user_model()

_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}


def _pode_atribuir_responsavel(user):
    # tem_habilitacao já concede automaticamente ao Administrador do
    # escritório (bypass interno do kernel), independentemente desta
    # habilitação — ver apps/accounts/permissoes.py.
    return tem_habilitacao(user, MODULO_PROCESSOS, HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL)


def _pode_gerenciar_integrantes(user):
    return tem_habilitacao(user, MODULO_GERIR, HAB_GERIR_HABILITAR_USUARIO_PROCESSOS)


def _resolver_escopo(request):
    nivel_maximo = nivel_acesso_modulo(request.user, MODULO_PROCESSOS)
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


def _processos_no_escopo(request, escopo):
    qs = Processo.objects.select_related("cliente", "responsavel")
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(responsavel=request.user)
    return qs


def _processos_mutaveis(request):
    qs = Processo.objects.all()
    if not usuario_admin_escritorio(request.user):
        qs = qs.filter(responsavel=request.user)
    return qs


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    processos = _processos_no_escopo(request, escopo).exclude(status="arquivado")
    return render(request, "processos/lista.html", {
        "processos": processos,
        "item_ativo": "processos",
        "novo_url": reverse("processos:novo"),
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
    })


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    escopo, _ = _resolver_escopo(request)
    processo = get_object_or_404(
        _processos_no_escopo(request, escopo).prefetch_related(
            "partes",
            "movimentacoes",
            "integrantes_habilitados",
        ),
        pk=pk,
    )
    pode_modificar = (
        usuario_admin_escritorio(request.user)
        or processo.responsavel_id == request.user.pk
    )
    pode_gerenciar_integrantes = _pode_gerenciar_integrantes(request.user)
    partes = list(processo.partes.all())
    for parte in partes:
        if pode_modificar:
            parte.form_editar = ParteProcessoForm(instance=parte, processo=processo)
    vinculos_apensos = list(
        vinculos_apensos_do(
            processo,
            processos_visiveis=_processos_no_escopo(request, escopo),
        ).select_related(
            "processo_menor__cliente",
            "processo_menor__responsavel",
            "processo_maior__cliente",
            "processo_maior__responsavel",
        )
    )
    processos_apensos = [
        vinculo.outro_processo(processo) for vinculo in vinculos_apensos
    ]
    ids_mutaveis = set(
        _processos_mutaveis(request)
        .filter(pk__in=[apenso.pk for apenso in processos_apensos])
        .values_list("pk", flat=True)
    )
    apensos = [
        {
            "vinculo": vinculo,
            "processo": apenso,
            "pode_remover": pode_modificar and apenso.pk in ids_mutaveis,
        }
        for vinculo, apenso in zip(vinculos_apensos, processos_apensos)
    ]
    candidatos_apenso = Processo.objects.none()
    if pode_modificar:
        candidatos_apenso = (
            _processos_mutaveis(request)
            .exclude(pk=processo.pk)
            .exclude(pk__in=ids_processos_apensos_do(processo))
            .order_by("numero", "titulo", "pk")
        )
    form_apenso = AdicionarApensoForm(
        processo_origem=processo,
        processos_queryset=candidatos_apenso,
    )
    integrantes = list(processo.integrantes_habilitados.all())
    candidatos_integrante = User.objects.none()
    if pode_gerenciar_integrantes:
        candidatos_integrante = responsaveis_elegiveis().exclude(
            pk__in=[integrante.pk for integrante in integrantes]
        )
    form_integrante = AdicionarIntegranteForm(usuarios_queryset=candidatos_integrante)
    return render(request, "processos/detalhe.html", {
        "processo": processo,
        "movimentacoes": processo.movimentacoes.order_by("-data"),
        "partes": partes,
        "partes_polo_ativo": [p for p in partes if p.grupo_visual == "polo_ativo"],
        "partes_polo_passivo": [p for p in partes if p.grupo_visual == "polo_passivo"],
        "partes_outros": [p for p in partes if p.grupo_visual == "outros"],
        "participantes_total": len(partes),
        "apensos": apensos,
        "apensos_total": len(apensos),
        "form_apenso": form_apenso,
        "tem_candidatos_apenso": candidatos_apenso.exists(),
        "integrantes": integrantes,
        "integrantes_total": len(integrantes),
        "form_integrante": form_integrante,
        "tem_candidatos_integrante": candidatos_integrante.exists(),
        "pode_gerenciar_integrantes": pode_gerenciar_integrantes,
        "form_parte": ParteProcessoForm(processo=processo),
        "form_movimentacao": MovimentacaoProcessualForm(),
        "aba_ativa": request.GET.get("aba", "andamentos"),
        "item_ativo": "processos",
        "pode_modificar": pode_modificar,
    })


@login_required
@require_POST
def adicionar_apenso(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    with transaction.atomic():
        mutaveis = _processos_mutaveis(request).select_for_update()
        processo = get_object_or_404(mutaveis, pk=pk)
        formulario = AdicionarApensoForm(
            request.POST,
            processo_origem=processo,
            processos_queryset=mutaveis.exclude(pk=processo.pk),
        )
        if not formulario.is_valid():
            raise Http404
        processo_apenso = get_object_or_404(
            mutaveis,
            pk=formulario.cleaned_data["processo_apenso"].pk,
        )
        vincular_processos_apensos(processo, processo_apenso)
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=apensos")


@login_required
@require_POST
def remover_apenso(request, pk, vinculo_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    with transaction.atomic():
        mutaveis = _processos_mutaveis(request).select_for_update()
        processo = get_object_or_404(mutaveis, pk=pk)
        vinculo = get_object_or_404(
            vinculos_apensos_do(processo).select_for_update(),
            pk=vinculo_pk,
        )
        processo_apenso = vinculo.outro_processo(processo)
        get_object_or_404(mutaveis, pk=processo_apenso.pk)
        vinculo.delete()
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=apensos")


@login_required
@require_POST
def adicionar_integrante(request, pk):
    if not _pode_gerenciar_integrantes(request.user):
        raise PermissionDenied
    processo = get_object_or_404(Processo, pk=pk)
    formulario = AdicionarIntegranteForm(
        request.POST,
        usuarios_queryset=responsaveis_elegiveis().exclude(
            pk__in=processo.integrantes_habilitados.values("pk")
        ),
    )
    if not formulario.is_valid():
        raise Http404
    processo.integrantes_habilitados.add(formulario.cleaned_data["usuario"])
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=integrantes")


@login_required
@require_POST
def remover_integrante(request, pk, usuario_pk):
    if not _pode_gerenciar_integrantes(request.user):
        raise PermissionDenied
    processo = get_object_or_404(Processo, pk=pk)
    usuario = get_object_or_404(processo.integrantes_habilitados, pk=usuario_pk)
    processo.integrantes_habilitados.remove(usuario)
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=integrantes")


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    pode_atribuir_responsavel = _pode_atribuir_responsavel(request.user)
    FormClass = ProcessoResponsavelForm if pode_atribuir_responsavel else ProcessoForm
    form_kwargs = (
        {"responsaveis_queryset": responsaveis_elegiveis()}
        if pode_atribuir_responsavel else {}
    )
    if request.method == "POST":
        form = FormClass(request.POST, **form_kwargs)
        if form.is_valid():
            processo = form.save(commit=False)
            if not pode_atribuir_responsavel:
                processo.responsavel = request.user
            processo.status = "ativo"
            if not processo.equipe:
                processo.equipe = equipe_padrao_para_usuario(request.user)
            processo.save()
            return redirect("processos:detalhe", pk=processo.pk)
    else:
        initial = {"responsavel": request.user.pk} if pode_atribuir_responsavel else {}
        form = FormClass(initial=initial, **form_kwargs)
    return render(request, "processos/form.html", {
        "modo": "novo",
        "form": form,
        "item_ativo": "processos",
        "pode_atribuir_responsavel": pode_atribuir_responsavel,
        "responsavel_exibido": request.user,
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    pode_atribuir_responsavel = _pode_atribuir_responsavel(request.user)
    FormClass = ProcessoResponsavelForm if pode_atribuir_responsavel else ProcessoForm
    form_kwargs = (
        {"responsaveis_queryset": responsaveis_elegiveis()}
        if pode_atribuir_responsavel else {}
    )
    if request.method == "POST":
        form = FormClass(request.POST, instance=processo, **form_kwargs)
        if form.is_valid():
            form.save()
            return redirect("processos:detalhe", pk=processo.pk)
    else:
        form = FormClass(instance=processo, **form_kwargs)
    return render(request, "processos/form.html", {
        "modo": "editar",
        "form": form,
        "item_ativo": "processos",
        "pode_atribuir_responsavel": pode_atribuir_responsavel,
        "responsavel_exibido": processo.responsavel,
    })


@login_required
def arquivados(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    processos = _processos_no_escopo(request, escopo).filter(status="arquivado")
    return render(request, "processos/arquivados.html", {
        "processos": processos,
        "item_ativo": "processos",
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "usuario_e_admin": usuario_admin_escritorio(request.user),
    })


@login_required
def arquivar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        processo.status = "arquivado"
        processo.save()
    return redirect("processos:detalhe", pk=pk)


@login_required
def reabrir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        processo.status = "ativo"
        processo.save()
    return redirect("processos:detalhe", pk=pk)


@login_required
def adicionar_movimentacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = MovimentacaoProcessualForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.processo = processo
            movimentacao.autor = request.user
            movimentacao.save()
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=andamentos")


@login_required
def adicionar_parte(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = ParteProcessoForm(request.POST, processo=processo)
        if form.is_valid():
            parte = form.save(commit=False)
            parte.processo = processo
            parte.save()
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")


@login_required
def editar_parte(request, pk, parte_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    parte = get_object_or_404(processo.partes, pk=parte_pk)
    if request.method == "POST":
        form = ParteProcessoForm(request.POST, instance=parte, processo=processo)
        if form.is_valid():
            form.save()
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")
