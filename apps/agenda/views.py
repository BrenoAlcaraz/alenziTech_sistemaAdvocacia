from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.delegacao import (
    aceitar_convite,
    criar_convite_delegacao,
    delegacao_exige_convite,
    recusar_convite,
)
from apps.accounts.models import ConviteDelegacao
from apps.accounts.permissoes import tem_permissao_modulo, tem_habilitacao, nivel_acesso_modulo
from apps.accounts.permissoes_constants import (
    MODULO_AGENDA,
    MODULO_GERIR,
    HAB_AGENDA_CRIAR_PARA_OUTROS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.atividade.services import registrar_atividade
from apps.notificacoes.models import Notificacao
from apps.processos.services import processos_do_cliente, rotulo_processo

from apps.accounts.equipe_atalho import SelecionarMembrosEquipeForm, dados_para_js

from .models import Compromisso, ParticipanteCompromisso
from .forms import AdicionarParticipanteForm, CompromissoForm


FILTROS_VALIDOS = {"hoje", "proximos_7", "vencidos", "todos"}
_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}
VISOES_VALIDAS = {"lista", "calendario"}
ABAS_VALIDAS = {"novidades", "terceiro", "delegados", "convites", "outros"}
_CONVITES_QUE_OCULTAM = [ConviteDelegacao.STATUS_PENDENTE, ConviteDelegacao.STATUS_RECUSADO]


def _excluir_ocultos_por_convite(qs):
    """Remove compromisso com convite de delegação pendente/recusado —
    ainda não é (ou nunca será) atribuição ativa do responsável (specs/
    delegacao-por-convite-agenda-tarefas.md). Compromisso sem convite
    (direto) ou com convite aceito não é afetado."""
    return qs.exclude(convite_delegacao__status__in=_CONVITES_QUE_OCULTAM)

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


