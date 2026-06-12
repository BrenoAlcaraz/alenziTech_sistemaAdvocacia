from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dados temporários apenas para layout — substituir futuramente por queries reais
RESUMO_MOCK = [
    {"icone": "briefcase", "valor": 5, "label": "Casos no escritório"},
    {"icone": "shield-check", "valor": 2, "label": "Administradores"},
    {"icone": "clock", "valor": 2, "label": "Casos não liberados"},
]

CASOS_MOCK = [
    {"titulo": "Construtora Horizonte vs. Município", "numero": "0801234-55.2024.8.19.0001", "area": "CÍVEL", "adm_count": 1},
    {"titulo": "Unimed – Contencioso de Massa", "numero": "0805678-99.2024.8.19.0001", "area": "CONSUMIDOR", "adm_count": 0},
    {"titulo": "Inventário Família Andrade", "numero": "0809999-11.2024.8.19.0001", "area": "SUCESSÕES", "adm_count": 1},
]


@login_required
def painel(request):
    # Futuramente: calcular resumo real de processos, tarefas e usuários do escritório
    return render(request, "dashboard/painel.html", {
        "resumo": RESUMO_MOCK,
        "casos": CASOS_MOCK,
        "plano_nome": "Mestre",
        "item_ativo": "painel",
    })
