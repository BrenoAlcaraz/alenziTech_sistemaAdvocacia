from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Case, When, Value, IntegerField, F
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import tem_permissao_modulo, tem_habilitacao, nivel_acesso_modulo
from apps.accounts.permissoes_constants import (
    MODULO_TAREFAS,
    HAB_TAREFAS_ATRIBUIR_OUTROS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from .models import ReatribuicaoTarefa, Tarefa
from .forms import ReatribuirForm, TarefaForm


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


_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}


def _resolver_escopo(request):
    """
    Resolve o escopo efetivo de LEITURA (somente_seus/todos), seguindo o
    mesmo contrato usado em `apps/clientes/views.py`: parâmetro AUSENTE
    usa o nível máximo do usuário como padrão; parâmetro PRESENTE com
    valor inválido (incluindo string vazia) ou acima do nível máximo
    autorizado é sempre negado (403). Nunca usado por mutação.
    Retorna (escopo_efetivo, nivel_maximo).
    """
    nivel_maximo = nivel_acesso_modulo(request.user, MODULO_TAREFAS)
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


def _tarefas_no_escopo(request, escopo):
    """QuerySet de LEITURA (quadro/lista), restrito pelo escopo efetivo."""
    qs = Tarefa.objects.select_related("responsavel", "processo", "cliente")
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(responsavel=request.user)
    return qs


def _tarefas_mutaveis(request):
    """
    QuerySet usado para mutação (editar/reatribuir/concluir/etc.).

    "Todos" é escopo de visualização, não autorização de mutação sobre
    qualquer tarefa: um usuário não-admin só muta tarefa da própria
    responsabilidade, mesmo com nível máximo `todos`. Só o Administrador
    do escritório alcança qualquer tarefa do tenant para mutação.
    """
    qs = Tarefa.objects.all()
    if not usuario_admin_escritorio(request.user):
        qs = qs.filter(responsavel=request.user)
    return qs


def _pode_atribuir_a_outros(request):
    return usuario_admin_escritorio(request.user) or tem_habilitacao(
        request.user, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS
    )


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
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    ordem = _normalizar_ordem(request.GET.get("ordem", "prazo_proximo"))
    escopo, escopo_maximo = _resolver_escopo(request)
    tarefas = _tarefas_no_escopo(request, escopo).order_by(*_get_order_args(ordem))
    tarefas_por_status = {
        "a_fazer": [t for t in tarefas if t.status == "a_fazer"],
        "em_andamento": [t for t in tarefas if t.status == "em_andamento"],
        "concluida": [t for t in tarefas if t.status == "concluida"],
        "cancelada": [t for t in tarefas if t.status == "cancelada"],
    }
    return render(request, "tarefas/quadro.html", {
        "tarefas_por_status": tarefas_por_status,
        "ordem": ordem,
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "is_admin": usuario_admin_escritorio(request.user),
        "next_url": request.get_full_path(),
        "item_ativo": "tarefas",
    })


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    ordem = _normalizar_ordem(request.GET.get("ordem", "prazo_proximo"))
    escopo, escopo_maximo = _resolver_escopo(request)
    tarefas = _tarefas_no_escopo(request, escopo).order_by(*_get_order_args(ordem))
    return render(request, "tarefas/lista.html", {
        "tarefas": tarefas,
        "ordem": ordem,
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "is_admin": usuario_admin_escritorio(request.user),
        "next_url": request.get_full_path(),
        "item_ativo": "tarefas",
    })


@login_required
def nova(request):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    if request.method == "POST":
        form = TarefaForm(request.POST)
        if form.is_valid():
            destinatario = form.cleaned_data.get("destinatario")
            if destinatario and destinatario != request.user and not _pode_atribuir_a_outros(request):
                raise PermissionDenied
            tarefa = form.save(commit=False)
            tarefa.criador = request.user
            tarefa.atribuidor = request.user
            tarefa.responsavel = destinatario or request.user
            tarefa.atribuido_em = timezone.now()
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
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
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
def reatribuir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = ReatribuirForm(request.POST)
        if form.is_valid():
            novo_responsavel = form.cleaned_data["destinatario"]
            if novo_responsavel != request.user and not _pode_atribuir_a_outros(request):
                raise PermissionDenied
            ReatribuicaoTarefa.objects.create(
                tarefa=tarefa,
                responsavel_anterior=tarefa.responsavel,
                responsavel_novo=novo_responsavel,
                autor=request.user,
            )
            tarefa.responsavel = novo_responsavel
            tarefa.atribuido_em = timezone.now()
            tarefa.save(update_fields=["responsavel", "atribuido_em"])
            return _redirect_seguro(request)
    else:
        form = ReatribuirForm(initial={"destinatario": tarefa.responsavel_id})
    return render(request, "tarefas/reatribuir.html", {
        "form": form,
        "tarefa": tarefa,
        "reatribuicoes": tarefa.reatribuicoes.select_related("responsavel_anterior", "responsavel_novo", "autor"),
        "next_url": request.GET.get("next") or request.path,
        "item_ativo": "tarefas",
    })


@login_required
def concluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
    if request.method == "POST":
        tarefa.status = "concluida"
        tarefa.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def reabrir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
    if request.method == "POST":
        tarefa.status = "a_fazer"
        tarefa.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def iniciar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
    if request.method == "POST":
        tarefa.status = "em_andamento"
        tarefa.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def cancelar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
    if request.method == "POST":
        tarefa.status = "cancelada"
        tarefa.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def excluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
    if request.method == "POST":
        tarefa.delete()
    return _redirect_seguro(request)
