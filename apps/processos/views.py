from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Processo
from .forms import ProcessoForm, ParteProcessoForm, MovimentacaoProcessualForm


@login_required
def lista(request):
    processos = Processo.objects.select_related("cliente", "responsavel").all()
    return render(request, "processos/lista.html", {
        "processos": processos,
        "item_ativo": "processos",
        "novo_url": reverse("processos:novo"),
    })


@login_required
def detalhe(request, pk):
    processo = get_object_or_404(
        Processo.objects.select_related("cliente", "responsavel")
                        .prefetch_related("partes", "movimentacoes"),
        pk=pk
    )
    return render(request, "processos/detalhe.html", {
        "processo": processo,
        "movimentacoes": processo.movimentacoes.order_by("-data"),
        "partes": processo.partes.all(),
        "form_parte": ParteProcessoForm(),
        "form_movimentacao": MovimentacaoProcessualForm(),
        "aba_ativa": request.GET.get("aba", "andamentos"),
        "item_ativo": "processos",
    })


@login_required
def novo(request):
    if request.method == "POST":
        form = ProcessoForm(request.POST)
        if form.is_valid():
            processo = form.save(commit=False)
            processo.responsavel = request.user
            processo.status = "ativo"
            processo.save()
            return redirect("processos:detalhe", pk=processo.pk)
    else:
        form = ProcessoForm()
    return render(request, "processos/form.html", {
        "modo": "novo",
        "form": form,
        "item_ativo": "processos",
    })


@login_required
def editar(request, pk):
    processo = get_object_or_404(Processo, pk=pk)
    if request.method == "POST":
        form = ProcessoForm(request.POST, instance=processo)
        if form.is_valid():
            form.save()
            return redirect("processos:detalhe", pk=processo.pk)
    else:
        form = ProcessoForm(instance=processo)
    return render(request, "processos/form.html", {
        "modo": "editar",
        "form": form,
        "item_ativo": "processos",
    })


@login_required
def adicionar_movimentacao(request, pk):
    processo = get_object_or_404(Processo, pk=pk)
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
    processo = get_object_or_404(Processo, pk=pk)
    if request.method == "POST":
        form = ParteProcessoForm(request.POST)
        if form.is_valid():
            parte = form.save(commit=False)
            parte.processo = processo
            parte.save()
    return redirect(f"{reverse('processos:detalhe', args=[pk])}?aba=partes")
