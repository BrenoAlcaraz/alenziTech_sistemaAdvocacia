from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import tem_permissao_modulo, tem_habilitacao, nivel_acesso_modulo
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    HAB_AGENDA_CRIAR_PARA_OUTROS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)

from .models import Compromisso
from .forms import CompromissoForm


FILTROS_VALIDOS = {"hoje", "proximos_7", "vencidos", "todos"}
_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}


def _redirect_seguro(request):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("agenda:index")


def _normalizar_filtro(filtro):
    if filtro in FILTROS_VALIDOS:
        return filtro
    return "proximos_7"


def _resolver_escopo(request):
    """
    Resolve o escopo efetivo de LEITURA (somente_seus/todos), seguindo o
    mesmo contrato usado em `apps/tarefas/views.py`: parâmetro AUSENTE
    usa o nível máximo do usuário como padrão; parâmetro PRESENTE com
    valor inválido (incluindo string vazia) ou acima do nível máximo
    autorizado é sempre negado (403). Nunca usado por mutação.
    Retorna (escopo_efetivo, nivel_maximo).
    """
    nivel_maximo = nivel_acesso_modulo(request.user, MODULO_AGENDA)
    if nivel_maximo not in _ESCOPOS_VALIDOS:
        nivel_maximo = NIVEL_SOMENTE_SEUS

    solicitado = request.GET.get("escopo")
    if solicitado is None:
        return nivel_maximo, nivel_maximo

    if solicitado not in _ESCOPOS_VALIDOS:
        raise PermissionDenied
    if solicitado == NIVEL_TODOS and nivel_maximo != NIVEL_TODOS:
        raise PermissionDenied
    return solicitado, nivel_maximo


def _compromissos_no_escopo(request, escopo):
    """QuerySet de LEITURA (index), restrito pelo escopo efetivo."""
    qs = Compromisso.objects.select_related("responsavel", "processo", "cliente")
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(responsavel=request.user)
    return qs


def _compromissos_mutaveis(request):
    """
    QuerySet usado para mutação (editar/concluir/cancelar/reabrir/excluir).

    "Todos" é escopo de visualização, não autorização de mutação sobre
    qualquer compromisso: um usuário não-admin só muta compromisso da
    própria responsabilidade, mesmo com nível máximo `todos`. Só o
    Administrador do escritório alcança qualquer compromisso do tenant
    para mutação.
    """
    qs = Compromisso.objects.all()
    if not usuario_admin_escritorio(request.user):
        qs = qs.filter(responsavel=request.user)
    return qs


def _pode_criar_para_outros(request):
    return usuario_admin_escritorio(request.user) or tem_habilitacao(
        request.user, MODULO_AGENDA, HAB_AGENDA_CRIAR_PARA_OUTROS
    )


@login_required
def index(request):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    filtro = _normalizar_filtro(request.GET.get("filtro", "proximos_7"))
    escopo, escopo_maximo = _resolver_escopo(request)
    hoje = timezone.localdate()
    agora = timezone.now()

    compromissos = _compromissos_no_escopo(request, escopo)

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
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "is_admin": usuario_admin_escritorio(request.user),
        "item_ativo": "agenda",
        "next_url": request.get_full_path(),
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        responsavel_original = compromisso.responsavel
        form = CompromissoForm(request.POST, instance=compromisso)
        if form.is_valid():
            status_original = compromisso.status
            compromisso = form.save(commit=False)
            compromisso.responsavel = responsavel_original
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
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    if request.method == "POST":
        form = CompromissoForm(request.POST)
        if form.is_valid():
            compromisso = form.save(commit=False)
            if not compromisso.responsavel:
                compromisso.responsavel = request.user
            if compromisso.responsavel != request.user and not _pode_criar_para_outros(request):
                raise PermissionDenied
            compromisso.status = "agendado"
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


@login_required
def concluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        compromisso.status = "concluido"
        compromisso.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def cancelar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        compromisso.status = "cancelado"
        compromisso.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def reabrir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        compromisso.status = "agendado"
        compromisso.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def excluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        compromisso.delete()
    return _redirect_seguro(request)
