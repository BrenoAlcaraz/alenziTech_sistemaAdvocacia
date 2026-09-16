from datetime import timedelta

from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Case, When, Value, IntegerField, F
from django.http import JsonResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import tem_permissao_modulo, tem_habilitacao, nivel_acesso_modulo
from apps.accounts.permissoes_constants import (
    MODULO_GERIR,
    MODULO_TAREFAS,
    HAB_TAREFAS_ATRIBUIR_OUTROS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.notificacoes.models import Notificacao
from apps.processos.services import processos_do_cliente, rotulo_processo
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

ABAS_VALIDAS = {"novidades", "terceiro", "delegadas", "outros"}


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


def _pode_ver_outro_usuario(user):
    """Painel do gestor: só quem tem `gerir`/Admin pode olhar as tarefas
    de um usuário específico via ?usuario= — para qualquer outra pessoa
    o parâmetro é ignorado (specs/dashboard-painel-do-gestor.md)."""
    return usuario_admin_escritorio(user) or tem_permissao_modulo(user, MODULO_GERIR)


def _pode_atribuir_a_outros(request):
    return usuario_admin_escritorio(request.user) or tem_habilitacao(
        request.user, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS
    )


def _normalizar_aba(request, usuario_filtro):
    """
    Sub-aba ativa da faixa abaixo da lista principal (mesmo padrão de
    `apps/agenda/views.py`). Quem chega via `?usuario=` (seletor de
    colega da aba "Ver tarefas de outra pessoa") reabre já naquela aba;
    senão respeita `?aba=` se válido; senão "Recentes" é o padrão.
    """
    if usuario_filtro is not None:
        return "outros"
    aba = request.GET.get("aba")
    if aba in ABAS_VALIDAS:
        return aba
    return "novidades"


def _tarefas_novidades(request):
    """
    Sub-aba "Recentes (últimas 24h)": qualquer tarefa que entrou na
    lista do usuário nas últimas 24h, de qualquer origem — `atribuido_em`
    marca tanto a atribuição inicial quanto uma reatribuição posterior.
    Sempre visível, sem checagem de habilitação.
    """
    limite = timezone.now() - timedelta(hours=24)
    return (
        Tarefa.objects.select_related("responsavel", "processo", "cliente")
        .filter(responsavel=request.user, atribuido_em__gte=limite)
        .order_by("-atribuido_em")
    )


def _tarefas_atribuidas_por_terceiros(request):
    """
    Sub-aba "Atribuídas a mim por terceiros": só tarefas em que o
    usuário é responsável, mas quem atribuiu foi outra pessoa. Sempre
    visível, sem checagem de habilitação.
    """
    return (
        Tarefa.objects.select_related("responsavel", "processo", "cliente")
        .filter(responsavel=request.user)
        .exclude(atribuidor__isnull=True)
        .exclude(atribuidor=request.user)
        .order_by("-atribuido_em")
    )


def _tarefas_delegadas_por_mim(request):
    """
    Sub-aba "Delegadas por mim": todas as tarefas que o próprio usuário
    atribuiu a outra pessoa, qualquer status. Só para quem tem a
    habilitação de atribuir tarefa a terceiros.
    """
    return (
        Tarefa.objects.select_related("responsavel", "processo", "cliente")
        .filter(atribuidor=request.user)
        .exclude(responsavel=request.user)
        .order_by("-atribuido_em")
    )


def _usuario_travado(request):
    """
    Usuário travado no campo "Atribuir a" quando o formulário é aberto a
    partir de "+ Nova tarefa para esta pessoa" (sub-aba "Ver tarefas de
    outra pessoa"). `disabled=True` no form faz o Django ignorar
    qualquer valor de `destinatario` vindo do POST e usar sempre o
    `initial` — por isso o travamento é seguro mesmo que o campo seja
    adulterado no HTML.
    """
    para_usuario_id = request.POST.get("para_usuario") or request.GET.get("para_usuario")
    if not para_usuario_id:
        return None
    return get_object_or_404(User, pk=para_usuario_id, is_active=True)


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

    usuario_filtro = None
    usuario_filtro_id = request.GET.get("usuario")
    if usuario_filtro_id and _pode_ver_outro_usuario(request.user):
        usuario_filtro = get_object_or_404(User, pk=usuario_filtro_id)

    if usuario_filtro:
        # Atalho do Painel do gestor: ignora o escopo somente_seus/todos
        # do próprio usuário logado — vê as tarefas do usuário filtrado.
        escopo = escopo_maximo = NIVEL_TODOS
        tarefas = Tarefa.objects.select_related(
            "responsavel", "processo", "cliente"
        ).filter(responsavel=usuario_filtro).order_by(*_get_order_args(ordem))
    else:
        escopo, escopo_maximo = _resolver_escopo(request)
        tarefas = _tarefas_no_escopo(request, escopo).order_by(*_get_order_args(ordem))

    # Atalho "ver todas" do card de Tarefas relacionadas no detalhe do
    # Processo/Cliente — só mais um filtro sobre o escopo normal do
    # usuário, nunca amplia o que ele já enxergaria no quadro.
    processo_filtro_id = request.GET.get("processo")
    if processo_filtro_id:
        tarefas = tarefas.filter(processo_id=processo_filtro_id)
    cliente_filtro_id = request.GET.get("cliente")
    if cliente_filtro_id:
        tarefas = tarefas.filter(cliente_id=cliente_filtro_id)

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
        "usuario_filtro": usuario_filtro,
        "processo_filtro_id": processo_filtro_id,
        "cliente_filtro_id": cliente_filtro_id,
        "is_admin": usuario_admin_escritorio(request.user),
        "next_url": request.get_full_path(),
        "item_ativo": "tarefas",
    })


