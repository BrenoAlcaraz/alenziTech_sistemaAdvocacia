from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q
from django.db.models.functions import Coalesce, TruncDate
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode

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
    HAB_AGENDA_ATRIBUIR_OUTROS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.atividade.services import registrar_atividade
from apps.notificacoes.models import Notificacao
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.processos.services import processos_do_cliente, rotulo_processo

from apps.accounts.equipe_atalho import SelecionarMembrosEquipeForm, dados_para_js

from . import visoes
from .models import (
    NATUREZA_AFAZER,
    NATUREZA_EVENTO,
    STATUS_A_FAZER,
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_EM_ANDAMENTO,
    TIPOS_AFAZER,
    TIPOS_EVENTO,
    ItemAgenda,
    ParticipanteItemAgenda,
    ReatribuicaoItemAgenda,
)
from .forms import AdicionarParticipanteForm, ItemAgendaForm, ReatribuirForm


_ESCOPOS_VALIDOS = {NIVEL_SOMENTE_SEUS, NIVEL_TODOS}
VISOES = [("dia", "Meu dia"), ("calendario", "Calendário"), ("kanban", "Kanban")]
VISAO_PADRAO = "dia"
ORIGENS_VALIDAS = {"manual", "processo"}
# Parâmetros da barra de filtros — os únicos repassados ao alternar
# visão, navegar no calendário ou ordenar o kanban.
PARAMETROS_FILTRO = ("tipo", "natureza", "escopo", "usuario", "delegados", "origem", "processo", "cliente", "ordem")
_CONVITES_QUE_OCULTAM = [ConviteDelegacao.STATUS_PENDENTE, ConviteDelegacao.STATUS_RECUSADO]


# Tipos do log de atividade herdados de Tarefas (afazer) e Compromisso
# (evento); reatribuir e iniciar só existiam em Tarefas.
_TIPOS_ATIVIDADE = {
    "criado": ("tarefa_criada", "compromisso_criado"),
    "editado": ("tarefa_editada", "compromisso_editado"),
    "concluido": ("tarefa_concluida", "compromisso_concluido"),
    "reaberto": ("tarefa_reaberta", "compromisso_reaberto"),
    "cancelado": ("tarefa_cancelada", "compromisso_cancelado"),
    "excluido": ("tarefa_excluida", "compromisso_excluido"),
    "participante_adicionado": ("tarefa_participante_adicionado", "compromisso_participante_adicionado"),
    "participante_removido": ("tarefa_participante_removido", "compromisso_participante_removido"),
    "iniciado": ("tarefa_iniciada", "tarefa_iniciada"),
    "reatribuido": ("tarefa_reatribuida", "tarefa_reatribuida"),
}


def _tipo_atividade(item, acao):
    afazer, evento = _TIPOS_ATIVIDADE[acao]
    return evento if item.eh_evento else afazer


def _excluir_ocultos_por_convite(qs):
    """Remove item com convite de delegação pendente/recusado — ainda não
    é (ou nunca será) atribuição ativa do responsável (PDR-0033). Item
    sem convite (direto) ou com convite aceito não é afetado."""
    return qs.exclude(convite_delegacao__status__in=_CONVITES_QUE_OCULTAM)


def _redirect_seguro(request):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("agenda:index")


def _normalizar_visao(visao):
    if visao in dict(VISOES):
        return visao
    return VISAO_PADRAO


