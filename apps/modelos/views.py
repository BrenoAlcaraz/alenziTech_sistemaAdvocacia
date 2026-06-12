from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dados temporários apenas para layout — substituir futuramente por queries reais
MODELOS_MOCK = [
    {
        "id": 1,
        "titulo": "Petição inicial – Ação de cobrança",
        "categoria": "Petição inicial",
        "area_direito": "Cível",
        "preview": "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA __ VARA CÍVEL.... [modelo de exemplo com a estrutura e o tom que o escr...",
    },
    {
        "id": 2,
        "titulo": "Contestação – Padrão do escritório",
        "categoria": "Contestação",
        "area_direito": "Cível",
        "preview": "MM. Juízo... [modelo de contestação com preliminares e mérito no estilo da casa]",
    },
]


@login_required
def lista(request):
    aba_ativa = request.GET.get("aba", "modelos")
    return render(request, "modelos/lista.html", {
        "modelos": MODELOS_MOCK,
        "aba_ativa": aba_ativa, "item_ativo": "modelos",
    })


@login_required
def novo(request):
    return render(request, "modelos/form.html", {"modo": "novo", "item_ativo": "modelos"})


@login_required
def detalhe(request, pk):
    modelo = next((m for m in MODELOS_MOCK if m["id"] == pk), MODELOS_MOCK[0])
    return render(request, "modelos/form.html", {"modo": "editar", "modelo": modelo, "item_ativo": "modelos"})