def _normalizar_aba(request, usuario_filtro):
    """
    Sub-aba ativa da faixa abaixo da lista/calendário. Quem chega via
    `?usuario=` (seletor de colega da aba "Agenda de outros usuários")
    reabre já naquela aba; senão respeita `?aba=` se válido; senão
    "Novos na sua agenda" é o padrão.
    """
    if usuario_filtro is not None:
        return "outros"
    aba = request.GET.get("aba")
    if aba in ABAS_VALIDAS:
        return aba
    return "novidades"


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

    Atalho do Painel do gestor: com `?usuario=` e permissão de
    `gerir`/Admin, ignora o escopo do usuário logado e mostra a agenda
    do usuário filtrado (specs/dashboard-painel-do-gestor.md).
    """
    usuario_filtro_id = request.GET.get("usuario")
    if usuario_filtro_id and _pode_ver_outro_usuario(request.user):
        return qs.filter(responsavel_id=usuario_filtro_id)
    if escopo == NIVEL_SOMENTE_SEUS:
        qs = qs.filter(
            Q(responsavel=request.user) | Q(participacoes__usuario=request.user)
        ).distinct()
        qs = _excluir_ocultos_por_convite(qs)
    return qs


def _compromissos_no_escopo(request, escopo):
    """
    QuerySet de LEITURA (index), restrito pelo escopo efetivo.

    Compromisso cancelado nunca aparece na grade operacional padrão —
    só na seção "Cancelados" (ver `cancelados`).
    """
    qs = Compromisso.objects.select_related(
        "responsavel", "processo", "cliente", "convite_delegacao"
    ).exclude(status="cancelado")
    return _aplicar_escopo(qs, request, escopo)


def _pode_ver_outro_usuario(user):
    """Painel do gestor: só quem tem `gerir`/Admin pode olhar a agenda de
    um usuário específico via ?usuario= — para qualquer outra pessoa o
    parâmetro é ignorado (specs/dashboard-painel-do-gestor.md)."""
    return usuario_admin_escritorio(user) or tem_permissao_modulo(user, MODULO_GERIR)


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
        qs = _excluir_ocultos_por_convite(qs)
    return qs


def _pode_criar_para_outros(request):
    return usuario_admin_escritorio(request.user) or tem_habilitacao(
        request.user, MODULO_AGENDA, HAB_AGENDA_CRIAR_PARA_OUTROS
    )


def _compromissos_novidades(request):
    """
    Sub-aba "Novos na sua agenda (últimas 24h)": qualquer compromisso
    que entrou na agenda do usuário nas últimas 24h, de qualquer
    origem — responsável desde a criação, ou convidado como
    participante nas últimas 24h (o que for mais recente para cada
    caso). Sempre visível, sem checagem de habilitação.
    """
    limite = timezone.now() - timedelta(hours=24)
    return _excluir_ocultos_por_convite(
        Compromisso.objects.select_related("responsavel", "processo", "cliente")
        .exclude(status="cancelado")
        .filter(
            Q(responsavel=request.user, criado_em__gte=limite)
            | Q(participacoes__usuario=request.user, participacoes__criado_em__gte=limite)
        )
        .distinct()
    ).order_by("-criado_em")


def _compromissos_adicionado_por_terceiro(request):
    """
    Sub-aba "Adicionado por terceiro": só compromissos em que o usuário
    é responsável, mas quem criou foi outra pessoa. Sempre visível, sem
    checagem de habilitação.
    """
    return _excluir_ocultos_por_convite(
        Compromisso.objects.select_related("responsavel", "processo", "cliente")
        .exclude(status="cancelado")
        .filter(responsavel=request.user)
        .exclude(criado_por__isnull=True)
        .exclude(criado_por=request.user)
    ).order_by("-criado_em")


def _compromissos_delegados_por_mim(request):
    """
    Sub-aba "Delegados por mim": compromissos que o próprio usuário
    colocou na agenda de outra pessoa — inclui qualquer status
    (agendado/concluído/cancelado), diferente da grade operacional
    padrão. Só para quem tem a habilitação de criar para outros.
    """
    return (
        Compromisso.objects.select_related("responsavel", "processo", "cliente", "convite_delegacao")
        .filter(criado_por=request.user)
        .exclude(responsavel=request.user)
        .order_by("-criado_em")
    )


def _convites_pendentes_do_usuario(request):
    """Convites de delegação de Compromisso pendentes para o usuário
    logado responder (specs/delegacao-por-convite-agenda-tarefas.md) —
    qualquer usuário pode ser destinatário, sem exigir habilitação."""
    return (
        ConviteDelegacao.objects.filter(
            destinatario=request.user,
            status=ConviteDelegacao.STATUS_PENDENTE,
            content_type=ContentType.objects.get_for_model(Compromisso),
        )
        .select_related("delegante")
        .order_by("-criado_em")
    )


def _usuarios_participantes_possiveis(compromisso):
    """Universo de quem pode participar (ativos, exceto o responsável),
    inclusive quem já participa — a lista de conferência mostra estes
    como já presentes."""
    return User.objects.filter(is_active=True).exclude(
        pk=compromisso.responsavel_id
    ).order_by("first_name", "username")


def _usuarios_elegiveis_para_participante(compromisso):
    """Usuários que ainda podem ser convidados: mesmo universo do
    responsável, exceto o próprio responsável e quem já participa."""
    return _usuarios_participantes_possiveis(compromisso).exclude(
        pk__in=compromisso.participacoes.values("usuario_id")
    )


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
    """
    Lista e calendário convivem na mesma página — as duas visões são
    sempre montadas no mesmo request e alternadas no cliente (JS,
    `data-view-toggle`/`data-view`), sem recarregar a página nem perder
    filtro/data selecionada. `?visao=` só decide qual delas nasce
    visível (deep link e reload de filtro/navegação de mês).
    """
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    visao = _normalizar_visao(request.GET.get("visao"))
    pode_ver_outro_usuario = _pode_ver_outro_usuario(request.user)
    pode_criar_para_outros = _pode_criar_para_outros(request)

    usuario_filtro = None
    usuario_filtro_id = request.GET.get("usuario")
    if usuario_filtro_id and pode_ver_outro_usuario:
        usuario_filtro = get_object_or_404(User, pk=usuario_filtro_id)

    contexto = {
        "visao": visao,
        "aba_ativa": _normalizar_aba(request, usuario_filtro),
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "usuario_filtro": usuario_filtro,
        "is_admin": usuario_admin_escritorio(request.user),
        "item_ativo": "agenda",
        "next_url": request.get_full_path(),
        "pode_ver_outro_usuario": pode_ver_outro_usuario,
        "pode_criar_para_outros": pode_criar_para_outros,
    }

    # ── Bloco Lista ──────────────────────────────────────────────────
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

    # ── Bloco Calendário ─────────────────────────────────────────────
    contexto.update(_contexto_calendario(request, escopo))

    # ── Faixa de sub-abas ────────────────────────────────────────────
    novidades = list(_compromissos_novidades(request))
    terceiro = list(_compromissos_adicionado_por_terceiro(request))
    _anexar_minha_participacao(request, novidades)
    _anexar_minha_participacao(request, terceiro)
    contexto.update({
        "compromissos_novidades": novidades,
        "compromissos_terceiro": terceiro,
        "convites_recebidos": list(_convites_pendentes_do_usuario(request)),
    })

    if pode_criar_para_outros:
        delegados = list(_compromissos_delegados_por_mim(request))
        contexto["compromissos_delegados"] = delegados

    if pode_ver_outro_usuario:
        contexto["usuarios_outros"] = User.objects.filter(is_active=True).order_by(
            "first_name", "username"
        )

    return render(request, "agenda/index.html", contexto)


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
            if not compromisso.cliente and compromisso.processo:
                compromisso.cliente = compromisso.processo.clientes.first()
            compromisso.save()
            if compromisso.data_hora_inicio != data_anterior:
                _resetar_confirmacoes_por_reagendamento(compromisso)
            registrar_atividade(
                request.user, "compromisso_editado", f"Editou o compromisso {compromisso.titulo}",
                processo=compromisso.processo,
            )
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
        "equipe_atalho": dados_para_js(
            _usuarios_participantes_possiveis(compromisso),
            presentes=[*compromisso.participacoes.values_list("usuario_id", flat=True)],
        ),
        "item_ativo": "agenda",
        "pode_ver_disponibilidade": _pode_ver_outro_usuario(request.user),
    })


@login_required
def convite_responder(request, pk):
    """Aceitar/recusar convite de delegação — sub-aba "Convites
    recebidos" do index (specs/delegacao-por-convite-agenda-tarefas.md).
    Sem página própria: mesma sub-aba dos demais estados de Agenda."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    convite = get_object_or_404(
        ConviteDelegacao,
        pk=pk,
        destinatario=request.user,
        status=ConviteDelegacao.STATUS_PENDENTE,
        content_type=ContentType.objects.get_for_model(Compromisso),
    )
    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "aceitar":
            aceitar_convite(convite, request.user)
        elif acao == "recusar":
            recusar_convite(convite, request.user, justificativa=request.POST.get("justificativa", ""))
        else:
            raise Http404
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("agenda:index")