def _resolver_escopo(request):
    """
    Resolve o escopo efetivo de LEITURA (somente_seus/todos): parâmetro
    AUSENTE usa o nível máximo do usuário como padrão; parâmetro PRESENTE
    com valor inválido (incluindo string vazia) ou acima do nível máximo
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
    Em `somente_seus`, restringe a item onde o usuário é responsável OU
    participante (qualquer status de confirmação) — participante nunca é
    responsável, só ganha visibilidade.

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


def _com_data_referencia(qs):
    """`data_ref`: dia em que o item cai na agenda — início (evento), data
    para fazer ou, sem ela, data fatal (afazer). Nulo em afazer sem data,
    que só aparece sem filtro de data."""
    return qs.annotate(
        data_ref=Coalesce(TruncDate("data_hora_inicio"), "data_para_fazer", "data_fatal")
    )


def _ordenar_por_data(qs):
    return qs.order_by(F("data_ref").asc(nulls_last=True), "data_hora_inicio", "hora_para_fazer")


def _ler_filtros(request):
    """Filtros da barra única, já normalizados — valor inválido vira
    "sem filtro". Escopo e pessoa têm resolução própria (autorização)."""
    tipos = dict(ItemAgenda.TIPO_CHOICES)
    tipo = request.GET.get("tipo")
    natureza = request.GET.get("natureza")
    origem = request.GET.get("origem")
    ordem = request.GET.get("ordem")
    return {
        "tipo": tipo if tipo in tipos else "",
        "natureza": natureza if natureza in (NATUREZA_AFAZER, NATUREZA_EVENTO) else "",
        "origem": origem if origem in ORIGENS_VALIDAS else "",
        "delegados": request.GET.get("delegados") == "1",
        "processo": _parse_int(request.GET.get("processo"), minimo=1),
        "cliente": _parse_int(request.GET.get("cliente"), minimo=1),
        "ordem": ordem if ordem in dict(visoes.ORDENS_KANBAN) else visoes.ORDEM_KANBAN_PADRAO,
    }


def _itens_visiveis(request, escopo, usuario_filtro, delegados):
    """
    Universo de LEITURA da tela, antes dos filtros que só estreitam.

    Item cancelado nunca aparece nas visões operacionais — só em
    "Cancelados". "Delegados por mim" mostra o que o próprio usuário
    atribuiu a outra pessoa, inclusive com convite ainda pendente ou
    recusado (é quem acompanha a resposta), sem depender do escopo.
    """
    qs = ItemAgenda.objects.select_related(
        "responsavel", "processo", "cliente", "convite_delegacao"
    ).exclude(status=STATUS_CANCELADO)
    if delegados:
        qs = qs.filter(atribuidor=request.user).exclude(responsavel=request.user)
        if usuario_filtro:
            qs = qs.filter(responsavel=usuario_filtro)
        return qs
    return _aplicar_escopo(qs, request, escopo)


def _aplicar_filtros(qs, filtros):
    """Tipo, natureza, origem, processo e cliente só restringem o que o
    escopo já mostra, nunca ampliam."""
    if filtros["tipo"]:
        qs = qs.filter(tipo=filtros["tipo"])
    if filtros["natureza"] == NATUREZA_AFAZER:
        qs = qs.filter(tipo__in=TIPOS_AFAZER)
    elif filtros["natureza"] == NATUREZA_EVENTO:
        qs = qs.filter(tipo__in=TIPOS_EVENTO)
    if filtros["origem"] == "processo":
        qs = qs.filter(movimentacao_origem__isnull=False)
    elif filtros["origem"] == "manual":
        qs = qs.filter(movimentacao_origem__isnull=True)
    if filtros["processo"]:
        qs = qs.filter(processo_id=filtros["processo"])
    if filtros["cliente"]:
        qs = qs.filter(cliente_id=filtros["cliente"])
    return qs


def _opcoes_de_vinculo(visiveis):
    """Processos e clientes oferecidos no filtro: só os que aparecem em
    itens que o usuário já enxerga — o seletor não expõe o cadastro."""
    return (
        list(Processo.objects.filter(pk__in=visiveis.values("processo_id")).order_by("titulo")),
        list(Cliente.objects.filter(pk__in=visiveis.values("cliente_id")).order_by("nome_razao_social")),
    )


def _query_dos_filtros(request):
    """Querystring só com os filtros ativos, para os links que trocam de
    visão/mês/dia sem perder a barra de filtros."""
    return urlencode([
        (nome, request.GET[nome]) for nome in PARAMETROS_FILTRO if request.GET.get(nome)
    ])


def _pode_ver_outro_usuario(user):
    """Painel do gestor: só quem tem `gerir`/Admin pode olhar a agenda de
    um usuário específico via ?usuario= — para qualquer outra pessoa o
    parâmetro é ignorado (specs/dashboard-painel-do-gestor.md)."""
    return usuario_admin_escritorio(user) or tem_permissao_modulo(user, MODULO_GERIR)


def _itens_mutaveis(request):
    """
    QuerySet usado para mutação (editar/status/reatribuir/excluir/
    participantes).

    "Todos" é escopo de visualização, não autorização de mutação sobre
    qualquer item: um usuário não-admin só muta item da própria
    responsabilidade, mesmo com nível máximo `todos`. Só o Administrador
    do escritório alcança qualquer item do tenant para mutação —
    inclusive um item ainda oculto por convite de delegação.
    """
    qs = ItemAgenda.objects.all()
    if not usuario_admin_escritorio(request.user):
        qs = qs.filter(responsavel=request.user)
        qs = _excluir_ocultos_por_convite(qs)
    return qs


def _pode_atribuir_a_outros(request):
    return usuario_admin_escritorio(request.user) or tem_habilitacao(
        request.user, MODULO_AGENDA, HAB_AGENDA_ATRIBUIR_OUTROS
    )


def _convites_pendentes_do_usuario(request):
    """Convites de delegação pendentes para o usuário logado responder
    (PDR-0033) — qualquer usuário pode ser destinatário, sem exigir
    habilitação."""
    return (
        ConviteDelegacao.objects.filter(
            destinatario=request.user,
            status=ConviteDelegacao.STATUS_PENDENTE,
            content_type=ContentType.objects.get_for_model(ItemAgenda),
        )
        .select_related("delegante")
        .order_by("-criado_em")
    )


def _usuarios_participantes_possiveis(item):
    """Universo de quem pode participar (ativos, exceto o responsável),
    inclusive quem já participa — a lista de conferência mostra estes
    como já presentes."""
    return User.objects.filter(is_active=True).exclude(
        pk=item.responsavel_id
    ).order_by("first_name", "username")


def _usuarios_elegiveis_para_participante(item):
    """Usuários que ainda podem ser convidados: mesmo universo do
    responsável, exceto o próprio responsável e quem já participa."""
    return _usuarios_participantes_possiveis(item).exclude(
        pk__in=item.participacoes.values("usuario_id")
    )


def _quando(item):
    """Data/hora curta do item para as notificações."""
    if item.eh_evento:
        return timezone.localtime(item.data_hora_inicio).strftime("%d/%m %H:%M")
    data = item.data_para_fazer or item.data_fatal
    return data.strftime("%d/%m") if data else "sem data"


def _adicionar_participante(item, usuario):
    """Participante sempre ganha visibilidade; só em Evento é convidado a
    confirmar presença (PDR-0020)."""
    participacao = ParticipanteItemAgenda.objects.create(item=item, usuario=usuario)
    if item.eh_evento:
        Notificacao.objects.create(
            destinatario=usuario,
            mensagem=(
                f'Você foi convidado para "{item.titulo}" '
                f"em {_quando(item)} — confirme sua presença."
            ),
        )
    return participacao


def _resetar_confirmacoes_por_reagendamento(item):
    """
    Volta para pendente a confirmação de todo participante já confirmado
    e notifica cada um — chamado quando `data_hora_inicio` muda numa
    edição (o item já reflete a nova data neste ponto).
    """
    confirmados = list(
        item.participacoes.filter(
            status=ParticipanteItemAgenda.STATUS_CONFIRMADO
        ).select_related("usuario")
    )
    for participacao in confirmados:
        Notificacao.objects.create(
            destinatario=participacao.usuario,
            mensagem=(
                f'"{item.titulo}" foi reagendado para '
                f"{_quando(item)} — confirme sua presença novamente."
            ),
        )
    item.participacoes.filter(
        pk__in=[p.pk for p in confirmados]
    ).update(status=ParticipanteItemAgenda.STATUS_PENDENTE, lembrete_enviado=False)


def _notificar_cancelamento(item):
    """Notificação distinta de convite/lembrete — responsável e todos os
    participantes, independente do status de confirmação de cada um."""
    mensagem = f'{item.get_tipo_display()} cancelado: "{item.titulo}" em {_quando(item)}'
    destinatarios = list(
        item.participacoes.values_list("usuario_id", flat=True)
    )
    if item.responsavel_id:
        destinatarios.append(item.responsavel_id)
    for destinatario_id in destinatarios:
        Notificacao.objects.create(destinatario_id=destinatario_id, mensagem=mensagem)


def _anexar_minha_participacao(request, itens):
    participacoes_usuario = {
        p.item_id: p
        for p in ParticipanteItemAgenda.objects.filter(
            item_id__in=[c.pk for c in itens], usuario=request.user
        )
    }
    for item in itens:
        item.minha_participacao = participacoes_usuario.get(item.pk)


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


def _resolver_dia_selecionado(request, ano, mes, dias_no_mes, hoje):
    dia = _parse_int(request.GET.get("dia"), minimo=1, maximo=dias_no_mes)
    if dia:
        return dia
    if ano == hoje.year and mes == hoje.month:
        return hoje.day
    return 1


@login_required
def index(request):
    """
    Tela única da Agenda Jurídica. Meu dia, Calendário e Kanban saem da
    mesma lista filtrada, montadas no mesmo request e alternadas no
    cliente (`data-view-toggle`/`data-view`) sem recarregar nem perder
    filtros; `?visao=` só decide qual nasce visível.
    """
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    pode_ver_outro_usuario = _pode_ver_outro_usuario(request.user)
    pode_atribuir_a_outros = _pode_atribuir_a_outros(request)

    usuario_filtro = None
    usuario_filtro_id = request.GET.get("usuario")
    if usuario_filtro_id and pode_ver_outro_usuario:
        usuario_filtro = get_object_or_404(User, pk=usuario_filtro_id)

    filtros = _ler_filtros(request)
    visiveis = _itens_visiveis(request, escopo, usuario_filtro, filtros["delegados"])
    itens = list(_ordenar_por_data(_com_data_referencia(_aplicar_filtros(visiveis, filtros))))
    _anexar_minha_participacao(request, itens)

    hoje = timezone.localdate()
    ano, mes = _resolver_mes_ano(request, hoje)
    _, dias_no_mes = visoes.grade_do_mes(ano, mes)
    dia = _resolver_dia_selecionado(request, ano, mes, dias_no_mes, hoje)
    processos_opcoes, clientes_opcoes = _opcoes_de_vinculo(visiveis)

    contexto = {
        "visao": _normalizar_visao(request.GET.get("visao")),
        "visoes_opcoes": VISOES,
        "filtros": filtros,
        "filtros_query": _query_dos_filtros(request),
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "usuario_filtro": usuario_filtro,
        "is_admin": usuario_admin_escritorio(request.user),
        "item_ativo": "agenda",
        "next_url": request.get_full_path(),
        "pode_ver_outro_usuario": pode_ver_outro_usuario,
        "pode_criar_para_outros": pode_atribuir_a_outros,
        "itens": itens,
        "grupos_dia": visoes.grupos_meu_dia(itens, hoje),
        "colunas_kanban": visoes.colunas_kanban(itens, filtros["ordem"]),
        "ordens_kanban": visoes.ORDENS_KANBAN,
        "legenda_tipos": visoes.legenda_tipos(),
        "tipos_afazer": [(t, r) for t, r in ItemAgenda.TIPO_CHOICES if t in TIPOS_AFAZER],
        "tipos_evento": [(t, r) for t, r in ItemAgenda.TIPO_CHOICES if t in TIPOS_EVENTO],
        "processos_opcoes": processos_opcoes,
        "clientes_opcoes": clientes_opcoes,
        # Filtro vindo de link ("ver todos" do processo/cliente) sem item
        # visível: mantém o valor selecionado sem revelar o cadastro.
        "processo_fora_das_opcoes": bool(filtros["processo"])
        and filtros["processo"] not in {p.pk for p in processos_opcoes},
        "cliente_fora_das_opcoes": bool(filtros["cliente"])
        and filtros["cliente"] not in {c.pk for c in clientes_opcoes},
        "convites_recebidos": list(_convites_pendentes_do_usuario(request)),
    }
    contexto.update(visoes.calendario(itens, ano, mes, dia, hoje))
    if pode_ver_outro_usuario:
        contexto["usuarios_outros"] = User.objects.filter(is_active=True).order_by(
            "first_name", "username"
        )
    return render(request, "agenda/index.html", contexto)


@login_required
def cancelados(request):
    """
    Consulta: item cancelado fica disponível aqui por até 7 dias após o
    cancelamento — depois disso o job `expurgar_compromissos_cancelados`
    o remove.
    """
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    escopo, escopo_maximo = _resolver_escopo(request)
    itens = _aplicar_escopo(
        ItemAgenda.objects.select_related("responsavel", "processo", "cliente").filter(
            status=STATUS_CANCELADO
        ),
        request,
        escopo,
    ).prefetch_related("participacoes__usuario").order_by("-cancelado_em")

    return render(request, "agenda/cancelados.html", {
        "compromissos": itens,
        "escopo_atual": escopo,
        "escopo_maximo": escopo_maximo,
        "item_ativo": "agenda",
    })


@login_required
def editar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        responsavel_original = item.responsavel
        status_original = item.status
        inicio_anterior = item.data_hora_inicio
        form = ItemAgendaForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save(commit=False)
            # Responsável e status mudam só por reatribuição e ações de
            # status, nunca por este formulário.
            item.responsavel = responsavel_original
            item.status = status_original
            if not item.cliente and item.processo:
                item.cliente = item.processo.clientes.first()
            item.save()
            if item.eh_evento and item.data_hora_inicio != inicio_anterior:
                _resetar_confirmacoes_por_reagendamento(item)
            registrar_atividade(
                request.user, _tipo_atividade(item, "editado"),
                f"Editou {item.get_tipo_display().lower()} {item.titulo}",
                processo=item.processo,
            )
            return redirect("agenda:index")
    else:
        form = ItemAgendaForm(instance=item)
    return render(request, "agenda/form.html", {
        "form": form,
        "modo": "editar",
        "compromisso": item,
        "participacoes": item.participacoes.select_related("usuario"),
        "form_participante": AdicionarParticipanteForm(
            usuarios_queryset=_usuarios_elegiveis_para_participante(item)
        ),
        "equipe_atalho": dados_para_js(
            _usuarios_participantes_possiveis(item),
            presentes=[*item.participacoes.values_list("usuario_id", flat=True)],
        ),
        "item_ativo": "agenda",
        "pode_ver_disponibilidade": _pode_ver_outro_usuario(request.user),
    })


@login_required
def convite_responder(request, pk):
    """Aceitar/recusar convite de delegação (PDR-0033) — sem página
    própria: responde a partir do index."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    convite = get_object_or_404(
        ConviteDelegacao,
        pk=pk,
        destinatario=request.user,
        status=ConviteDelegacao.STATUS_PENDENTE,
        content_type=ContentType.objects.get_for_model(ItemAgenda),
    )
    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "aceitar":
            aceitar_convite(convite, request.user)
        elif acao == "recusar":
            recusar_convite(convite, request.user, justificativa=request.POST.get("justificativa", ""))
        else:
            raise Http404
    return _redirect_seguro(request)


