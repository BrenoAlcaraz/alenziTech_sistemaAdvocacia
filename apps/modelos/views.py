from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.modelos.forms import ImportarModeloPecaForm, ModeloPecaForm
from apps.modelos.models import ModeloPeca
from apps.modelos.services import ErroImportacaoDocumento, extrair_texto_documento


@login_required
def lista(request):
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


@login_required
def detalhe(request, pk):
    modelo = get_object_or_404(ModeloPeca, pk=pk)
    return render(request, "modelos/detalhe.html", {
        "modelo": modelo,
        "item_ativo": "modelos",
    })


@login_required
def editar(request, pk):
    modelo = get_object_or_404(ModeloPeca, pk=pk)

    if request.method == "POST":
        form = ModeloPecaForm(request.POST, instance=modelo)
        if form.is_valid():
            form.save()
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
def importar(request):
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
