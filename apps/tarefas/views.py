from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Tarefa
from .forms import TarefaForm


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
    if request.method == "POST":
        form = TarefaForm(request.POST)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.responsavel = request.user
            tarefa.status = "a_fazer"
            if not tarefa.cliente and tarefa.processo and tarefa.processo.cliente:
                tarefa.cliente = tarefa.processo.cliente
            tarefa.save()
            return redirect("tarefas:quadro")
    else:
        form = TarefaForm()
    return render(request, "tarefas/form.html", {"form": form, "modo": "novo", "item_ativo": "tarefas"})
