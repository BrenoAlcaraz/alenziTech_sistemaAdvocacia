from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Processo
from .forms import ProcessoForm

# Dados temporários apenas para layout — substituir futuramente por queries reais
PROCESSOS_MOCK = [
    {
        "id": 1,
        "titulo": "Construtora Horizonte vs. Município",
        "numero": "0801234-55.2024.8.19.0001",
        "area_direito": "CÍVEL",
        "instancia": "1ª Instância",
        "vara_juizo": "11ª Vara Cível – Comarca da Capital",
        "valor_causa": "R$ 450.000,00",
        "cliente": "Construtora Horizonte Ltda.",
        "prazo_label": "em 2 dias",
        "prazo_urgente": True,
        "status": "ativo",
    },
    {
        "id": 2,
        "titulo": "Unimed – Contencioso de Massa",
        "numero": "0805678-99.2024.8.19.0001",
        "area_direito": "CONSUMIDOR",
        "instancia": "1ª Instância",
        "vara_juizo": "3ª Vara Cível",
        "valor_causa": "R$ 120.000,00",
        "cliente": "Unimed Regional",
        "prazo_label": "em 2 dias",
        "prazo_urgente": True,
        "status": "ativo",
    },
    {
        "id": 3,
        "titulo": "Inventário Família Andrade",
        "numero": "0809999-11.2024.8.19.0001",
        "area_direito": "SUCESSÕES",
        "instancia": "1ª Instância",
        "vara_juizo": "2ª Vara de Família e Sucessões",
        "valor_causa": "R$ 800.000,00",
        "cliente": "Roberto Andrade",
        "prazo_label": "em 15 dias",
        "prazo_urgente": False,
        "status": "ativo",
    },
    {
        "id": 4,
        "titulo": "Rescisão Trabalhista – TechCorp",
        "numero": "0102345-66.2024.5.01.0001",
        "area_direito": "TRABALHISTA",
        "instancia": "1ª Instância",
        "vara_juizo": "1ª Vara do Trabalho",
        "valor_causa": "R$ 85.000,00",
        "cliente": "TechCorp Soluções S.A.",
        "prazo_label": "sem prazo",
        "prazo_urgente": False,
        "status": "ativo",
    },
]

MOVIMENTACOES_MOCK = [
    {"data": "25/05/2026", "descricao": "Distribuição por sorteio à 11ª Vara Cível.", "tipo": "andamento"},
    {"data": "31/05/2026", "descricao": "Juntada da petição inicial e documentos.", "tipo": "andamento"},
    {"data": "02/06/2026", "descricao": "Prazo para contestação: 15 dias úteis.", "tipo": "prazo"},
]

PARTES_MOCK = [
    {"nome": "Construtora Horizonte Ltda.", "tipo": "autor", "cpf_cnpj": "12.345.678/0001-90"},
    {"nome": "Município do Rio de Janeiro", "tipo": "reu", "cpf_cnpj": ""},
]


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
