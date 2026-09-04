from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.permissoes import tem_habilitacao, tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    HAB_MODELOS_CRIAR,
    HAB_MODELOS_EDITAR_ALHEIO,
    HAB_MODELOS_EXCLUIR_ALHEIO,
    MODULO_MODELOS,
)
from apps.modelos.forms import ImportarModeloPecaForm, ModeloPecaForm
from apps.modelos.models import ModeloPeca
from apps.modelos.services import ErroImportacaoDocumento, extrair_texto_documento
from apps.notificacoes.models import Notificacao


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    aba_ativa = request.GET.get("aba", "modelos")
    busca = request.GET.get("q", "").strip()

    modelos = ModeloPeca.objects.select_related("criado_por").order_by("-criado_em", "-pk")

    if busca:
        modelos = modelos.filter(
            Q(titulo__icontains=busca)
            | Q(categoria__icontains=busca)
            | Q(area_direito__icontains=busca)
            | Q(conteudo__icontains=busca)
        )

    return render(request, "modelos/lista.html", {
        "modelos": modelos,
        "aba_ativa": aba_ativa,
        "busca": busca,
        "item_ativo": "modelos",
    })


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_MODELOS, HAB_MODELOS_CRIAR):
        raise PermissionDenied

    if request.method == "POST":
        form = ModeloPecaForm(request.POST)
        if form.is_valid():
            modelo = form.save(commit=False)
            modelo.criado_por = request.user
            modelo.save()
            return redirect("modelos:detalhe", pk=modelo.pk)
    else:
        form = ModeloPecaForm()

    return render(request, "modelos/form.html", {
        "form": form,
        "modo": "novo",
        "modelo": None,
        "item_ativo": "modelos",
    })


# `editar`/`excluir` repetem "dono OU habilitação alheia" (2 ocorrências,
# cada uma com sua própria habilitação — PDR-0018). Deliberadamente não
# extraído: só vale abstrair se uma 3ª view precisar do mesmo padrão.
def _eh_dono(user, modelo):
    return modelo.criado_por_id == user.id


def _pode_editar_alheio(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_EDITAR_ALHEIO)


def _pode_excluir_alheio(user):
    return tem_habilitacao(user, MODULO_MODELOS, HAB_MODELOS_EXCLUIR_ALHEIO)


@login_required
def detalhe(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    eh_dono = _eh_dono(request.user, modelo)
    return render(request, "modelos/detalhe.html", {
        "modelo": modelo,
        "item_ativo": "modelos",
        "pode_editar": eh_dono or _pode_editar_alheio(request.user),
        "pode_excluir": eh_dono or _pode_excluir_alheio(request.user),
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    eh_dono = _eh_dono(request.user, modelo)
    if not eh_dono and not _pode_editar_alheio(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = ModeloPecaForm(request.POST, instance=modelo)
        if form.is_valid():
            form.save()
            if not eh_dono and modelo.criado_por_id:
                Notificacao.objects.create(
                    destinatario=modelo.criado_por,
                    mensagem=f'Seu modelo de peça foi editado: "{modelo.titulo}"',
                )
            return redirect("modelos:detalhe", pk=modelo.pk)
    else:
        form = ModeloPecaForm(instance=modelo)

    return render(request, "modelos/form.html", {
        "form": form,
        "modo": "editar",
        "modelo": modelo,
        "item_ativo": "modelos",
    })


@login_required
def excluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied

    modelo = get_object_or_404(ModeloPeca, pk=pk)
    eh_dono = _eh_dono(request.user, modelo)
    if not eh_dono and not _pode_excluir_alheio(request.user):
        raise PermissionDenied

    if request.method == "POST":
        titulo = modelo.titulo
        autor = modelo.criado_por
        modelo.delete()
        if not eh_dono and autor is not None:
            Notificacao.objects.create(
                destinatario=autor,
                mensagem=f'Seu modelo de peça foi excluído: "{titulo}"',
            )
        return redirect("modelos:lista")

    return redirect("modelos:detalhe", pk=modelo.pk)


@login_required
def importar(request):
    if not tem_permissao_modulo(request.user, MODULO_MODELOS):
        raise PermissionDenied
    if not tem_habilitacao(request.user, MODULO_MODELOS, HAB_MODELOS_CRIAR):
        raise PermissionDenied

    if request.method == "POST":
        form = ImportarModeloPecaForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data["arquivo"]
            try:
                conteudo = extrair_texto_documento(arquivo)
            except ErroImportacaoDocumento as erro:
                form.add_error("arquivo", str(erro))
            else:
                titulo = form.cleaned_data["titulo"].strip()
                if not titulo:
                    titulo = Path(arquivo.name).stem.strip()
                titulo = titulo[:255] or "Modelo importado"

                modelo = ModeloPeca.objects.create(
                    titulo=titulo,
                    categoria=form.cleaned_data["categoria"],
                    area_direito=form.cleaned_data["area_direito"],
                    conteudo=conteudo,
                    criado_por=request.user,
                )
                return redirect("modelos:detalhe", pk=modelo.pk)
    else:
        form = ImportarModeloPecaForm()

    return render(request, "modelos/importar.html", {
        "form": form,
        "item_ativo": "modelos",
    })