@login_required
def processos_por_cliente(request):
    """Processos do cliente informado, para o filtro dinâmico dos
    formulários de criação/edição de itens."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    processos = processos_do_cliente(request.GET.get("cliente"))
    return JsonResponse({
        "processos": [{"id": p.id, "label": rotulo_processo(p)} for p in processos],
    })


@login_required
def disponibilidade_convidado(request):
    """
    Eventos que o convidado já tem no mesmo horário — checagem
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

    candidatos = ItemAgenda.objects.filter(
        tipo__in=TIPOS_EVENTO,
        responsavel_id=usuario_id,
        data_hora_inicio__date=inicio.date(),
    ).exclude(status=STATUS_CANCELADO).order_by("data_hora_inicio")

    conflitos = [
        c for c in candidatos
        if c.data_hora_inicio <= fim and inicio <= (c.data_hora_fim or c.data_hora_inicio)
    ]

    return JsonResponse({
        "compromissos": [
            {"titulo": c.titulo, "horario": _quando(c)} for c in conflitos
        ],
    })


def _usuario_travado(request):
    """
    Usuário travado no campo Responsável quando o formulário é aberto a
    partir de "+ Novo nesta agenda" (sub-aba "Agenda de outros
    usuários"). `disabled=True` no form faz o Django ignorar qualquer
    valor de `responsavel` vindo do POST e usar sempre o `initial` — por
    isso o travamento é seguro mesmo que o campo seja adulterado no HTML.
    """
    para_usuario_id = request.POST.get("para_usuario") or request.GET.get("para_usuario")
    if not para_usuario_id:
        return None
    return get_object_or_404(User, pk=para_usuario_id, is_active=True)


