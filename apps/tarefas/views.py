from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Tarefa


@login_required
def quadro(request):
    tarefas = Tarefa.objects.select_related("responsavel", "processo", "cliente").all()
    tarefas_por_status = {
        "a_fazer": [t for t in tarefas if t.status == "a_fazer"],
        "em_andamento": [t for t in tarefas if t.status == "em_andamento"],
        "concluida": [t for t in tarefas if t.status == "concluida"],
    }
    return render(request, "tarefas/quadro.html", {"tarefas_por_status": tarefas_por_status, "item_ativo": "tarefas"})


@login_required
def lista(request):
    tarefas = Tarefa.objects.select_related("responsavel", "processo", "cliente").all()
    return render(request, "tarefas/lista.html", {"tarefas": tarefas, "item_ativo": "tarefas"})


@login_required
def nova(request):
    return render(request, "tarefas/form.html", {"modo": "novo", "item_ativo": "tarefas"})
