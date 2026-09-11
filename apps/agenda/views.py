from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
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
from apps.notificacoes.models import Notificacao
from apps.processos.services import processos_do_cliente

from .models import Compromisso, ParticipanteCompromisso
from .forms import AdicionarParticipanteForm, CompromissoForm


FILTROS_VALIDOS = {"hoje", "proximos_7", "vencidos", "todos"}
_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}
VISOES_VALIDAS = {"lista", "calendario"}

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
DIAS_SEMANA = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]

# Cor de cada tipo no calendário — mesmo mapeamento visual dos badges de
# lista.html, em versão sólida (para o ponto indicador do dia).
CORES_TIPO = {
    "audiencia": "#dc2626",
    "prazo": "#b45309",
    "reuniao": "#15803d",
    "protocolo": "#6b7280",
    "pericia": "#a21caf",
    "julgamento": "#292524",
    "retorno": "#0d9488",
    "outro": "#6b7280",
}


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


def _normalizar_visao(visao):
    if visao in VISOES_VALIDAS:
        return visao
    return "lista"


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


def _aplicar_escopo(qs, request, escopo):
    """
    Em `somente_seus`, restringe a compromisso onde o usuário é
    responsável OU participante (qualquer status de confirmação) —
    participante nunca é responsável, só ganha visibilidade.
    """
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(
            Q(responsavel=request.user) | Q(participacoes__usuario=request.user)
        ).distinct()
    return qs


def _compromissos_no_escopo(request, escopo):
    """
    QuerySet de LEITURA (index), restrito pelo escopo efetivo.

    Compromisso cancelado nunca aparece na grade operacional padrão —
    só na seção "Cancelados" (ver `cancelados`).
    """
    qs = Compromisso.objects.select_related(
        "responsavel", "processo", "cliente"
    ).exclude(status="cancelado")
    return _aplicar_escopo(qs, request, escopo)


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


def _usuarios_elegiveis_para_participante(compromisso):
    """Usuários que ainda podem ser convidados: mesmo universo do
    responsável, exceto o próprio responsável e quem já participa."""
    return User.objects.filter(is_active=True).exclude(
        pk__in=compromisso.participacoes.values("usuario_id")
    ).exclude(pk=compromisso.responsavel_id).order_by("first_name", "username")


def _horario_curto(compromisso):
    return timezone.localtime(compromisso.data_hora_inicio).strftime("%d/%m %H:%M")


def _notificar_convite(participacao):
    Notificacao.objects.create(
        destinatario=participacao.usuario,
        mensagem=(
            f'Você foi convidado para "{participacao.compromisso.titulo}" '
            f"em {_horario_curto(participacao.compromisso)} — confirme sua presença."
        ),
    )


def _resetar_confirmacoes_por_reagendamento(compromisso):
    """
    Volta para pendente a confirmação de todo participante já confirmado
    e notifica cada um — chamado quando `data_hora_inicio` muda numa
    edição (compromisso já reflete a nova data neste ponto).
    """
    confirmados = list(
        compromisso.participacoes.filter(
            status=ParticipanteCompromisso.STATUS_CONFIRMADO
        ).select_related("usuario")
    )
    for participacao in confirmados:
        Notificacao.objects.create(
            destinatario=participacao.usuario,
            mensagem=(
                f'"{compromisso.titulo}" foi reagendado para '
                f"{_horario_curto(compromisso)} — confirme sua presença novamente."
            ),
        )
    compromisso.participacoes.filter(
        pk__in=[p.pk for p in confirmados]
    ).update(status=ParticipanteCompromisso.STATUS_PENDENTE, lembrete_enviado=False)


def _notificar_cancelamento(compromisso):
    """Notificação distinta de convite/lembrete — responsável e todos os
    participantes, independente do status de confirmação de cada um."""
    horario = _horario_curto(compromisso)
    mensagem = f'Compromisso cancelado: "{compromisso.titulo}" em {horario}'
    destinatarios = list(
        compromisso.participacoes.values_list("usuario_id", flat=True)
    )
    if compromisso.responsavel_id:
        destinatarios.append(compromisso.responsavel_id)
    for destinatario_id in destinatarios:
        Notificacao.objects.create(destinatario_id=destinatario_id, mensagem=mensagem)


def _anexar_minha_participacao(request, compromissos):
    participacoes_usuario = {
        p.compromisso_id: p
        for p in ParticipanteCompromisso.objects.filter(
            compromisso_id__in=[c.pk for c in compromissos], usuario=request.user
        )
    }
    for compromisso in compromissos:
        compromisso.minha_participacao = participacoes_usuario.get(compromisso.pk)


def _parse_int(valor, minimo=None, maximo=None):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    if minimo is not None and numero < minimo:
        return None
    if maximo is not None and numero > maximo:
        return None
    return numero