@login_required
def novo(request):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    usuario_travado = _usuario_travado(request)

    if request.method == "POST":
        form = ItemAgendaForm(request.POST)
        if usuario_travado:
            form.fields["responsavel"].disabled = True
            form.fields["responsavel"].initial = usuario_travado
        if form.is_valid():
            item = form.save(commit=False)
            if not item.responsavel:
                item.responsavel = request.user
            if item.responsavel != request.user and not _pode_atribuir_a_outros(request):
                raise PermissionDenied
            item.status = STATUS_A_FAZER
            item.criado_por = request.user
            item.atribuidor = request.user
            item.atribuido_em = timezone.now()
            if not item.cliente and item.processo:
                item.cliente = item.processo.clientes.first()
            item.save()
            for usuario in form.cleaned_data.get("participantes") or []:
                if usuario.pk != item.responsavel_id:
                    _adicionar_participante(item, usuario)
            # Delegação por convite (PDR-0033): só se aplica quando o
            # responsável é outra pessoa, nunca em auto-atribuição.
            if item.responsavel_id != request.user.pk and delegacao_exige_convite(
                request.user, item.responsavel
            ):
                convite = criar_convite_delegacao(request.user, item.responsavel, item)
                item.convite_delegacao = convite
                item.save(update_fields=["convite_delegacao"])
            registrar_atividade(
                request.user, _tipo_atividade(item, "criado"),
                f"Criou {item.get_tipo_display().lower()} {item.titulo}",
                processo=item.processo,
            )
            return redirect("agenda:index")
    else:
        initial = {"responsavel": usuario_travado or request.user}
        # Atalhos do detalhe de Processo/Cliente: só pré-preenchem.
        for campo in ("tipo", "processo", "cliente"):
            if request.GET.get(campo):
                initial[campo] = request.GET[campo]
        form = ItemAgendaForm(initial=initial)
        if usuario_travado:
            form.fields["responsavel"].disabled = True
    return render(request, "agenda/form.html", {
        "form": form,
        "item_ativo": "agenda",
        "usuario_travado": usuario_travado,
        "equipe_atalho": dados_para_js(form.fields["participantes"].queryset),
        "pode_ver_disponibilidade": _pode_ver_outro_usuario(request.user),
    })


