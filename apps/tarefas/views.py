from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField, F
from django.utils.http import url_has_allowed_host_and_scheme
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


def _redirect_seguro(request):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("tarefas:quadro")


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
        "next_url": request.get_full_path(),
        "item_ativo": "tarefas",
    })


@login_required
def lista(request):
    ordem = _normalizar_ordem(request.GET.get("ordem", "prazo_proximo"))
    tarefas = Tarefa.objects.select_related("responsavel", "processo", "cliente").order_by(*_get_order_args(ordem))
    return render(request, "tarefas/lista.html", {
        "tarefas": tarefas,
        "ordem": ordem,
        "next_url": request.get_full_path(),
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


@login_required
def editar(request, pk):
    tarefa = get_object_or_404(Tarefa, pk=pk)
    if request.method == "POST":
        form = TarefaForm(request.POST, instance=tarefa)
        if form.is_valid():
            responsavel_original = tarefa.responsavel
            status_original = tarefa.status
            tarefa = form.save(commit=False)
            tarefa.responsavel = responsavel_original
            tarefa.status = status_original
            if not tarefa.cliente and tarefa.processo and tarefa.processo.cliente:
                tarefa.cliente = tarefa.processo.cliente
            tarefa.save()
            return redirect("tarefas:quadro")
    else:
        form = TarefaForm(instance=tarefa)
    return render(request, "tarefas/form.html", {
        "form": form,
        "modo": "editar",
        "tarefa": tarefa,
        "item_ativo": "tarefas",
    })


@login_required
def concluir(request, pk):
    tarefa = get_object_or_404(Tarefa, pk=pk)
    if request.method == "POST":
        tarefa.status = "concluida"
        tarefa.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def reabrir(request, pk):
    tarefa = get_object_or_404(Tarefa, pk=pk)
    if request.method == "POST":
        tarefa.status = "a_fazer"
        tarefa.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def iniciar(request, pk):
    tarefa = get_object_or_404(Tarefa, pk=pk)
    if request.method == "POST":
        tarefa.status = "em_andamento"
        tarefa.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def excluir(request, pk):
    tarefa = get_object_or_404(Tarefa, pk=pk)
    if request.method == "POST":
        tarefa.delete()
    return _redirect_seguro(request)
