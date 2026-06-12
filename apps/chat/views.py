from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dados temporários apenas para layout — substituir futuramente por queries reais
CONVERSAS_MOCK = [
    {
        "id": 1,
        "nome": "Dra. Maria Lenzi",
        "iniciais": "ML",
        "cor_avatar": "bg-teal-600",
        "ultima_mensagem": "Você: Vi sim, Maria. Prazo dia 12. Consegue adiantar a contestação?",
        "horario": "08:45",
        "nao_lidas": 0,
    },
    {
        "id": 2,
        "nome": "Lucas Martins",
        "iniciais": "LM",
        "cor_avatar": "bg-stone-500",
        "ultima_mensagem": "Confirmado, vou protocolar ainda hoje.",
        "horario": "Ontem",
        "nao_lidas": 2,
    },
]

MENSAGENS_MOCK = [
    {"autor": "Dra. Maria Lenzi", "iniciais": "ML", "conteudo": "João, vi o prazo do processo Unimed. Você já elaborou a contestação?", "horario": "08:30", "minha": False},
    {"autor": "Você", "iniciais": "JS", "conteudo": "Vi sim, Maria. Prazo dia 12. Consegue adiantar a contestação?", "horario": "08:45", "minha": True},
]


@login_required
def lista(request):
    # Futuramente: Conversa.objects.filter(participantes=request.user)
    return render(request, "chat/lista.html", {"conversas": CONVERSAS_MOCK, "item_ativo": "chat"})


@login_required
def detalhe(request, pk):
    conversa = next((c for c in CONVERSAS_MOCK if c["id"] == pk), CONVERSAS_MOCK[0])
    return render(request, "chat/detalhe.html", {
        "conversa": conversa,
        "mensagens": MENSAGENS_MOCK,
        "item_ativo": "chat",
    })