def _mudar_status(request, pk, novo_status, acao, verbo, *, queryset=None):
    """Troca de status comum a concluir/iniciar/reabrir — mesma regra de
    mutação (responsável ou Administrador)."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(queryset if queryset is not None else _itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        item.status = novo_status
        item.cancelado_em = None
        item.save(update_fields=["status", "cancelado_em"])
        registrar_atividade(
            request.user, _tipo_atividade(item, acao),
            f"{verbo} {item.get_tipo_display().lower()} {item.titulo}",
            processo=item.processo,
        )
    return item


@login_required
def concluir(request, pk):
    item = _mudar_status(request, pk, STATUS_CONCLUIDO, "concluido", "Concluiu")
    if request.method == "POST" and item.criado_por_id and item.criado_por_id != item.responsavel_id:
        Notificacao.objects.create(
            destinatario=item.criado_por,
            mensagem=f'{item.get_tipo_display()} concluído: "{item.titulo}"',
        )
    return _redirect_seguro(request)


@login_required
def iniciar(request, pk):
    """"Em andamento" só existe em Afazer."""
    _mudar_status(
        request, pk, STATUS_EM_ANDAMENTO, "iniciado", "Iniciou",
        queryset=_itens_mutaveis(request).filter(tipo__in=TIPOS_AFAZER),
    )
    return _redirect_seguro(request)


@login_required
def reabrir(request, pk):
    _mudar_status(request, pk, STATUS_A_FAZER, "reaberto", "Reabriu")
    return _redirect_seguro(request)


@login_required
def cancelar(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST" and item.status != STATUS_CANCELADO:
        item.status = STATUS_CANCELADO
        item.cancelado_em = timezone.now()
        item.save(update_fields=["status", "cancelado_em"])
        _notificar_cancelamento(item)
        registrar_atividade(
            request.user, _tipo_atividade(item, "cancelado"),
            f"Cancelou {item.get_tipo_display().lower()} {item.titulo}",
            processo=item.processo,
        )
    return _redirect_seguro(request)


@login_required
def excluir(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        descricao = f"{item.get_tipo_display().lower()} {item.titulo}"
        processo = item.processo
        tipo_atividade = _tipo_atividade(item, "excluido")
        item.delete()
        registrar_atividade(
            request.user, tipo_atividade, f"Excluiu {descricao}",
            processo=processo,
        )
    return _redirect_seguro(request)


@login_required
def reatribuir(request, pk):
    """Reatribuição com histórico, para qualquer item e sem convite (como
    em Tarefas); passar a outra pessoa exige "atribuir a outros"."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = ReatribuirForm(request.POST)
        if form.is_valid():
            novo_responsavel = form.cleaned_data["destinatario"]
            if novo_responsavel != request.user and not _pode_atribuir_a_outros(request):
                raise PermissionDenied
            ReatribuicaoItemAgenda.objects.create(
                item=item,
                responsavel_anterior=item.responsavel,
                responsavel_novo=novo_responsavel,
                autor=request.user,
            )
            item.responsavel = novo_responsavel
            item.atribuidor = request.user
            item.atribuido_em = timezone.now()
            item.save(update_fields=["responsavel", "atribuidor", "atribuido_em"])
            # O novo responsável não pode seguir como participante.
            item.participacoes.filter(usuario=novo_responsavel).delete()
            registrar_atividade(
                request.user, _tipo_atividade(item, "reatribuido"),
                f"Reatribuiu {item.get_tipo_display().lower()} {item.titulo} para "
                f"{novo_responsavel.get_full_name() or novo_responsavel.username}",
                processo=item.processo,
            )
            return _redirect_seguro(request)
    else:
        form = ReatribuirForm(initial={"destinatario": item.responsavel_id})
    return render(request, "agenda/reatribuir.html", {
        "form": form,
        "item": item,
        "reatribuicoes": item.reatribuicoes.select_related("responsavel_anterior", "responsavel_novo", "autor"),
        "next_url": request.GET.get("next") or request.path,
        "item_ativo": "agenda",
    })


