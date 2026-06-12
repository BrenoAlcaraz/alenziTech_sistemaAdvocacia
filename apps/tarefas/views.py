from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dados temporários apenas para layout — substituir futuramente por queries reais
TAREFAS_MOCK = [
    {
        "id": 1,
        "titulo": "Levantar documentos do inventário",
        "descricao": "Certidões e bens da Família Andrade.",
        "status": "a_fazer",
        "prioridade": "alta",
        "prazo_label": "em 6 dias",
        "prazo_urgente": False,
        "responsavel": "Bia Rocha",
        "processo": "Inventário Família Andrade",
    },
    {
        "id": 2,
        "titulo": "Cumprir liminar – Unimed",
        "descricao": "Oficiar e acompanhar cumprimento.",
        "status": "a_fazer",
        "prioridade": "alta",
        "prazo_label": "em 2 dias",
        "prazo_urgente": True,
        "responsavel": "Lucas Martins",
        "processo": "Unimed – Contencioso de Massa",
    },
    {
        "id": 3,
        "titulo": "Elaborar contestação – TechCorp",
        "descricao": "Prazo fatal. Verificar documentos do RH.",
        "status": "em_andamento",
        "prioridade": "alta",
        "prazo_label": "em 3 dias",
        "prazo_urgente": True,
        "responsavel": "Dr. João Souza",
        "processo": "Rescisão Trabalhista – TechCorp",
    },
]


@login_required
def quadro(request):
    # Futuramente: Tarefa.objects.select_related("responsavel", "processo").all()
    tarefas_por_status = {
        "a_fazer": [t for t in TAREFAS_MOCK if t["status"] == "a_fazer"],
        "em_andamento": [t for t in TAREFAS_MOCK if t["status"] == "em_andamento"],
        "concluida": [t for t in TAREFAS_MOCK if t["status"] == "concluida"],
    }
    return render(request, "tarefas/quadro.html", {"tarefas_por_status": tarefas_por_status, "item_ativo": "tarefas"})


@login_required
def lista(request):
    return render(request, "tarefas/lista.html", {"tarefas": TAREFAS_MOCK, "item_ativo": "tarefas"})


@login_required
def nova(request):
    return render(request, "tarefas/form.html", {"modo": "novo", "item_ativo": "tarefas"})
