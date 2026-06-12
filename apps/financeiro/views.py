from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dados temporários apenas para layout — substituir futuramente por queries reais
LANCAMENTOS_MOCK = [
    {"id": 1, "tipo": "receita", "descricao": "Honorários – Construtora Horizonte", "valor": "R$ 25.000,00", "data": "01/06/2026", "categoria": "Honorário", "cliente": "Construtora Horizonte Ltda."},
    {"id": 2, "tipo": "despesa", "descricao": "Custas processuais – Unimed", "valor": "R$ 1.500,00", "data": "02/06/2026", "categoria": "Reembolso", "cliente": "Unimed Regional"},
    {"id": 3, "tipo": "despesa", "descricao": "Honorários periciais", "valor": "R$ 10.000,00", "data": "28/05/2026", "categoria": "Despesa do Escritório", "cliente": ""},
]

CUSTAS_MOCK = [
    {
        "id": 1,
        "descricao": "Custas de citação – Unimed (adiantado pelo escritório)",
        "valor": "R$ 740,00",
        "tipo": "adiantamento",
        "negativo": True,
        "cliente": "Unimed Regional",
        "data": "02/06/2026",
        "detalhe": "Pagamento adiantado pelo escritório • Unimed Regional",
    },
]

SALDO_CLIENTES_MOCK = [
    {"cliente": "Construtora Horizonte Ltda.", "saldo": "Crédito: R$ 3.150,00", "credito": True},
    {"cliente": "Unimed Regional", "saldo": "A cobrar: R$ 740,00", "credito": False},
]

RESUMO_MOCK = {
    "a_receber": "R$ 72.000,00",
    "recebido": "R$ 25.000,00",
    "despesas": "R$ 11.500,00",
    "saldo": "R$ 13.500,00",
}


@login_required
def index(request):
    # Futuramente: calcular totais reais e listar lançamentos com filtros
    return render(request, "financeiro/index.html", {
        "resumo": RESUMO_MOCK,
        "lancamentos": LANCAMENTOS_MOCK,
        "aba_ativa": "lancamentos", "item_ativo": "financeiro",
    })


@login_required
def custas(request):
    return render(request, "financeiro/custas.html", {
        "resumo": RESUMO_MOCK,
        "custas": CUSTAS_MOCK,
        "saldo_clientes": SALDO_CLIENTES_MOCK,
        "aba_ativa": "custas", "item_ativo": "financeiro",
    })


@login_required
def form_lancamento(request):
    return render(request, "financeiro/form_lancamento.html", {"item_ativo": "financeiro"})


@login_required
def form_custa(request):
    return render(request, "financeiro/form_custa.html", {"item_ativo": "financeiro"})