@login_required
def adicionar_participante(request, pk):
    """Gerenciar participantes reaproveita a autorização de edição do
    item — sem habilitação granular própria."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = AdicionarParticipanteForm(
            request.POST,
            usuarios_queryset=_usuarios_elegiveis_para_participante(item),
        )
        if not form.is_valid():
            raise Http404
        participacao = _adicionar_participante(item, form.cleaned_data["usuario"])
        registrar_atividade(
            request.user, _tipo_atividade(item, "participante_adicionado"),
            f"Adicionou {participacao.usuario.get_full_name() or participacao.usuario.username} "
            f"como participante de {item.titulo}",
            processo=item.processo,
        )
    return redirect("agenda:editar", pk=pk)


@login_required
def remover_participante(request, pk, usuario_pk):
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        participacao = get_object_or_404(
            ParticipanteItemAgenda, item=item, usuario_id=usuario_pk
        )
        usuario = participacao.usuario
        participacao.delete()
        registrar_atividade(
            request.user, _tipo_atividade(item, "participante_removido"),
            f"Removeu {usuario.get_full_name() or usuario.username} dos participantes de "
            f"{item.titulo}",
            processo=item.processo,
        )
    return redirect("agenda:editar", pk=pk)


@login_required
def adicionar_equipe_participante(request, pk):
    """Equipe como atalho de seleção (PDR-0028): a lista de conferência
    envia só pessoas; cada uma vira participante normal. Mesma
    autorização de `adicionar_participante`."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        form = SelecionarMembrosEquipeForm(
            request.POST, usuarios_elegiveis=_usuarios_participantes_possiveis(item)
        )
        if not form.is_valid():
            raise Http404
        ja_participam = set(item.participacoes.values_list("usuario_id", flat=True))
        for usuario in form.cleaned_data["usuarios"]:
            if usuario.pk in ja_participam:
                continue
            _adicionar_participante(item, usuario)
            registrar_atividade(
                request.user, _tipo_atividade(item, "participante_adicionado"),
                f"Adicionou {usuario.get_full_name() or usuario.username} como participante "
                f"de {item.titulo}",
                processo=item.processo,
            )
    return redirect("agenda:editar", pk=pk)


