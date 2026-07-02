from datetime import timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Compromisso


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
def form_compromisso(request):
    return render(request, "agenda/form.html", {"item_ativo": "agenda"})
