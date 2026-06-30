from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField, F
from .models import Tarefa
from .forms import TarefaForm


ORDENS_VALIDAS = {
    "prazo_proximo",
    "prazo_distante",
    "prioridade_alta",
    "prioridade_baixa",
    "mais_recentes",
    "mais_antigas",
}


def _normalizar_ordem(ordem):
    if ordem in ORDENS_VALIDAS:
        return ordem
    return "prazo_proximo"


def _get_order_args(ordem):
    if ordem == "prazo_distante":
        return [F("prazo").desc(nulls_last=True), "titulo"]
    if ordem == "prioridade_alta":
        return [
            Case(
                When(prioridade="alta", then=Value(1)),
                When(prioridade="media", then=Value(2)),
                When(prioridade="baixa", then=Value(3)),
                output_field=IntegerField(),
            ),
            "titulo",
        ]
    if ordem == "prioridade_baixa":
        return [
            Case(
                When(prioridade="baixa", then=Value(1)),
                When(prioridade="media", then=Value(2)),
                When(prioridade="alta", then=Value(3)),
                output_field=IntegerField(),
            ),
            "titulo",
        ]
    if ordem == "mais_recentes":
        return ["-criado_em"]
    if ordem == "mais_antigas":
        return ["criado_em"]
    # prazo_proximo é o padrão e o fallback para valores inválidos
    return [F("prazo").asc(nulls_last=True), "titulo"]


@login_required
def quadro(request):
    ordem = _normalizar_ordem(request.GET.get("ordem", "prazo_proximo"))
    tarefas = Tarefa.objects.select_related("responsavel", "processo", "cliente").order_by(*_get_order_args(ordem))
    tarefas_por_status = {
        "a_fazer": [t for t in tarefas if t.status == "a_fazer"],
        "em_andamento": [t for t in tarefas if t.status == "em_andamento"],
        "concluida": [t for t in tarefas if t.status == "concluida"],
    }
    return render(request, "tarefas/quadro.html", {
        "tarefas_por_status": tarefas_por_status,
        "ordem": ordem,
        "item_ativo": "tarefas",
    })


@login_required
def lista(request):
    ordem = _normalizar_ordem(request.GET.get("ordem", "prazo_proximo"))
    tarefas = Tarefa.objects.select_related("responsavel", "processo", "cliente").order_by(*_get_order_args(ordem))
    return render(request, "tarefas/lista.html", {
        "tarefas": tarefas,
        "ordem": ordem,
        "item_ativo": "tarefas",
    })


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