@login_required
def adicionar_todos_participantes(request, pk):
    """Convida todos os usuários ativos ainda não participantes. Mesma
    autorização de `adicionar_participante`."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    item = get_object_or_404(_itens_mutaveis(request), pk=pk)
    if request.method == "POST":
        for usuario in _usuarios_elegiveis_para_participante(item):
            _adicionar_participante(item, usuario)
            registrar_atividade(
                request.user, _tipo_atividade(item, "participante_adicionado"),
                f"Adicionou {usuario.get_full_name() or usuario.username} como participante "
                f"de {item.titulo}",
                processo=item.processo,
            )
    return redirect("agenda:editar", pk=pk)


def _responder_presenca(request, pk, status):
    """Confirmar/recusar presença é ação do próprio participante sobre o
    próprio registro, só em Evento — não passa pela autorização de
    edição do item, só pela autorização de módulo."""
    if not tem_permissao_modulo(request.user, MODULO_AGENDA):
        raise PermissionDenied
    _resolver_escopo(request)
    participacao = get_object_or_404(
        ParticipanteItemAgenda, item_id=pk, usuario=request.user, item__tipo__in=TIPOS_EVENTO
    )
    if request.method == "POST":
        participacao.status = status
        participacao.save(update_fields=["status"])
    return _redirect_seguro(request)


@login_required
def confirmar_presenca(request, pk):
    return _responder_presenca(request, pk, ParticipanteItemAgenda.STATUS_CONFIRMADO)


@login_required
def recusar_presenca(request, pk):
    return _responder_presenca(request, pk, ParticipanteItemAgenda.STATUS_RECUSADO)
