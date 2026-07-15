from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from apps.accounts.escopo import departamento_padrao_para_usuario
from .models import Cliente
from .forms import ClienteForm


@login_required
def lista(request):
    clientes = Cliente.objects.filter(ativo=True)
    return render(request, "clientes/lista.html", {"clientes": clientes, "item_ativo": "clientes"})


@login_required
def detalhe(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, ativo=True)
    processos = cliente.processos.all()
    return render(request, "clientes/detalhe.html", {
        "cliente": cliente,
        "processos": processos,
        "aba_ativa": request.GET.get("aba", "processos"),
        "item_ativo": "clientes",
    })


@login_required
def novo(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            if not cliente.responsavel:
                cliente.responsavel = request.user
            if not cliente.departamento:
                cliente.departamento = departamento_padrao_para_usuario(request.user)
            cliente.save()
            return redirect("clientes:lista")
    else:
        form = ClienteForm()
    return render(request, "clientes/form.html", {"modo": "novo", "form": form, "item_ativo": "clientes"})


@login_required
def editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, ativo=True)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect("clientes:detalhe", pk=pk)
    else:
        form = ClienteForm(instance=cliente)
    return render(request, "clientes/form.html", {
        "modo": "editar",
        "form": form,
        "item_ativo": "clientes",
    })


@login_required
def desativar(request, pk):
    if request.method == "POST":
        cliente = get_object_or_404(Cliente, pk=pk, ativo=True)
        cliente.ativo = False
        cliente.save()
        return redirect("clientes:lista")
    return redirect("clientes:detalhe", pk=pk)


@login_required
def inativos(request):
    clientes = Cliente.objects.filter(ativo=False)
    return render(request, "clientes/inativos.html", {"clientes": clientes, "item_ativo": "clientes"})


@login_required
def reativar(request, pk):
    if request.method == "POST":
        cliente = get_object_or_404(Cliente, pk=pk, ativo=False)
        cliente.ativo = True
        cliente.save()
        return redirect("clientes:inativos")
    return redirect("clientes:inativos")
