from urllib.parse import urlencode

from django.db.models import F, Q
from django.db.models.functions import Coalesce, TruncDate
from django.urls import reverse
from django.utils import timezone

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import nivel_acesso_modulo, tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_TODOS

from .avisos import CONVITES_QUE_OCULTAM, avisar_atribuicao, avisar_fatal_alterada, avisar_prazo_gerado
from .models import (
    STATUS_CANCELADO,
    STATUS_ENCERRADOS,
    TIPO_PRAZO,
    TIPOS_AFAZER,
    TIPOS_EVENTO,
    ItemAgenda,
    ReatribuicaoItemAgenda,
)


def titulo_prazo_do_andamento(andamento):
    return f"Prazo — {andamento.get_tipo_display()}"


def sincronizar_prazo_do_andamento(andamento):
    """Mantém exatamente um Prazo por andamento com prazo de nosso
    cliente (PDR-0034, PDR-0037): cria, acompanha a data fatal ou remove.
    Retorna o item (ou None quando o andamento não gera prazo)."""
    item = ItemAgenda.objects.filter(movimentacao_origem=andamento).first()
    if not andamento.gera_prazo_na_agenda:
        if item is not None:
            item.delete()
        return None

    if item is None:
        processo = andamento.processo
        item = ItemAgenda.objects.create(
            tipo=TIPO_PRAZO,
            titulo=titulo_prazo_do_andamento(andamento),
            descricao=andamento.descricao,
            data_fatal=andamento.data_prazo,
            data_para_fazer=ItemAgenda.data_para_fazer_padrao(andamento.data_prazo),
            responsavel=processo.responsavel,
            atribuido_em=timezone.now(),
            processo=processo,
            cliente=processo.clientes.first(),
            movimentacao_origem=andamento,
        )
        avisar_prazo_gerado(item)
        return item

    if item.data_fatal != andamento.data_prazo:
        # Data para fazer ajustada à mão é preservada, desde que continue
        # antes da nova fatal.
        manteve_padrao = item.data_para_fazer in (None, ItemAgenda.data_para_fazer_padrao(item.data_fatal))
        if manteve_padrao or item.data_para_fazer > andamento.data_prazo:
            item.data_para_fazer = ItemAgenda.data_para_fazer_padrao(andamento.data_prazo)
        fatal_anterior = item.data_fatal
        item.data_fatal = andamento.data_prazo
        item.save(update_fields=["data_fatal", "data_para_fazer"])
        avisar_fatal_alterada(item, fatal_anterior)
    return item


def transferir_prazos_gerados(processo, novo_responsavel):
    """Prazos gerados por andamento ainda abertos acompanham o novo
    responsável do processo; concluído/cancelado guarda o histórico."""
    itens = (
        ItemAgenda.objects.filter(movimentacao_origem__processo=processo)
        .exclude(status__in=STATUS_ENCERRADOS)
        .exclude(responsavel=novo_responsavel)
    )
    agora = timezone.now()
    for item in itens:
        ReatribuicaoItemAgenda.objects.create(
            item=item, responsavel_anterior=item.responsavel, responsavel_novo=novo_responsavel,
        )
        item.responsavel = novo_responsavel
        item.atribuido_em = agora
        item.save(update_fields=["responsavel", "atribuido_em"])
        avisar_atribuicao(item)


def excluir_ocultos_por_convite(qs):
    """Remove item com convite de delegação pendente/recusado — ainda não
    é (ou nunca será) atribuição ativa do responsável (PDR-0033). Item
    sem convite (direto) ou com convite aceito não é afetado."""
    return qs.exclude(convite_delegacao__status__in=CONVITES_QUE_OCULTAM)


def restringir_ao_usuario(qs, user):
    """Escopo `somente_seus`: item onde o usuário é responsável OU
    participante (qualquer status de confirmação), fora os ocultos por
    convite."""
    qs = qs.filter(Q(responsavel=user) | Q(participacoes__usuario=user)).distinct()
    return excluir_ocultos_por_convite(qs)


def itens_visiveis_para(user):
    """Universo de LEITURA do usuário fora da tela da agenda (Dashboard,
    Processo, Cliente): nível máximo do módulo, sem cancelados; sem o
    módulo, nada."""
    if not tem_permissao_modulo(user, MODULO_AGENDA):
        return ItemAgenda.objects.none()
    qs = ItemAgenda.objects.exclude(status=STATUS_CANCELADO)
    if nivel_acesso_modulo(user, MODULO_AGENDA) != NIVEL_TODOS:
        qs = restringir_ao_usuario(qs, user)
    return qs


def itens_mutaveis_por(user):
    """
    "Todos" é escopo de visualização, não autorização de mutação: um
    usuário não-admin só muta item da própria responsabilidade. Só o
    Administrador do escritório alcança qualquer item do tenant —
    inclusive um item ainda oculto por convite de delegação.
    """
    qs = ItemAgenda.objects.all()
    if not usuario_admin_escritorio(user):
        qs = excluir_ocultos_por_convite(qs.filter(responsavel=user))
    return qs


def ordenar_por_data(qs):
    """Pela data em que o item cai na agenda — início (evento), data para
    fazer ou fatal (afazer); afazer sem data por último."""
    return qs.annotate(
        data_ref=Coalesce(TruncDate("data_hora_inicio"), "data_para_fazer", "data_fatal")
    ).order_by(F("data_ref").asc(nulls_last=True), "data_hora_inicio", "hora_para_fazer")


def anexar_urls(itens, user):
    """`item.url`: o formulário do item para quem pode editá-lo; para quem
    só enxerga, a Agenda Jurídica filtrada pelo vínculo do item."""
    mutaveis = set(
        itens_mutaveis_por(user).filter(pk__in=[i.pk for i in itens]).values_list("pk", flat=True)
    )
    for item in itens:
        if item.pk in mutaveis:
            item.url = reverse("agenda:editar", args=[item.pk])
            continue
        filtro = {"tipo": item.tipo}
        if item.processo_id:
            filtro["processo"] = item.processo_id
        elif item.cliente_id:
            filtro["cliente"] = item.cliente_id
        item.url = f"{reverse('agenda:index')}?{urlencode(filtro)}"
    return itens


def agenda_do_vinculo(user, *, processo=None, cliente=None, limite=5):
    """Card "Agenda do processo/cliente": itens em aberto de qualquer tipo
    vinculados, no escopo de leitura do usuário. None sem o módulo."""
    if not tem_permissao_modulo(user, MODULO_AGENDA):
        return None
    abertos = itens_visiveis_para(user).exclude(status__in=STATUS_ENCERRADOS)
    if processo is not None:
        abertos = abertos.filter(processo=processo)
    if cliente is not None:
        abertos = abertos.filter(cliente=cliente)
    itens = list(ordenar_por_data(abertos.select_related("responsavel"))[:limite])
    return {
        "itens": anexar_urls(itens, user),
        "total": abertos.count(),
        "tipos_por_natureza": [
            ("Afazer", [(t, r) for t, r in ItemAgenda.TIPO_CHOICES if t in TIPOS_AFAZER]),
            ("Evento", [(t, r) for t, r in ItemAgenda.TIPO_CHOICES if t in TIPOS_EVENTO]),
        ],
    }
