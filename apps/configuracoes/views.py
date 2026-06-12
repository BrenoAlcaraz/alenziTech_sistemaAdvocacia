from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dados temporários apenas para layout — substituir futuramente por queries reais
USUARIOS_MOCK = [
    {"nome": "Dr. João Souza", "username": "joao.souza", "iniciais": "JS", "badge": "Mestre", "voce": True},
    {"nome": "Dra. Maria Lenzi", "username": "maria.lenzi", "iniciais": "ML", "badge": "Advogado", "voce": False},
    {"nome": "Lucas Martins", "username": "lucas.martins", "iniciais": "LM", "badge": "Funcionário", "voce": False},
]


@login_required
def index(request):
    # Futuramente: listar usuários reais, exibir dados reais do plano e do escritório
    return render(request, "configuracoes/index.html", {
        "usuarios": USUARIOS_MOCK,
        "plano_nome": "Plano Profissional",
        "usuarios_ativos": 6,
        "limite_usuarios": 10, "item_ativo": "configuracoes",
    })