@login_required
def lista(request):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    ordem = _normalizar_ordem(request.GET.get("ordem", "prazo_proximo"))
    pode_atribuir_a_outros = _pode_atribuir_a_outros(request)

    usuario_filtro = None
    usuario_filtro_id = request.GET.get("usuario")
    if usuario_filtro_id and pode_atribuir_a_outros:
        usuario_filtro = get_object_or_404(User, pk=usuario_filtro_id)

    if usuario_filtro:
        # Sub-aba "Ver tarefas de outra pessoa": ignora o escopo
        # somente_seus/todos do próprio usuário logado — mostra as
        # tarefas do usuário filtrado (mesmo padrão de agenda:index).
        escopo = escopo_maximo = NIVEL_TODOS
        tarefas = Tarefa.objects.select_related(
            "responsavel", "processo", "cliente"
        ).filter(responsavel=usuario_filtro).order_by(*_get_order_args(ordem))
    else:
        escopo, escopo_maximo = _resolver_escopo(request)
        tarefas = _tarefas_no_escopo(request, escopo).order_by(*_get_order_args(ordem))

    contexto = {
        "tarefas": tarefas,
        "ordem": ordem,
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "usuario_filtro": usuario_filtro,
        "is_admin": usuario_admin_escritorio(request.user),
        "next_url": request.get_full_path(),
        "item_ativo": "tarefas",
        "aba_ativa": _normalizar_aba(request, usuario_filtro),
        "pode_atribuir_a_outros": pode_atribuir_a_outros,
    }

    # ── Faixa de sub-abas ────────────────────────────────────────────
    contexto.update({
        "tarefas_novidades": list(_tarefas_novidades(request)),
        "tarefas_terceiro": list(_tarefas_atribuidas_por_terceiros(request)),
    })
    if pode_atribuir_a_outros:
        contexto["tarefas_delegadas"] = list(_tarefas_delegadas_por_mim(request))
        contexto["usuarios_outros"] = User.objects.filter(is_active=True).order_by(
            "first_name", "username"
        )

    return render(request, "tarefas/lista.html", contexto)


@login_required
def processos_por_cliente(request):
    """Processos do cliente informado, para o filtro dinâmico dos
    formulários de criação/edição de tarefas."""
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    processos = processos_do_cliente(request.GET.get("cliente"))
    return JsonResponse({
        "processos": [{"id": p.id, "label": rotulo_processo(p)} for p in processos],
    })


@login_required
def nova(request):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    usuario_travado = _usuario_travado(request)
    if request.method == "POST":
        form = TarefaForm(request.POST)
        if usuario_travado:
            form.fields["destinatario"].disabled = True
            form.fields["destinatario"].initial = usuario_travado
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
            if not tarefa.cliente and tarefa.processo:
                tarefa.cliente = tarefa.processo.clientes.first()
            tarefa.save()
            return redirect("tarefas:quadro")
    else:
        form = TarefaForm(initial={"destinatario": usuario_travado} if usuario_travado else None)
        if usuario_travado:
            form.fields["destinatario"].disabled = True
    return render(request, "tarefas/form.html", {
        "form": form,
        "modo": "novo",
        "item_ativo": "tarefas",
        "usuario_travado": usuario_travado,
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_TAREFAS):
        raise PermissionDenied
    _resolver_escopo(request)
    tarefa = get_object_or_404(_tarefas_mutaveis(request), pk=pk)
    next_url = request.GET.get("next") or request.POST.get("next")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = None
    if request.method == "POST":
        form = TarefaForm(request.POST, instance=tarefa)
        if form.is_valid():
            responsavel_original = tarefa.responsavel
            status_original = tarefa.status
            tarefa = form.save(commit=False)
            tarefa.responsavel = responsavel_original
            tarefa.status = status_original
            if not tarefa.cliente and tarefa.processo:
                tarefa.cliente = tarefa.processo.clientes.first()
            tarefa.save()
            return redirect(next_url or "tarefas:quadro")
    else:
        form = TarefaForm(instance=tarefa)
    return render(request, "tarefas/form.html", {
        "form": form,
        "modo": "editar",
        "tarefa": tarefa,
        "next_url": next_url,
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
        if tarefa.criador_id and tarefa.criador_id != tarefa.responsavel_id:
            Notificacao.objects.create(
                destinatario=tarefa.criador,
                mensagem=f'Tarefa concluída: "{tarefa.titulo}"',
            )
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
