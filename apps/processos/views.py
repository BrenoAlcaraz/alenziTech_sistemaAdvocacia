from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.urls import reverse
from apps.accounts.escopo import equipe_padrao_para_usuario
from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import nivel_acesso_modulo, tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from .models import ParteProcesso, Processo, RepresentanteParte
from .forms import (
    ClassificacaoParteForm,
    MovimentacaoProcessualForm,
    ParteProcessoForm,
    ProcessoForm,
    ProcessoResponsavelForm,
    RepresentanteParteForm,
)
from .services import (
    cliente_do_processo_corresponde_documento,
    obter_ou_criar_representante_externo,
    responsaveis_elegiveis,
    vincular_responsavel_como_advogado,
)


_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}


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
            "partes__cliente",
            "partes__representantes__usuario",
            "autoridades",
            "movimentacoes",
        ),
        pk=pk,
    )
    pode_modificar = (
        usuario_admin_escritorio(request.user)
        or processo.responsavel_id == request.user.pk
    )
    partes = list(processo.partes.all())
    for parte in partes:
        if pode_modificar and not parte.registro_legado:
            parte.form_classificacao = ClassificacaoParteForm(initial={
                "tipo": parte.qualificacao,
                "atuacao_ministerio_publico": parte.atuacao_ministerio_publico,
            })
    autoridades = list(processo.autoridades.all())
    return render(request, "processos/detalhe.html", {
        "processo": processo,
        "movimentacoes": processo.movimentacoes.order_by("-data"),
        "partes": partes,
        "partes_polo_ativo": [p for p in partes if p.grupo_visual == "polo_ativo"],
        "partes_polo_passivo": [p for p in partes if p.grupo_visual == "polo_passivo"],
        "partes_outros": [p for p in partes if p.grupo_visual == "outros"],
        "autoridades": autoridades,
        "participantes_total": len(partes) + len(autoridades),
        "form_parte": ParteProcessoForm(initial={"vara_orgao": processo.vara_juizo}),
        "form_advogado": RepresentanteParteForm(),
        "form_movimentacao": MovimentacaoProcessualForm(),
        "aba_ativa": request.GET.get("aba", "andamentos"),
        "item_ativo": "processos",
        "pode_modificar": pode_modificar,
    })


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    is_admin = usuario_admin_escritorio(request.user)
    FormClass = ProcessoResponsavelForm if is_admin else ProcessoForm
    form_kwargs = (
        {"responsaveis_queryset": responsaveis_elegiveis()} if is_admin else {}
    )
    if request.method == "POST":
        form = FormClass(request.POST, **form_kwargs)
        if form.is_valid():
            processo = form.save(commit=False)
            if not is_admin:
                processo.responsavel = request.user
            processo.status = "ativo"
            if not processo.equipe:
                processo.equipe = equipe_padrao_para_usuario(request.user)
            processo.save()
            return redirect("processos:detalhe", pk=processo.pk)
    else:
        initial = {"responsavel": request.user.pk} if is_admin else {}
        form = FormClass(initial=initial, **form_kwargs)
    return render(request, "processos/form.html", {
        "modo": "novo",
        "form": form,
        "item_ativo": "processos",
        "is_admin": is_admin,
        "responsavel_exibido": request.user,
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    is_admin = usuario_admin_escritorio(request.user)
    FormClass = ProcessoResponsavelForm if is_admin else ProcessoForm
    form_kwargs = (
        {"responsaveis_queryset": responsaveis_elegiveis()} if is_admin else {}
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
        "is_admin": is_admin,
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
        form = ParteProcessoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                cliente = cliente_do_processo_corresponde_documento(
                    processo,
                    form.cleaned_data.get("cpf_cnpj"),
                )
                participante = form.criar_para_processo(
                    processo,
                    cliente=cliente,
                    usuario=request.user,
                )
                if isinstance(participante, ParteProcesso) and cliente is not None:
                    vincular_responsavel_como_advogado(participante)
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")


@login_required
def adicionar_advogado(request, pk, parte_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    parte = get_object_or_404(processo.partes, pk=parte_pk)
    if request.method == "POST":
        form = RepresentanteParteForm(request.POST)
        if form.is_valid():
            representante = form.save(commit=False)
            representante.parte = parte
            if representante.tipo == "interno":
                RepresentanteParte.objects.get_or_create(
                    parte=parte,
                    tipo="interno",
                    usuario=representante.usuario,
                )
            else:
                obter_ou_criar_representante_externo(parte, representante)
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")


@login_required
def alterar_classificacao_parte(request, pk, parte_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    parte = get_object_or_404(
        processo.partes.filter(registro_legado=False),
        pk=parte_pk,
    )
    if request.method == "POST":
        form = ClassificacaoParteForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                form.salvar(parte, usuario=request.user)
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")


@login_required
def remover_advogado(request, pk, parte_pk, representante_pk):
    if not tem_permissao_modulo(request.user, MODULO_PROCESSOS):
        raise PermissionDenied
    _resolver_escopo(request)
    processo = get_object_or_404(_processos_mutaveis(request), pk=pk)
    parte = get_object_or_404(processo.partes, pk=parte_pk)
    representante = get_object_or_404(
        parte.representantes,
        pk=representante_pk,
    )
    if request.method == "POST":
        representante.delete()
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")
