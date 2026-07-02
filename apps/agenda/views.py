from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Compromisso
from .forms import CompromissoForm


FILTROS_VALIDOS = {"hoje", "proximos_7", "vencidos", "todos"}


def _normalizar_filtro(filtro):
    if filtro in FILTROS_VALIDOS:
        return filtro
    return "proximos_7"


@login_required
def index(request):
    filtro = _normalizar_filtro(request.GET.get("filtro", "proximos_7"))
    hoje = timezone.localdate()
    agora = timezone.now()

    compromissos = Compromisso.objects.select_related(
        "responsavel", "processo", "cliente"
    )

    if filtro == "hoje":
        compromissos = compromissos.filter(data_hora_inicio__date=hoje)
    elif filtro == "proximos_7":
        compromissos = compromissos.filter(
            data_hora_inicio__date__gte=hoje,
            data_hora_inicio__date__lte=hoje + timedelta(days=7),
        )
    elif filtro == "vencidos":
        compromissos = compromissos.filter(
            data_hora_inicio__lt=agora,
            status="agendado",
        )
    # "todos": sem filtro de data ou status

    compromissos = compromissos.order_by("data_hora_inicio")

    return render(request, "agenda/lista.html", {
        "compromissos": compromissos,
        "filtro": filtro,
        "item_ativo": "agenda",
    })


@login_required
def editar(request, pk):
    compromisso = get_object_or_404(Compromisso, pk=pk)
    if request.method == "POST":
        form = CompromissoForm(request.POST, instance=compromisso)
        if form.is_valid():
            status_original = compromisso.status
            compromisso = form.save(commit=False)
            compromisso.status = status_original
            if not compromisso.cliente and compromisso.processo and compromisso.processo.cliente:
                compromisso.cliente = compromisso.processo.cliente
            compromisso.save()
            return redirect("agenda:index")
    else:
        form = CompromissoForm(instance=compromisso)
    return render(request, "agenda/form.html", {
        "form": form,
        "modo": "editar",
        "compromisso": compromisso,
        "item_ativo": "agenda",
    })


@login_required
def form_compromisso(request):
    if request.method == "POST":
        form = CompromissoForm(request.POST)
        if form.is_valid():
            compromisso = form.save(commit=False)
            compromisso.status = "agendado"
            if not compromisso.responsavel:
                compromisso.responsavel = request.user
            if not compromisso.cliente and compromisso.processo and compromisso.processo.cliente:
                compromisso.cliente = compromisso.processo.cliente
            compromisso.save()
            return redirect("agenda:index")
    else:
        form = CompromissoForm(initial={"responsavel": request.user})
    return render(request, "agenda/form.html", {
        "form": form,
        "item_ativo": "agenda",
    })