@login_required
def processos_por_cliente(request):
    """Processos do cliente informado, para o filtro dinâmico dos
    formulários de criação/edição de compromissos."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    processos = processos_do_cliente(request.GET.get("cliente"))
    return JsonResponse({
        "processos": [{"id": p.id, "label": rotulo_processo(p)} for p in processos],
    })


@login_required
def disponibilidade_convidado(request):
    """
    Compromissos que o convidado já tem no mesmo horário — checagem
    informativa ao adicionar participante, nunca bloqueia a criação.
    Mesma condição de habilitação da sub-aba "Agenda de outros
    usuários" (Permissão "Agenda"/"Todos" + Gerir).
    """
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    if not _pode_ver_outro_usuario(request.user):
        raise PermissionDenied

    usuario_id = request.GET.get("usuario")
    inicio = parse_datetime(request.GET.get("inicio") or "")
    if not usuario_id or inicio is None:
        return JsonResponse({"compromissos": []})
    if timezone.is_naive(inicio):
        inicio = timezone.make_aware(inicio)

    fim = parse_datetime(request.GET.get("fim") or "") or inicio
    if timezone.is_naive(fim):
        fim = timezone.make_aware(fim)

    candidatos = Compromisso.objects.filter(
        responsavel_id=usuario_id,
        data_hora_inicio__date=inicio.date(),
    ).exclude(status="cancelado").order_by("data_hora_inicio")

    conflitos = [
        c for c in candidatos
        if c.data_hora_inicio <= fim and inicio <= (c.data_hora_fim or c.data_hora_inicio)
    ]

    return JsonResponse({
        "compromissos": [
            {"titulo": c.titulo, "horario": _horario_curto(c)} for c in conflitos
        ],
    })


def _usuario_travado(request):
    """
    Usuário travado no campo Responsável quando o formulário é aberto a
    partir de "+ Novo compromisso nesta agenda" (sub-aba "Agenda de
    outros usuários"). `disabled=True` no form faz o Django ignorar
    qualquer valor de `responsavel` vindo do POST e usar sempre o
    `initial` — por isso o travamento é seguro mesmo que o campo seja
    adulterado no HTML.
    """
    para_usuario_id = request.POST.get("para_usuario") or request.GET.get("para_usuario")
    if not para_usuario_id:
        return None
    return get_object_or_404(User, pk=para_usuario_id, is_active=True)


@login_required
def form_compromisso(request):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    usuario_travado = _usuario_travado(request)

    if request.method == "POST":
        form = CompromissoForm(request.POST)
        if usuario_travado:
            form.fields["responsavel"].disabled = True
            form.fields["responsavel"].initial = usuario_travado
        if form.is_valid():
            compromisso = form.save(commit=False)
            if not compromisso.responsavel:
                compromisso.responsavel = request.user
            if compromisso.responsavel != request.user and not _pode_criar_para_outros(request):
                raise PermissionDenied
            compromisso.status = "agendado"
            compromisso.criado_por = request.user
            if not compromisso.cliente and compromisso.processo:
                compromisso.cliente = compromisso.processo.clientes.first()
            compromisso.save()
            for usuario in form.cleaned_data.get("participantes") or []:
                if usuario.pk == compromisso.responsavel_id:
                    continue
                participacao = ParticipanteCompromisso.objects.create(
                    compromisso=compromisso, usuario=usuario
                )
                _notificar_convite(participacao)
            # Delegação por convite (specs/delegacao-por-convite-agenda-
            # tarefas.md): só se aplica quando o responsável é outra
            # pessoa, nunca em auto-atribuição.
            if compromisso.responsavel_id != request.user.pk and delegacao_exige_convite(
                request.user, compromisso.responsavel
            ):
                convite = criar_convite_delegacao(request.user, compromisso.responsavel, compromisso)
                compromisso.convite_delegacao = convite
                compromisso.save(update_fields=["convite_delegacao"])
            registrar_atividade(
                request.user, "compromisso_criado", f"Criou o compromisso {compromisso.titulo}",
                processo=compromisso.processo,
            )
            return redirect("agenda:index")
    else:
        form = CompromissoForm(initial={"responsavel": usuario_travado or request.user})
        if usuario_travado:
            form.fields["responsavel"].disabled = True
    return render(request, "agenda/form.html", {
        "form": form,
        "item_ativo": "agenda",
        "usuario_travado": usuario_travado,
        "equipe_atalho": dados_para_js(form.fields["participantes"].queryset),
        "pode_ver_disponibilidade": _pode_ver_outro_usuario(request.user),
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
        registrar_atividade(
            request.user, "compromisso_concluido", f"Concluiu o compromisso {compromisso.titulo}",
            processo=compromisso.processo,
        )
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
        registrar_atividade(
            request.user, "compromisso_cancelado", f"Cancelou o compromisso {compromisso.titulo}",
            processo=compromisso.processo,
        )
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
        registrar_atividade(
            request.user, "compromisso_reaberto", f"Reabriu o compromisso {compromisso.titulo}",
            processo=compromisso.processo,
        )
    return _redirect_seguro(request)


@login_required
def excluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        titulo = compromisso.titulo
        processo = compromisso.processo
        compromisso.delete()
        registrar_atividade(
            request.user, "compromisso_excluido", f"Excluiu o compromisso {titulo}",
            processo=processo,
        )
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
        registrar_atividade(
            request.user, "compromisso_participante_adicionado",
            f"Adicionou {participacao.usuario.get_full_name() or participacao.usuario.username} "
            f"como participante do compromisso {compromisso.titulo}",
            processo=compromisso.processo,
        )
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
        usuario = participacao.usuario
        participacao.delete()
        registrar_atividade(
            request.user, "compromisso_participante_removido",
            f"Removeu {usuario.get_full_name() or usuario.username} dos participantes do "
            f"compromisso {compromisso.titulo}",
            processo=compromisso.processo,
        )
    return redirect("agenda:editar", pk=pk)


@login_required
def adicionar_equipe_participante(request, pk):
    """Equipe como atalho de seleção (PDR-0028): a lista de conferência
    envia só pessoas; cada uma passa pela confirmação de presença normal
    (PDR-0020). Mesma autorização de `adicionar_participante`."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = SelecionarMembrosEquipeForm(
            request.POST, usuarios_elegiveis=_usuarios_participantes_possiveis(compromisso)
        )
        if not form.is_valid():
            raise Http404
        for usuario in form.cleaned_data["usuarios"]:
            participacao, criada = ParticipanteCompromisso.objects.get_or_create(
                compromisso=compromisso, usuario=usuario
            )
            if criada:
                _notificar_convite(participacao)
                registrar_atividade(
                    request.user, "compromisso_participante_adicionado",
                    f"Adicionou {usuario.get_full_name() or usuario.username} como participante "
                    f"do compromisso {compromisso.titulo}",
                    processo=compromisso.processo,
                )
    return redirect("agenda:editar", pk=pk)


@login_required
def adicionar_todos_participantes(request, pk):
    """Convida todos os usuários ativos ainda não convidados; cada um passa
    pela confirmação de presença normal (PDR-0020). Mesma autorização de
    `adicionar_participante`."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    compromisso = get_object_or_404(_compromissos_mutaveis(request), pk=pk)
    if request.method == "POST":
        for usuario in _usuarios_elegiveis_para_participante(compromisso):
            participacao = ParticipanteCompromisso.objects.create(
                compromisso=compromisso, usuario=usuario
            )
            _notificar_convite(participacao)
            registrar_atividade(
                request.user, "compromisso_participante_adicionado",
                f"Adicionou {usuario.get_full_name() or usuario.username} como participante "
                f"do compromisso {compromisso.titulo}",
                processo=compromisso.processo,
            )
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
