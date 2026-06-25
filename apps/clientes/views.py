from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Cliente
from .forms import ClienteForm
# Dados temporários apenas para layout — substituir futuramente por queries reais
CLIENTES_MOCK = [
    {"id": 1, "tipo": "PF", "nome_razao_social": "Roberto Andrade", "cpf_cnpj": "123.456.789-00", "email": "roberto.andrade@email.com", "telefone": "(21) 99988-7766", "num_processos": 1},
    {"id": 2, "tipo": "PJ", "nome_razao_social": "Construtora Horizonte Ltda.", "cpf_cnpj": "12.345.678/0001-90", "email": "", "telefone": "", "num_processos": 1},
    {"id": 3, "tipo": "PJ", "nome_razao_social": "Unimed Regional", "cpf_cnpj": "98.765.432/0001-10", "email": "", "telefone": "", "num_processos": 1},
    {"id": 4, "tipo": "PJ", "nome_razao_social": "TechCorp Soluções S.A.", "cpf_cnpj": "11.222.333/0001-44", "email": "", "telefone": "", "num_processos": 1},
    {"id": 5, "tipo": "PJ", "nome_razao_social": "Comércio Silva ME", "cpf_cnpj": "22.333.444/0001-55", "email": "", "telefone": "", "num_processos": 0},
]

PROCESSOS_MOCK_CLIENTE = [
    {"id": 1, "titulo": "Inventário Família Andrade", "numero": "0809999-11.2024.8.19.0001", "area_direito": "SUCESSÕES"},
]


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
            form.save()
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