def _resolver_mes_ano(request, hoje):
    ano = _parse_int(request.GET.get("ano"), minimo=1, maximo=9999) or hoje.year
    mes = _parse_int(request.GET.get("mes"), minimo=1, maximo=12) or hoje.month
    return ano, mes


def _mes_adjacente(ano, mes, delta):
    indice = (ano * 12 + (mes - 1)) + delta
    return indice // 12, indice % 12 + 1


def _grade_do_mes(ano, mes):
    """(offset a partir de domingo, dias no mês) — sem dias do mês
    anterior/seguinte, mesmo comportamento do protótipo (célula vazia só
    antes do dia 1)."""
    _, dias_no_mes = monthrange(ano, mes)
    primeiro_dia_semana = date(ano, mes, 1).weekday()  # segunda=0
    offset_domingo = (primeiro_dia_semana + 1) % 7
    return offset_domingo, dias_no_mes


def _resolver_dia_selecionado(request, ano, mes, dias_no_mes, hoje):
    dia = _parse_int(request.GET.get("dia"), minimo=1, maximo=dias_no_mes)
    if dia:
        return dia
    if ano == hoje.year and mes == hoje.month:
        return hoje.day
    return 1


def _tipos_por_dia(compromissos_mes):
    """{dia: [{"tipo","cor"}, ...]} — ordem estável pela ordem de
    TIPO_CHOICES, sem repetir tipo já visto no mesmo dia."""
    tipos_presentes = defaultdict(set)
    for compromisso in compromissos_mes:
        dia = timezone.localtime(compromisso.data_hora_inicio).day
        tipos_presentes[dia].add(compromisso.tipo)
    return {
        dia: [
            {"tipo": tipo, "cor": CORES_TIPO[tipo]}
            for tipo, _ in Compromisso.TIPO_CHOICES
            if tipo in presentes
        ]
        for dia, presentes in tipos_presentes.items()
    }


def _contexto_calendario(request, escopo):
    hoje = timezone.localdate()
    ano, mes = _resolver_mes_ano(request, hoje)
    offset_domingo, dias_no_mes = _grade_do_mes(ano, mes)
    dia_selecionado = _resolver_dia_selecionado(request, ano, mes, dias_no_mes, hoje)

    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, dias_no_mes)
    compromissos_mes = _compromissos_no_escopo(request, escopo).filter(
        data_hora_inicio__date__gte=primeiro_dia,
        data_hora_inicio__date__lte=ultimo_dia,
    )
    tipos_por_dia = _tipos_por_dia(compromissos_mes)

    dias = [
        {
            "numero": numero,
            "hoje": ano == hoje.year and mes == hoje.month and numero == hoje.day,
            "selecionado": numero == dia_selecionado,
            "tipos": tipos_por_dia.get(numero, []),
        }
        for numero in range(1, dias_no_mes + 1)
    ]

    data_selecionada = date(ano, mes, dia_selecionado)
    compromissos_dia = list(
        _compromissos_no_escopo(request, escopo)
        .filter(data_hora_inicio__date=data_selecionada)
        .order_by("data_hora_inicio")
    )
    _anexar_minha_participacao(request, compromissos_dia)

    ano_anterior, mes_anterior = _mes_adjacente(ano, mes, -1)
    ano_seguinte, mes_seguinte = _mes_adjacente(ano, mes, 1)

    return {
        "cal_ano": ano,
        "cal_mes": mes,
        "cal_mes_nome": MESES[mes - 1],
        "cal_offset_domingo": range(offset_domingo),
        "cal_dias": dias,
        "cal_ano_anterior": ano_anterior,
        "cal_mes_anterior": mes_anterior,
        "cal_ano_seguinte": ano_seguinte,
        "cal_mes_seguinte": mes_seguinte,
        "cal_hoje_ano": hoje.year,
        "cal_hoje_mes": hoje.month,
        "cal_data_selecionada_label": (
            f"{dia_selecionado} de {MESES[mes - 1].lower()} — "
            f"{DIAS_SEMANA[data_selecionada.weekday()]}"
        ),
        "compromissos_dia": compromissos_dia,
        "legenda_tipos": [
            {"tipo": tipo, "rotulo": rotulo, "cor": CORES_TIPO[tipo]}
            for tipo, rotulo in Compromisso.TIPO_CHOICES
        ],
    }


@login_required
def index(request):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    visao = _normalizar_visao(request.GET.get("visao"))
    contexto = {
        "visao": visao,
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "is_admin": usuario_admin_escritorio(request.user),
        "item_ativo": "agenda",
        "next_url": request.get_full_path(),
    }

    if visao == "calendario":
        contexto.update(_contexto_calendario(request, escopo))
        return render(request, "agenda/calendario.html", contexto)

    filtro = _normalizar_filtro(request.GET.get("filtro", "proximos_7"))
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

    compromissos = list(compromissos.order_by("data_hora_inicio"))
    _anexar_minha_participacao(request, compromissos)

    contexto.update({"compromissos": compromissos, "filtro": filtro})
    return render(request, "agenda/lista.html", contexto)


@login_required
def cancelados(request):
    """
    Consulta-only, sem reativar (decisão da spec): compromisso cancelado
    fica disponível aqui por até 7 dias após o cancelamento — depois
    disso o job `expurgar_compromissos_cancelados` o remove.
    """
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    compromissos = _aplicar_escopo(
        Compromisso.objects.select_related("responsavel", "processo", "cliente").filter(
            status="cancelado"
        ),
        request,
        escopo,
    ).prefetch_related("participacoes__usuario").order_by("-cancelado_em")

    return render(request, "agenda/cancelados.html", {
        "compromissos": compromissos,
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "item_ativo": "agenda",
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        responsavel_original = compromisso.responsavel
        data_anterior = compromisso.data_hora_inicio
        form = CompromissoForm(request.POST, instance=compromisso)
        if form.is_valid():
            status_original = compromisso.status
            compromisso = form.save(commit=False)
            compromisso.responsavel = responsavel_original
            compromisso.status = status_original
            if not compromisso.cliente and compromisso.processo and compromisso.processo.cliente:
                compromisso.cliente = compromisso.processo.cliente
            compromisso.save()
            if compromisso.data_hora_inicio != data_anterior:
                _resetar_confirmacoes_por_reagendamento(compromisso)
            return redirect("agenda:index")
    else:
        form = CompromissoForm(instance=compromisso)
    return render(request, "agenda/form.html", {
        "form": form,
        "modo": "editar",
        "compromisso": compromisso,
        "participacoes": compromisso.participacoes.select_related("usuario"),
        "form_participante": AdicionarParticipanteForm(
            usuarios_queryset=_usuarios_elegiveis_para_participante(compromisso)
        ),
        "item_ativo": "agenda",
    })


@login_required
def processos_por_cliente(request):
    """Processos do cliente informado, para o filtro dinâmico dos
    formulários de criação/edição de compromissos."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    processos = processos_do_cliente(request.GET.get("cliente"))
    return JsonResponse({
        "processos": [{"id": p.id, "label": str(p)} for p in processos],
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
            for usuario in form.cleaned_data.get("participantes") or []:
                if usuario.pk == compromisso.responsavel_id:
                    continue
                participacao = ParticipanteCompromisso.objects.create(
                    compromisso=compromisso, usuario=usuario
                )
                _notificar_convite(participacao)
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
    if request.method == "POST" and compromisso.status != "cancelado":
        compromisso.status = "cancelado"
        compromisso.cancelado_em = timezone.now()
        compromisso.save(update_fields=["status", "cancelado_em"])
        _notificar_cancelamento(compromisso)
    return _redirect_seguro(request)


@login_required
def reabrir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        compromisso.status = "agendado"
        compromisso.cancelado_em = None
        compromisso.save(update_fields=["status", "cancelado_em"])
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


@login_required
def adicionar_participante(request, pk):
    """Gerenciar participantes reaproveita a autorização de edição do
    compromisso já existente — sem habilitação granular própria."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = AdicionarParticipanteForm(
            request.POST,
            usuarios_queryset=_usuarios_elegiveis_para_participante(compromisso),
        )
        if not form.is_valid():
            raise Http404
        participacao = ParticipanteCompromisso.objects.create(
            compromisso=compromisso, usuario=form.cleaned_data["usuario"]
        )
        _notificar_convite(participacao)
    return redirect("agenda:editar", pk=pk)


@login_required
def remover_participante(request, pk, usuario_pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        participacao = get_object_or_404(
            ParticipanteCompromisso, compromisso=compromisso, usuario_id=usuario_pk
        )
        participacao.delete()
    return redirect("agenda:editar", pk=pk)


@login_required
def confirmar_presenca(request, pk):
    """Confirmar/recusar presença é ação do próprio participante sobre o
    próprio registro — não passa pela autorização de edição do
    compromisso, só pela autorização de módulo."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    participacao = get_object_or_404(
        ParticipanteCompromisso, compromisso_id=pk, usuario=request.user
    )
    if request.method == "POST":
        participacao.status = ParticipanteCompromisso.STATUS_CONFIRMADO
        participacao.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def recusar_presenca(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    participacao = get_object_or_404(
        ParticipanteCompromisso, compromisso_id=pk, usuario=request.user
    )
    if request.method == "POST":
        participacao.status = ParticipanteCompromisso.STATUS_RECUSADO
        participacao.save(update_fields=["status"])
    return _redirect_seguro(request)
