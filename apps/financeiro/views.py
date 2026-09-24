from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.permissoes import nivel_acesso_modulo, tem_permissao_modulo, tem_habilitacao
from apps.accounts.permissoes_constants import (
    HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO,
    MODULO_FINANCEIRO,
    NIVEL_DADOS_PROPRIOS,
    NIVEL_DADOS_TODOS,
    NIVEL_SOLICITACOES,
)
from apps.atividade.services import registrar_atividade
from apps.clientes.models import Cliente
from apps.clientes.validators import normalizar_documento
from apps.notificacoes.models import Notificacao
from apps.processos.models import Processo
from apps.processos.services import processos_do_cliente, rotulo_processo
from apps.saas_tenants.storage import resposta_de_arquivo

from .forms import (
    ConfirmarRecebimentoHonorarioForm,
    CreditarCustaForm,
    CustaJudicialForm,
    HonorarioForm,
    LancamentoFinanceiroForm,
    ReembolsoCustaForm,
    SolicitacaoFinanceiraForm,
)
from .models import (
    CustaJudicial, GrupoCustas, Honorario, LancamentoFinanceiro, MembroGrupoCustas, SolicitacaoFinanceira,
)
from .precatorio import ROTULO_ESFERA, elegivel_para_precatorio, esferas_publicas_do_processo, sugerir_regime
from .services import (
    analise_de_dados,
    atrasados,
    calcular_correcao_honorario,
    calcular_honorario_sucumbencial,
    cancelar_lancamentos_futuros_do_honorario,
    contratos_de_exito_pelo_ganho,
    gerar_lancamentos_do_honorario,
    cancelar_ocorrencias_futuras,
    custas_a_recuperar,
    gerar_ocorrencias,
    inicio_da_janela,
    lancamentos_operacionais,
    notificar_recebimento_de_honorario,
    receber_primeira_parcela,
    resumo_encerramento_recorrencia,
    reembolsar_custa,
    registrar_recebimento_honorario,
    registrar_credito_cliente,
    saldo_liquido_custas,
    saldo_previsto,
    situacao_do_honorario,
    uso_do_credito_por_custa,
    PERIODOS,
    janela_do_periodo,
    solicitacoes_vencendo_no_periodo,
    solicitacoes_vencidas,
    totais_da_janela,
    vencendo_no_periodo,
)


User = get_user_model()


def _redirect_seguro(request):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("financeiro:index")


FILTROS_LANCAMENTOS_VALIDOS = {
    "todos",
    "receitas",
    "despesas",
    "pagos",
    "recebidos",
    "apagar",
    "areceber",
    "atrasados",
    "solicitados",
    "apagar_periodo",
    "areceber_periodo",
    "apagar_atrasados",
    "areceber_atrasados",
}

# Filtros de ação do Painel: o próprio filtro define a janela de datas
# (de hoje ao fim do período, ou tudo o que já venceu), então ignoram o
# mês navegado.
FILTROS_PAINEL = {
    "apagar_periodo": "A pagar — vence {vence}",
    "areceber_periodo": "A receber — vence {vence}",
    "apagar_atrasados": "A pagar — atrasados",
    "areceber_atrasados": "A receber — atrasados",
}

# Rótulos do período (`?periodo=`) vindo do Painel.
ROTULOS_PERIODO = {
    "dia": {"no": "hoje", "do": "de hoje", "vence": "hoje"},
    "semana": {"no": "na semana", "do": "da semana", "vence": "nesta semana"},
    "mes": {"no": "no mês", "do": "do mês", "vence": "neste mês"},
}

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _normalizar_filtro_lancamentos(filtro):
    if filtro in FILTROS_LANCAMENTOS_VALIDOS:
        return filtro
    return "todos"


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


def _formatar_moeda(valor):
    valor = valor or Decimal("0")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar_saldo(valor):
    valor = valor or Decimal("0")
    sinal = "+ " if valor >= 0 else "− "
    return sinal + _formatar_moeda(abs(valor))


def _resumo_uso_do_credito(debitado, a_cobrar):
    partes = []
    if debitado:
        partes.append(f"{_formatar_moeda(debitado)} debitado do crédito")
    if a_cobrar:
        partes.append(f"{_formatar_moeda(a_cobrar)} a cobrar")
    return " e ".join(partes)


def _anotar_uso_do_credito(lancamentos, uso):
    for custa in lancamentos:
        if custa.pk in uso:
            custa.uso_credito = _resumo_uso_do_credito(*uso[custa.pk])


_NIVEIS_FINANCEIRO_DADOS = {NIVEL_DADOS_PROPRIOS, NIVEL_DADOS_TODOS}
_NIVEIS_FINANCEIRO_VALIDOS = {NIVEL_SOLICITACOES, *_NIVEIS_FINANCEIRO_DADOS}


def _nivel_financeiro(user):
    nivel = nivel_acesso_modulo(user, MODULO_FINANCEIRO)
    if nivel not in _NIVEIS_FINANCEIRO_VALIDOS:
        return NIVEL_SOLICITACOES
    return nivel


def _tem_acesso_dados(user):
    return _nivel_financeiro(user) in _NIVEIS_FINANCEIRO_DADOS


def _exige_nivel_dados(user):
    if not _tem_acesso_dados(user):
        raise PermissionDenied


def _exige_permissao_recebimento_honorario(user, lancamento):
    """Baixar, desfazer ou excluir recebimento de honorário é exclusivo do
    Administrador (PDR-0035). O recebimento de honorário único não se
    desfaz pelo lançamento: o `valor_recebido` do honorário ficaria errado."""
    if not lancamento.honorario_id:
        return
    if lancamento.eh_recebimento_de_honorario_unico or not usuario_admin_escritorio(user):
        raise PermissionDenied


def _lancamentos_no_escopo(user):
    qs = LancamentoFinanceiro.objects.select_related("cliente", "processo", "responsavel", "lancamento_origem")
    if _nivel_financeiro(user) == NIVEL_DADOS_PROPRIOS:
        qs = qs.filter(responsavel=user)
    return qs


@login_required
def index(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    if not _tem_acesso_dados(request.user):
        # Entrada única do módulo na sidebar — nível "solicitacoes" não
        # alcança o caixa geral, então é levado direto às solicitações.
        return redirect("financeiro:solicitacoes_lista")
    hoje = timezone.localdate()
    filtro = _normalizar_filtro_lancamentos(request.GET.get("filtro", "todos"))
    periodo = request.GET.get("periodo")
    if periodo not in PERIODOS:
        periodo = None
    ano, mes = _resolver_mes_ano(request, hoje)
    # Dia/semana vindos do Painel recortam lista e resumo por essa janela
    # no lugar do mês navegado; "mes" é o próprio mês corrente.
    recorte_periodo = periodo in ("dia", "semana")
    if recorte_periodo:
        inicio_janela, fim_janela = janela_do_periodo(periodo, hoje)
    else:
        inicio_janela = date(ano, mes, 1)
        fim_janela = date(ano, mes, monthrange(ano, mes)[1])
    fim_do_periodo = janela_do_periodo(periodo or "dia", hoje)[1]

    escopo = _lancamentos_no_escopo(request.user)
    escopo_janela = escopo.filter(data_vencimento__gte=inicio_janela, data_vencimento__lte=fim_janela)

    lancamentos = escopo_janela
    if filtro == "receitas":
        lancamentos = lancamentos.filter(tipo="receita")
    elif filtro == "despesas":
        lancamentos = lancamentos.filter(tipo="despesa")
    elif filtro == "pagos":
        lancamentos = lancamentos.filter(tipo="despesa", status="pago")
    elif filtro == "recebidos":
        lancamentos = lancamentos.filter(tipo="receita", status="pago")
    elif filtro == "apagar":
        lancamentos = lancamentos.filter(tipo="despesa", status="pendente")
    elif filtro == "areceber":
        lancamentos = lancamentos.filter(tipo="receita", status="pendente")
    elif filtro == "atrasados":
        # Atrasado de mês anterior continua atrasado — nunca some por
        # causa do mês navegado.
        lancamentos = atrasados(escopo, hoje)
    elif filtro == "apagar_periodo":
        lancamentos = vencendo_no_periodo(escopo, "despesa", hoje, fim_do_periodo)
    elif filtro == "areceber_periodo":
        lancamentos = vencendo_no_periodo(escopo, "receita", hoje, fim_do_periodo)
    elif filtro == "apagar_atrasados":
        lancamentos = atrasados(escopo, hoje, "despesa")
    elif filtro == "areceber_atrasados":
        lancamentos = atrasados(escopo, hoje, "receita")
    elif filtro == "solicitados":
        lancamentos = lancamentos.filter(solicitacao_origem__isnull=False)

    # Reembolso/custas de cliente ficam fora de recebido/pago; as custas
    # adiantadas e não reembolsadas entram em "pago" (dado global — só
    # para quem vê todos os dados).
    totais = totais_da_janela(
        escopo, inicio_janela, fim_janela,
        incluir_custas=_nivel_financeiro(request.user) == NIVEL_DADOS_TODOS,
    )
    a_receber, a_pagar = totais["a_receber"], totais["a_pagar"]
    recebido_mes, pago_mes = totais["recebido"], totais["pago"]
    saldo_atual_mes = recebido_mes - pago_mes

    resumo = {
        "a_receber": _formatar_moeda(a_receber),
        "a_pagar": _formatar_moeda(a_pagar),
        "recebido_mes": _formatar_moeda(recebido_mes),
        "pago_mes": _formatar_moeda(pago_mes),
        "saldo_previsto": _formatar_moeda(saldo_previsto(totais)),
        "saldo_atual_mes": _formatar_saldo(saldo_atual_mes),
        "saldo_atual_mes_positivo": saldo_atual_mes >= 0,
    }

    ano_anterior, mes_anterior = _mes_adjacente(ano, mes, -1)
    ano_seguinte, mes_seguinte = _mes_adjacente(ano, mes, 1)

    return render(request, "financeiro/index.html", {
        "resumo": resumo,
        "lancamentos": lancamentos,
        "filtro": filtro,
        "filtro_painel": FILTROS_PAINEL.get(filtro, "").format(**ROTULOS_PERIODO[periodo or "dia"]),
        "periodo": periodo,
        "recorte_periodo": recorte_periodo,
        "rotulo_janela": ROTULOS_PERIODO[periodo if recorte_periodo else "mes"],
        "inicio_janela": inicio_janela,
        "fim_janela": fim_janela,
        "query_janela": f"periodo={periodo}" if recorte_periodo else f"ano={ano}&mes={mes}",
        "next_url": request.get_full_path(),
        "is_admin": usuario_admin_escritorio(request.user),
        "aba_ativa": "lancamentos",
        "item_ativo": "financeiro",
        "mes_ano": ano,
        "mes_mes": mes,
        "mes_nome": MESES[mes - 1],
        "mes_atual": ano == hoje.year and mes == hoje.month,
        "mes_ano_anterior": ano_anterior,
        "mes_mes_anterior": mes_anterior,
        "mes_ano_seguinte": ano_seguinte,
        "mes_mes_seguinte": mes_seguinte,
    })


PERIODOS_GRAFICO_VALIDOS = {"6meses", "12meses", "exercicio"}
JANELAS_ANALISE_VALIDAS = {"sempre", "12meses", "exercicio"}


def _normalizar_periodo_grafico(periodo):
    if periodo in PERIODOS_GRAFICO_VALIDOS:
        return periodo
    return "6meses"


@login_required
def grafico(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    if not _tem_acesso_dados(request.user):
        return redirect("financeiro:solicitacoes_lista")

    hoje = timezone.localdate()
    periodo = _normalizar_periodo_grafico(request.GET.get("periodo", "6meses"))

    if periodo == "exercicio":
        data_inicio = date(hoje.year, 1, 1)
    else:
        meses = 6 if periodo == "6meses" else 12
        ano_inicio, mes_inicio = _mes_adjacente(hoje.year, hoje.month, -(meses - 1))
        data_inicio = date(ano_inicio, mes_inicio, 1)

    lancamentos_escopo = _lancamentos_no_escopo(request.user)
    incluir_custas = _nivel_financeiro(request.user) == NIVEL_DADOS_TODOS
    escopo = lancamentos_operacionais(lancamentos_escopo).filter(
        status="pago", data_pagamento__gte=data_inicio,
    )
    agregados = (
        escopo.values("data_pagamento__year", "data_pagamento__month", "tipo")
        .annotate(total=Sum("valor"))
    )
    por_mes = defaultdict(lambda: {"receita": Decimal("0"), "despesa": Decimal("0")})
    for linha in agregados:
        chave = (linha["data_pagamento__year"], linha["data_pagamento__month"])
        por_mes[chave][linha["tipo"]] = linha["total"]

    meses_intervalo = []
    ano_cursor, mes_cursor = data_inicio.year, data_inicio.month
    while (ano_cursor, mes_cursor) <= (hoje.year, hoje.month):
        meses_intervalo.append((ano_cursor, mes_cursor))
        ano_cursor, mes_cursor = _mes_adjacente(ano_cursor, mes_cursor, 1)

    if incluir_custas:
        for ano_mes, mes_mes in meses_intervalo:
            devedor = sum(
                custas_a_recuperar(
                    inicio=date(ano_mes, mes_mes, 1),
                    fim=date(ano_mes, mes_mes, monthrange(ano_mes, mes_mes)[1]),
                ).values(),
                Decimal("0"),
            )
            if devedor:
                por_mes[(ano_mes, mes_mes)]["despesa"] += devedor

    maior_valor = max(
        (v for dados in por_mes.values() for v in dados.values()), default=Decimal("0")
    ) or Decimal("1")

    barras = []
    for ano_mes, mes_mes in meses_intervalo:
        dados = por_mes.get((ano_mes, mes_mes), {"receita": Decimal("0"), "despesa": Decimal("0")})
        barras.append({
            "mes_label": MESES[mes_mes - 1][:3].upper(),
            "receita": _formatar_moeda(dados["receita"]),
            "despesa": _formatar_moeda(dados["despesa"]),
            "receita_pct": int((dados["receita"] / maior_valor) * 100),
            "despesa_pct": int((dados["despesa"] / maior_valor) * 100),
        })

    janela = request.GET.get("janela")
    if janela not in JANELAS_ANALISE_VALIDAS:
        janela = "sempre"
    analise = analise_de_dados(
        lancamentos_escopo, inicio=inicio_da_janela(janela, hoje), incluir_custas=incluir_custas,
    )

    return render(request, "financeiro/grafico.html", {
        "barras": barras,
        "periodo": periodo,
        "janela": janela,
        "analise": analise,
        "ano_exercicio": hoje.year,
        "aba_ativa": "grafico",
        "item_ativo": "financeiro",
    })


_FILTROS_SALDO = {
    "com_credito": ("Com crédito", lambda saldo: saldo > 0),
    "em_debito": ("Em débito", lambda saldo: saldo < 0),
    "sem_saldo": ("Sem saldo pendente", lambda saldo: saldo == 0),
}


def _rotulo_saldo(saldo):
    if saldo == 0:
        return "Sem saldo pendente"
    prefixo = "Crédito: " if saldo > 0 else "A cobrar: "
    return prefixo + _formatar_moeda(abs(saldo))


def _casa_busca(busca, *, nomes, documento=""):
    """Nome (sem distinguir caixa) ou documento (com ou sem pontuação)."""
    termo = busca.casefold()
    if any(termo in nome.casefold() for nome in nomes):
        return True
    digitos = normalizar_documento(busca)
    return bool(documento) and (busca in documento or (digitos and digitos in normalizar_documento(documento)))


def _linhas_de_saldo(custas, busca):
    """Uma linha por cliente ativo fora de grupo e por grupo, com o saldo
    de cada um — o grupo entra pelo saldo do próprio grupo e o membro só
    aparece dentro dele (busca pelo nome do membro também acha o grupo)."""
    individuais, por_grupo = defaultdict(list), defaultdict(list)
    for c in custas:
        if c.grupo_id:
            por_grupo[c.grupo_id].append(c)
        elif c.cliente_id:
            individuais[c.cliente_id].append(c)

    linhas = []
    clientes = Cliente.objects.filter(ativo=True, grupo_custas__isnull=True)
    for cliente in clientes:
        if busca and not _casa_busca(busca, nomes=[cliente.nome_razao_social], documento=cliente.cpf_cnpj):
            continue
        saldo = saldo_liquido_custas(individuais.get(cliente.id, []))
        linhas.append({
            "cliente_id": cliente.id, "grupo_id": None, "cliente": cliente, "saldo_valor": saldo,
            "url": reverse("financeiro:extrato_custas_cliente", args=[cliente.id]),
        })
    for grupo in GrupoCustas.objects.prefetch_related("membros__cliente"):
        nomes_membros = [m.cliente.nome_razao_social for m in grupo.membros.all()]
        if busca and not _casa_busca(busca, nomes=[grupo.nome, *nomes_membros]):
            continue
        saldo = saldo_liquido_custas(por_grupo.get(grupo.id, []))
        linhas.append({
            "cliente_id": None, "grupo_id": grupo.id, "grupo": grupo, "saldo_valor": saldo,
            "nomes_membros": nomes_membros,
            "url": reverse("financeiro:extrato_custas_grupo", args=[grupo.id]),
        })
    for linha in linhas:
        linha["saldo"] = _rotulo_saldo(linha["saldo_valor"])
        linha["credito"] = linha["saldo_valor"] >= 0
    return linhas


@login_required
def custas(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    custas_qs = list(
        CustaJudicial.objects.select_related("cliente", "processo", "grupo").order_by("-data", "-criado_em")
    )

    busca = (request.GET.get("busca") or "").strip()
    filtro_saldo = request.GET.get("saldo") or ""
    if filtro_saldo not in _FILTROS_SALDO:
        filtro_saldo = ""
    # Lista sempre todo cliente ativo, mesmo sem nenhum lançamento —
    # antes só aparecia quem já tinha CustaJudicial (reunião de 13/09).
    saldo_clientes = _linhas_de_saldo(custas_qs, busca)
    if filtro_saldo:
        aceita = _FILTROS_SALDO[filtro_saldo][1]
        saldo_clientes = [linha for linha in saldo_clientes if aceita(linha["saldo_valor"])]

    return render(request, "financeiro/custas.html", {
        "custas": custas_qs,
        "saldo_clientes": saldo_clientes,
        "filtro_busca": busca,
        "filtro_saldo": filtro_saldo,
        "filtros_saldo": [(chave, rotulo) for chave, (rotulo, _) in _FILTROS_SALDO.items()],
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def extrato_custas_cliente(request, cliente_id):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    custas_cliente = list(
        CustaJudicial.objects.filter(cliente=cliente)
        .select_related("processo", "reembolsada_por", "grupo").order_by("-data", "-criado_em")
    )
    lancamentos = [c for c in custas_cliente if c.tipo in ("adiantamento", "paga_pelo_cliente")]
    creditos = [c for c in custas_cliente if c.tipo == "deposito_cliente"]
    # Débitos pagos pelo saldo do grupo aparecem no histórico do membro,
    # mas o saldo individual só considera o que não é do grupo.
    individuais = [c for c in custas_cliente if not c.grupo_id]
    saldo = saldo_liquido_custas(individuais)
    membro = MembroGrupoCustas.objects.select_related("grupo").filter(cliente=cliente).first()

    # Débito pago pelo saldo de um grupo só se desdobra olhando o histórico
    # do grupo inteiro, não só o do membro.
    uso = uso_do_credito_por_custa(individuais)
    for grupo_id in {c.grupo_id for c in lancamentos if c.grupo_id}:
        uso.update(uso_do_credito_por_custa(CustaJudicial.objects.filter(grupo_id=grupo_id)))
    _anotar_uso_do_credito(lancamentos, uso)

    # Filtros só da lista de lançamentos (custas), nunca do saldo.
    processos_do_extrato = {c.processo_id: c.processo for c in lancamentos if c.processo_id}
    filtro_processo = request.GET.get("processo") or ""
    filtro_pago_por = request.GET.get("pago_por") or ""
    if filtro_processo:
        lancamentos = [c for c in lancamentos if str(c.processo_id) == filtro_processo]
    if filtro_pago_por == "escritorio":
        lancamentos = [c for c in lancamentos if c.tipo == "adiantamento"]
    elif filtro_pago_por == "cliente":
        lancamentos = [c for c in lancamentos if c.tipo == "paga_pelo_cliente"]
    else:
        filtro_pago_por = ""

    return render(request, "financeiro/extrato_custas_cliente.html", {
        "cliente": cliente,
        "grupo_do_cliente": membro.grupo if membro else None,
        "lancamentos": lancamentos,
        "creditos": creditos,
        "processos_do_extrato": list(processos_do_extrato.values()),
        "filtro_processo": filtro_processo,
        "filtro_pago_por": filtro_pago_por,
        "saldo": _formatar_saldo(saldo),
        "saldo_positivo": saldo >= 0,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def processos_por_cliente(request):
    """Processos do cliente informado, para o filtro dinâmico dos
    formulários de criação/edição do módulo financeiro."""
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    processos = processos_do_cliente(request.GET.get("cliente"))
    return JsonResponse({
        "processos": [{"id": p.id, "label": rotulo_processo(p)} for p in processos],
    })


@login_required
def form_lancamento(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    if request.method == "POST":
        form = LancamentoFinanceiroForm(request.POST, request.FILES)
        if form.is_valid():
            lancamento = form.save(commit=False)
            if not lancamento.responsavel:
                lancamento.responsavel = request.user
            if lancamento.processo and not lancamento.cliente:
                lancamento.cliente = lancamento.processo.clientes.first()
            lancamento.save()
            gerar_ocorrencias(lancamento)
            registrar_atividade(
                request.user, "lancamento_criado", f"Criou o lançamento {lancamento.descricao}",
                processo=lancamento.processo,
            )
            return redirect("financeiro:index")
    else:
        form = LancamentoFinanceiroForm(initial={"responsavel": request.user})

    return render(request, "financeiro/form_lancamento.html", {
        "form": form,
        "modo": "novo",
        "aba_ativa": "lancamentos",
        "item_ativo": "financeiro",
    })


@login_required
def editar_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    pode_receber_honorario = usuario_admin_escritorio(request.user)
    if lancamento.honorario_id and lancamento.status == "pago" and not pode_receber_honorario:
        raise PermissionDenied

    if request.method == "POST":
        form = LancamentoFinanceiroForm(
            request.POST, request.FILES, instance=lancamento, pode_receber_honorario=pode_receber_honorario,
        )
        if form.is_valid():
            lancamento = form.save(commit=False)
            if not lancamento.responsavel:
                lancamento.responsavel = request.user
            if lancamento.processo and not lancamento.cliente:
                lancamento.cliente = lancamento.processo.clientes.first()
            lancamento.save()
            gerar_ocorrencias(lancamento)
            registrar_atividade(
                request.user, "lancamento_editado", f"Editou o lançamento {lancamento.descricao}",
                processo=lancamento.processo,
            )
            return redirect("financeiro:index")
    else:
        form = LancamentoFinanceiroForm(instance=lancamento, pode_receber_honorario=pode_receber_honorario)

    return render(request, "financeiro/form_lancamento.html", {
        "form": form,
        "modo": "editar",
        "lancamento": lancamento,
        "aba_ativa": "lancamentos",
        "item_ativo": "financeiro",
    })


@login_required
def marcar_pago(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    _exige_permissao_recebimento_honorario(request.user, lancamento)
    if request.method == "POST":
        lancamento.status = "pago"
        lancamento.data_pagamento = timezone.localdate()
        lancamento.save(update_fields=["status", "data_pagamento"])
        registrar_atividade(
            request.user, "lancamento_pago", f"Marcou como pago o lançamento {lancamento.descricao}",
            processo=lancamento.processo,
        )
        if lancamento.honorario_id:
            notificar_recebimento_de_honorario(lancamento.honorario, request.user)
    return _redirect_seguro(request)


@login_required
def cancelar_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if lancamento.status == "pago":
        _exige_permissao_recebimento_honorario(request.user, lancamento)
    if request.method != "POST":
        return render(request, "financeiro/_confirmar_cancelamento.html", {
            "lancamento": lancamento,
            "next_url": request.GET.get("next", ""),
        })
    lancamento.status = "cancelado"
    lancamento.save(update_fields=["status"])
    registrar_atividade(
        request.user, "lancamento_cancelado", f"Cancelou o lançamento {lancamento.descricao}",
        processo=lancamento.processo,
    )
    return _redirect_seguro(request)


@login_required
def cancelar_recorrencia(request, pk):
    """Cancela as ocorrências futuras (pendentes, não vencidas) do
    parcelamento/recorrência de `lancamento` — sem afetar ocorrências já
    pagas, canceladas ou vencidas (PDR-0021)."""
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if request.method != "POST":
        return render(request, "financeiro/_confirmar_encerramento.html", {
            "lancamento": lancamento,
            "resumo": resumo_encerramento_recorrencia(lancamento),
            "next_url": request.GET.get("next", ""),
        })
    cancelar_ocorrencias_futuras(lancamento)
    registrar_atividade(
        request.user, "lancamento_recorrencia_cancelada",
        f"Cancelou a recorrência futura do lançamento {lancamento.descricao}",
        processo=lancamento.processo,
    )
    return _redirect_seguro(request)


@login_required
def reabrir_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    # Escopo (dados_proprios) é checado antes da habilitação abaixo: em
    # dados_proprios, HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO nunca alcança
    # lançamento de responsável diferente do usuário atual (404 aqui, antes
    # de chegar na checagem de habilitação) — ver ARCHITECTURE.md.
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if lancamento.status == "pago":
        _exige_permissao_recebimento_honorario(request.user, lancamento)
    origem = getattr(lancamento, "solicitacao_origem", None)
    if origem is not None and not tem_habilitacao(
        request.user, MODULO_FINANCEIRO, HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO
    ):
        raise PermissionDenied
    if request.method == "POST":
        lancamento.status = "pendente"
        lancamento.data_pagamento = None
        lancamento.save(update_fields=["status", "data_pagamento"])
        registrar_atividade(
            request.user, "lancamento_reaberto", f"Reabriu o lançamento {lancamento.descricao}",
            processo=lancamento.processo,
        )
        if origem is not None and origem.solicitante_id and origem.solicitante_id != request.user.id:
            Notificacao.objects.create(
                destinatario=origem.solicitante,
                mensagem=f'Lançamento reaberto: "{lancamento.descricao}"',
            )
    return _redirect_seguro(request)


@login_required
def excluir_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if hasattr(lancamento, "solicitacao_origem"):
        raise PermissionDenied
    _exige_permissao_recebimento_honorario(request.user, lancamento)
    if request.method == "POST":
        descricao = lancamento.descricao
        processo = lancamento.processo
        lancamento.delete()
        registrar_atividade(
            request.user, "lancamento_excluido", f"Excluiu o lançamento {descricao}",
            processo=processo,
        )
    return _redirect_seguro(request)


@login_required
def anexo_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if not lancamento.anexo:
        raise Http404
    return resposta_de_arquivo(request, lancamento.anexo)


@login_required
def anexar_lancamento(request, pk):
    """Ação inline da lista de lançamentos: anexa o boleto/documento da
    despesa sem navegar para a tela de edição completa — independe do
    status."""
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if request.method == "POST" and request.FILES.get("anexo"):
        lancamento.anexo = request.FILES["anexo"]
        lancamento.save(update_fields=["anexo"])
    return _redirect_seguro(request)


@login_required
def comprovante_pagamento_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if not lancamento.comprovante_pagamento:
        raise Http404
    return resposta_de_arquivo(request, lancamento.comprovante_pagamento)


@login_required
def anexar_comprovante_lancamento(request, pk):
    """Ação inline da lista de lançamentos: anexa o comprovante de
    pagamento sem navegar para a tela de edição completa — só disponível
    com o lançamento pago, mesma regra do formulário."""
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if lancamento.status == "pago" and request.method == "POST" and request.FILES.get("comprovante_pagamento"):
        lancamento.comprovante_pagamento = request.FILES["comprovante_pagamento"]
        lancamento.save(update_fields=["comprovante_pagamento"])
    return _redirect_seguro(request)


@login_required
def form_custa(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    if request.method == "POST":
        form = CustaJudicialForm(request.POST, request.FILES)
        if form.is_valid():
            custa = form.save()
            registrar_atividade(
                request.user, "custa_criada", f"Criou a custa judicial {custa.descricao}",
                processo=custa.processo,
            )
            if custa.grupo_id:
                return redirect("financeiro:extrato_custas_grupo", grupo_id=custa.grupo_id)
            if custa.cliente_id:
                return redirect("financeiro:extrato_custas_cliente", cliente_id=custa.cliente_id)
            return redirect("financeiro:custas")
    else:
        initial = {"data": timezone.localdate()}
        for campo in ("cliente", "grupo"):
            if request.GET.get(campo):
                initial[campo] = request.GET[campo]
        form = CustaJudicialForm(initial=initial)

    return render(request, "financeiro/form_custa.html", {
        "form": form,
        "url_aviso_saldo": reverse("financeiro:aviso_saldo_custa"),
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def form_creditar_custa(request, cliente_id):
    """Fluxo dedicado de Creditar — Cliente e Tipo ('Depósito do
    cliente') nunca chegam como campo do formulário: o cliente vem da
    própria rota, o tipo é fixado no momento de salvar (reunião de
    13/09)."""
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    cliente = get_object_or_404(Cliente, pk=cliente_id, ativo=True)
    if request.method == "POST":
        form = CreditarCustaForm(request.POST, request.FILES, cliente=cliente)
        if form.is_valid():
            # Creditar é uma receita "Reembolso" no financeiro geral que
            # já nasce com o crédito nas custas do cliente.
            dados = form.cleaned_data
            registrar_credito_cliente(
                cliente=cliente, valor=dados["valor"], data=dados["data"],
                descricao=dados["descricao"], processo=dados.get("processo"),
                anexo=dados.get("anexo"), responsavel=request.user,
            )
            registrar_atividade(
                request.user, "custa_creditada", f"Creditou custa a {cliente}",
                processo=dados.get("processo"),
            )
            return redirect("financeiro:extrato_custas_cliente", cliente_id=cliente.pk)
    else:
        form = CreditarCustaForm(cliente=cliente, initial={"data": timezone.localdate()})

    return render(request, "financeiro/form_creditar_custa.html", {
        "form": form,
        "cliente": cliente,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


@login_required
def anexo_custa(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    custa = get_object_or_404(CustaJudicial, pk=pk)
    if not custa.anexo:
        raise Http404
    return resposta_de_arquivo(request, custa.anexo)


@login_required
def form_reembolsar_custa(request, pk):
    """Reembolso, pelo cliente, de uma custa adiantada pelo escritório —
    anexa o comprovante e baixa o saldo devedor dele."""
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    custa = get_object_or_404(CustaJudicial.objects.select_related("cliente", "processo"), pk=pk)
    if not custa.pode_reembolsar:
        raise Http404
    if request.method == "POST":
        form = ReembolsoCustaForm(request.POST, request.FILES)
        if form.is_valid():
            reembolsar_custa(
                custa, data=form.cleaned_data["data"],
                comprovante=form.cleaned_data["comprovante"], responsavel=request.user,
            )
            registrar_atividade(
                request.user, "custa_reembolsada", f"Reembolsou a custa {custa.descricao}",
                processo=custa.processo,
            )
            return redirect("financeiro:extrato_custas_cliente", cliente_id=custa.cliente_id)
    else:
        form = ReembolsoCustaForm(initial={"data": timezone.localdate()})

    return render(request, "financeiro/form_reembolsar_custa.html", {
        "form": form,
        "custa": custa,
        "aba_ativa": "custas",
        "item_ativo": "financeiro",
    })


def _honorarios_no_escopo():
    return Honorario.objects.select_related("cliente", "processo")


def _preparar_precatorio(honorarios, hoje):
    """Sucumbências pagas pela Fazenda, com a sugestão de regime. O valor
    comparado ao teto é só o da sucumbência — o êxito do contrato segue o
    crédito do cliente, não este honorário."""
    elegiveis = [h for h in honorarios if elegivel_para_precatorio(h)]
    for h in elegiveis:
        h.valor_precatorio = h.calculo["sucumbencia"] if h.calculado else (h.valor_efetivo or h.valor_estimado)
        h.esferas_publicas = esferas_publicas_do_processo(h.processo)
        h.esferas_rotulo = ", ".join(ROTULO_ESFERA[e] for e in h.esferas_publicas)
        h.sugestao_regime = sugerir_regime(esferas=h.esferas_publicas, valor=h.valor_precatorio, data=hoje)
    return elegiveis


def _calculo_sucumbencial(honorario, ate):
    """Total da sucumbência já com o aviso de êxito dos contratos "pelo
    ganho" do mesmo processo (PDR-0032)."""
    return calcular_honorario_sucumbencial(honorario, ate, contratos_de_exito_pelo_ganho(honorario.processo))


def _salvar_honorario(form, usuario):
    """Grava o honorário e, se contratual parcelado/recorrente, gera os
    lançamentos pendentes vinculados a ele; com "Já recebido" marcado
    (só no cadastro, só Administrador), registra também o recebimento —
    tudo numa transação só."""
    with transaction.atomic():
        honorario = form.save()
        gerar_lancamentos_do_honorario(honorario, responsavel=usuario)
        if form.cleaned_data.get("ja_recebido"):
            _registrar_recebimento_do_cadastro(honorario, form.cleaned_data, usuario)
    return honorario


def _registrar_recebimento_do_cadastro(honorario, dados, usuario):
    data, comprovante = dados["data_recebimento"], dados.get("comprovante_recebimento")
    if honorario.recebimento_por_lancamentos:
        receber_primeira_parcela(honorario, data=data, comprovante=comprovante, usuario=usuario)
    else:
        registrar_recebimento_honorario(
            honorario, valor_efetivo=honorario.valor_estimado, valor=honorario.valor_estimado,
            data=data, comprovante=comprovante, usuario=usuario,
        )
    registrar_atividade(
        usuario, "honorario_recebido",
        f"Registrou recebimento no cadastro do honorário ({honorario.get_tipo_display()})",
        processo=honorario.processo,
    )


def _preparar_ciclo(honorario):
    """Parcelas e recebimentos vinculados, para o card: quantas parcelas
    já entraram e quantos recebimentos ainda estão sem comprovante."""
    lancamentos = [l for l in honorario.lancamentos.all() if l.status != "cancelado"]
    pagos = [l for l in lancamentos if l.status == "pago"]
    honorario.parcelas_total = len(lancamentos)
    honorario.parcelas_recebidas = len(pagos)
    honorario.sem_comprovante = sum(1 for l in pagos if not l.comprovante_pagamento)


@login_required
def honorarios_lista(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    hoje = timezone.localdate()
    honorarios = list(
        _honorarios_no_escopo().prefetch_related("processo__partes", "lancamentos").order_by("-criado_em")
    )
    for h in honorarios:
        _preparar_ciclo(h)
        if h.calculado:
            # Total sempre recalculado dos parâmetros — nunca o valor gravado.
            h.calculo = _calculo_sucumbencial(h, hoje)
            h.valor_total_exibido = h.calculo["total"]
            h.valor_pendente_hoje = max(h.calculo["total"] - h.valor_recebido, Decimal("0"))
            continue
        if not h.confirmavel:
            h.valor_total_exibido = h.valor_estimado
            continue
        valor_efetivo = h.valor_efetivo or h.valor_estimado
        pendente_base = valor_efetivo - h.valor_recebido
        correcao = calcular_correcao_honorario(
            valor_pendente=pendente_base,
            taxa_mensal=h.taxa_mensal,
            data_termo=h.data_termo,
            referencia_anterior=h.data_recebida,
            ate_data=hoje,
        )
        h.valor_total_exibido = valor_efetivo
        h.valor_pendente_hoje = pendente_base + correcao
    for h in honorarios:
        h.situacao = situacao_do_honorario(h, hoje, getattr(h, "valor_pendente_hoje", None))

    return render(request, "financeiro/honorarios_lista.html", {
        "honorarios": honorarios,
        # Sub-abas Contratuais/Sucumbência — "exito"/"outro" são tipos
        # legados (não mais criáveis, PDR-0032) e entram em Contratuais.
        "honorarios_contratuais": [h for h in honorarios if h.tipo != "sucumbencial"],
        "honorarios_sucumbencia": [h for h in honorarios if h.tipo == "sucumbencial"],
        "honorarios_precatorio": _preparar_precatorio(honorarios, hoje),
        "sub_aba": request.GET.get("aba", "contratuais"),
        "regime_choices": Honorario.REGIME_PAGAMENTO_CHOICES,
        "is_admin": usuario_admin_escritorio(request.user),
        "aba_ativa": "honorarios",
        "item_ativo": "financeiro",
    })


@login_required
def form_honorario(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    pode_registrar_recebimento = usuario_admin_escritorio(request.user)
    if request.method == "POST":
        form = HonorarioForm(request.POST, request.FILES, pode_registrar_recebimento=pode_registrar_recebimento)
        if form.is_valid():
            honorario = _salvar_honorario(form, request.user)
            registrar_atividade(
                request.user, "honorario_criado", f"Criou o honorário ({honorario.get_tipo_display()})",
                processo=honorario.processo,
            )
            return redirect("financeiro:honorarios_lista")
    else:
        form = HonorarioForm(pode_registrar_recebimento=pode_registrar_recebimento)

    return render(request, "financeiro/form_honorario.html", {
        "form": form,
        "modo": "novo",
        "aba_ativa": "honorarios",
        "item_ativo": "financeiro",
    })


@login_required
def editar_honorario(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    honorario = get_object_or_404(_honorarios_no_escopo(), pk=pk)

    if request.method == "POST":
        form = HonorarioForm(request.POST, request.FILES, instance=honorario)
        if form.is_valid():
            honorario = _salvar_honorario(form, request.user)
            registrar_atividade(
                request.user, "honorario_editado", f"Editou o honorário ({honorario.get_tipo_display()})",
                processo=honorario.processo,
            )
            return redirect("financeiro:honorarios_lista")
    else:
        form = HonorarioForm(instance=honorario)

    avisos_exito = _calculo_sucumbencial(honorario, timezone.localdate())["exito_contratos"] if honorario.calculado else []
    return render(request, "financeiro/form_honorario.html", {
        "form": form,
        "modo": "editar",
        "honorario": honorario,
        "avisos_exito": avisos_exito,
        "aba_ativa": "honorarios",
        "item_ativo": "financeiro",
    })


@login_required
def confirmar_recebimento_honorario(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    if not usuario_admin_escritorio(request.user):
        raise PermissionDenied
    honorario = get_object_or_404(_honorarios_no_escopo(), pk=pk)
    if not honorario.confirmavel:
        # Êxito é só anotação; parcelado/recorrente recebe nos lançamentos.
        raise Http404
    # Capturados antes de validar o form: ModelForm._post_clean() já
    # escreve os valores novos em `honorario` (mesma instância) durante
    # form.is_valid(), então ler `honorario.<campo>` depois disso
    # devolveria o valor recém-submetido, não o valor anterior.
    if honorario.calculado:
        valor_efetivo_antes = _calculo_sucumbencial(honorario, timezone.localdate())["total"]
    else:
        valor_efetivo_antes = honorario.valor_efetivo or honorario.valor_estimado
    valor_recebido_antes = honorario.valor_recebido
    taxa_mensal_antes = honorario.taxa_mensal
    data_termo_antes = honorario.data_termo
    data_recebida_antes = honorario.data_recebida

    if request.method == "POST":
        form = ConfirmarRecebimentoHonorarioForm(request.POST, request.FILES, instance=honorario)
        if form.is_valid():
            # Correção calculada com a taxa/data-termo/valor vigentes
            # antes desta submissão — cobre o tempo entre a confirmação
            # anterior (ou a data-termo) e esta confirmação.
            pendente_anterior = valor_efetivo_antes - valor_recebido_antes
            data_recebida_nova = form.cleaned_data["data_recebida"]
            correcao = calcular_correcao_honorario(
                valor_pendente=pendente_anterior,
                taxa_mensal=taxa_mensal_antes,
                data_termo=data_termo_antes,
                referencia_anterior=data_recebida_antes,
                ate_data=data_recebida_nova,
            )

            honorario_atualizado = form.save(commit=False)
            honorario_atualizado.valor_efetivo = form.cleaned_data["valor_efetivo"] + correcao

            valor_recebido_agora = form.cleaned_data.get("valor_recebido_agora")
            if not valor_recebido_agora:
                # Sem valor parcial informado, confirma o pendente
                # inteiro — mesmo comportamento de antes do PDR-0022.
                valor_recebido_agora = honorario_atualizado.valor_efetivo - valor_recebido_antes

            novo_valor_recebido = valor_recebido_antes + valor_recebido_agora
            if novo_valor_recebido > honorario_atualizado.valor_efetivo:
                form.add_error(
                    "valor_recebido_agora",
                    "O valor recebido não pode ultrapassar o valor efetivo pendente.",
                )
            else:
                # O service soma em `valor_recebido`: parte do valor anterior.
                honorario_atualizado.valor_recebido = valor_recebido_antes
                registrar_recebimento_honorario(
                    honorario_atualizado,
                    valor_efetivo=honorario_atualizado.valor_efetivo,
                    valor=valor_recebido_agora,
                    data=data_recebida_nova,
                    comprovante=form.cleaned_data.get("anexo"),
                    usuario=request.user,
                )
                registrar_atividade(
                    request.user, "honorario_recebido",
                    f"Confirmou recebimento do honorário ({honorario.get_tipo_display()})",
                    processo=honorario.processo,
                )
                return redirect("financeiro:honorarios_lista")
    else:
        form = ConfirmarRecebimentoHonorarioForm(
            instance=honorario,
            initial={
                "valor_efetivo": valor_efetivo_antes,
                "data_recebida": timezone.localdate(),
            },
        )

    pendente_atual = valor_efetivo_antes - valor_recebido_antes
    pendente_corrigido = pendente_atual + calcular_correcao_honorario(
        valor_pendente=pendente_atual,
        taxa_mensal=taxa_mensal_antes,
        data_termo=data_termo_antes,
        referencia_anterior=data_recebida_antes,
        ate_data=timezone.localdate(),
    )

    return render(request, "financeiro/confirmar_recebimento_honorario.html", {
        "form": form,
        "honorario": honorario,
        "pendente_corrigido": pendente_corrigido,
        "aba_ativa": "honorarios",
        "item_ativo": "financeiro",
    })


@login_required
def documento_honorario(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    honorario = get_object_or_404(_honorarios_no_escopo(), pk=pk)
    if not honorario.documento:
        raise Http404
    return resposta_de_arquivo(request, honorario.documento)


@login_required
def cancelar_honorario(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    honorario = get_object_or_404(_honorarios_no_escopo(), pk=pk)
    if request.method == "POST":
        with transaction.atomic():
            honorario.status = "cancelado"
            honorario.save(update_fields=["status"])
            cancelar_lancamentos_futuros_do_honorario(honorario)
            registrar_atividade(
                request.user, "honorario_cancelado",
                f"Cancelou o honorário ({honorario.get_tipo_display()})",
                processo=honorario.processo,
            )
    return redirect("financeiro:honorarios_lista")


@login_required
def definir_regime_honorario(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    honorario = get_object_or_404(_honorarios_no_escopo(), pk=pk, tipo="sucumbencial")
    regime = request.POST.get("regime_pagamento", "")
    if request.method == "POST" and regime in dict(Honorario.REGIME_PAGAMENTO_CHOICES) | {"": ""}:
        honorario.regime_pagamento = regime
        honorario.save(update_fields=["regime_pagamento"])
        registrar_atividade(
            request.user, "honorario_editado",
            f"Definiu o regime de pagamento do honorário: {honorario.get_regime_pagamento_display() or 'a definir'}",
            processo=honorario.processo,
        )
    return redirect(f"{reverse('financeiro:honorarios_lista')}?aba=precatorio")


def _solicitacoes_no_escopo(request):
    qs = SolicitacaoFinanceira.objects.select_related("cliente", "processo", "solicitante", "lancamento")
    if not _tem_acesso_dados(request.user):
        qs = qs.filter(solicitante=request.user)
    return qs


_ACOES_SOLICITACAO = {
    "analisar": "em_analise",
    "aprovar": "aprovada",
    "rejeitar": "rejeitada",
    "pagar": "paga",
}


SITUACOES_SOLICITACAO = {
    "pendentes": SolicitacaoFinanceira.STATUS_ABERTOS,
    "pagas": ("paga",),
    "rejeitadas": ("rejeitada",),
}


def _vencendo_no(periodo):
    return lambda qs, hoje: solicitacoes_vencendo_no_periodo(qs, hoje, janela_do_periodo(periodo, hoje)[1])


# "Vencem no período" vai de hoje ao fim do período — o que venceu antes
# de hoje é "vencida".
FILTROS_VENCIMENTO_SOLICITACAO = {
    "vencidas": ("Vencidas", solicitacoes_vencidas),
    "dia": ("Vencem hoje", _vencendo_no("dia")),
    "semana": ("Vencem nesta semana", _vencendo_no("semana")),
    "mes": ("Vencem neste mês", _vencendo_no("mes")),
}


def _query_sem(params, *chaves):
    restantes = params.copy()
    for chave in chaves:
        restantes.pop(chave, None)
    return restantes.urlencode()


def _data_ou_none(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def _filtrar_solicitacoes(qs, params, *, tem_acesso_dados):
    """Filtros da lista de Solicitações. "Solicitado por" e "pagamento
    realizado por" só existem para quem enxerga os dados de todos —
    quem só tem nível `solicitacoes` já vê apenas as próprias."""
    if params.get("cliente"):
        qs = qs.filter(cliente_id=_parse_int(params["cliente"]) or 0)
    if params.get("processo"):
        qs = qs.filter(processo_id=_parse_int(params["processo"]) or 0)
    if tem_acesso_dados:
        if params.get("solicitante"):
            qs = qs.filter(solicitante_id=_parse_int(params["solicitante"]) or 0)
        if params.get("pago_por_usuario"):
            qs = qs.filter(pagamento_realizado_por_id=_parse_int(params["pago_por_usuario"]) or 0)
    intervalos = (
        ("solicitado_de", "criado_em__date__gte"), ("solicitado_ate", "criado_em__date__lte"),
        ("pago_de", "data_pagamento__gte"), ("pago_ate", "data_pagamento__lte"),
    )
    for parametro, campo in intervalos:
        valor = _data_ou_none(params.get(parametro))
        if valor:
            qs = qs.filter(**{campo: valor})
    vencimento = params.get("vencimento")
    if vencimento in FILTROS_VENCIMENTO_SOLICITACAO:
        qs = FILTROS_VENCIMENTO_SOLICITACAO[vencimento][1](qs, timezone.localdate())
    return qs


@login_required
def solicitacoes_lista(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    tem_acesso_dados = _tem_acesso_dados(request.user)
    base = _filtrar_solicitacoes(
        _solicitacoes_no_escopo(request), request.GET, tem_acesso_dados=tem_acesso_dados,
    )
    situacao = request.GET.get("situacao")
    if situacao not in SITUACOES_SOLICITACAO:
        situacao = "pendentes"
    contagens = {
        chave: base.filter(status__in=status).count()
        for chave, status in SITUACOES_SOLICITACAO.items()
    }
    escopo = _solicitacoes_no_escopo(request)
    return render(request, "financeiro/solicitacoes_lista.html", {
        "solicitacoes": base.filter(status__in=SITUACOES_SOLICITACAO[situacao]),
        "situacao": situacao,
        "contagens": contagens,
        "filtros": request.GET,
        "filtros_query": _query_sem(request.GET, "situacao"),
        "clientes_filtro": Cliente.objects.filter(pk__in=escopo.values("cliente_id")).order_by("nome_razao_social"),
        "processos_filtro": Processo.objects.filter(pk__in=escopo.values("processo_id")),
        "solicitantes_filtro": User.objects.filter(pk__in=escopo.values("solicitante_id")),
        "pagadores_filtro": User.objects.filter(pk__in=escopo.values("pagamento_realizado_por_id")),
        "tem_acesso_dados": tem_acesso_dados,
        "filtros_vencimento": [(chave, rotulo) for chave, (rotulo, _) in FILTROS_VENCIMENTO_SOLICITACAO.items()],
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def form_solicitacao(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied

    # Nasce a partir da aba Custas Judiciais de um processo (`?processo=`
    # no link de origem, carregado depois via campo oculto `processo_fixo`
    # em reenvios) — nesse caminho é sempre uma custa a pagar, com
    # processo/cliente travados no que originou o pedido (relato do
    # sócio: não fazia sentido deixar trocar tipo/processo/cliente aqui).
    processo_fixo_id = (
        request.POST.get("processo_fixo") if request.method == "POST" else request.GET.get("processo")
    )
    processo_fixo = Processo.objects.filter(pk=processo_fixo_id).first() if processo_fixo_id else None

    next_url = request.GET.get("next") or request.POST.get("next")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = None

    if request.method == "POST":
        form = SolicitacaoFinanceiraForm(request.POST, request.FILES, processo_fixo=processo_fixo)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.solicitante = request.user
            if solicitacao.processo and not solicitacao.cliente:
                solicitacao.cliente = solicitacao.processo.clientes.first()
            solicitacao.save()
            registrar_atividade(
                request.user, "solicitacao_criada", f"Criou a solicitação financeira {solicitacao.descricao}",
                processo=solicitacao.processo,
            )
            return redirect(next_url or "financeiro:solicitacoes_lista")
    else:
        form = SolicitacaoFinanceiraForm(processo_fixo=processo_fixo)

    return render(request, "financeiro/form_solicitacao.html", {
        "form": form,
        "processo_fixo": processo_fixo,
        "next_url": next_url,
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def editar_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    solicitacao = get_object_or_404(_solicitacoes_no_escopo(request), pk=pk)
    if solicitacao.status not in ("solicitada", "em_analise"):
        # Fora da janela de edição (PDR-0015): a partir de aprovada, a
        # solicitação já está em processamento pelo caixa geral.
        raise PermissionDenied

    # Toda solicitação tipo="pagamento" tem processo obrigatório desde a
    # criação (SolicitacaoFinanceiraForm.clean); tratá-la como travada na
    # edição replica a trava da criação via aba Custas Judiciais e evita
    # trocar o processo/cliente de uma custa já vinculada. Reembolso nunca
    # trava (mesmo se tiver processo associado), pois travar forçaria o
    # campo oculto de tipo para "pagamento" e mudaria o tipo ao salvar.
    #
    # Só trava se o cliente já salvo ainda pertence ao processo: o
    # processo pode ter perdido esse cliente (ProcessoForm permite editar
    # `clientes`) desde que a solicitação foi criada, e
    # `_travar_tipo_processo_cliente` reatribuiria silenciosamente o
    # cliente hidden para o único cliente restante do processo — sem essa
    # checagem, salvar a edição sem tocar no cliente trocaria o cliente da
    # custa por engano.
    processo_fixo = None
    if solicitacao.tipo == "pagamento" and solicitacao.processo:
        if solicitacao.processo.clientes.filter(pk=solicitacao.cliente_id).exists():
            processo_fixo = solicitacao.processo

    next_url = request.GET.get("next") or request.POST.get("next")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = None

    if request.method == "POST":
        form = SolicitacaoFinanceiraForm(
            request.POST, request.FILES, instance=solicitacao, processo_fixo=processo_fixo
        )
        if form.is_valid():
            solicitacao = form.save()
            registrar_atividade(
                request.user, "solicitacao_editada", f"Editou a solicitação financeira {solicitacao.descricao}",
                processo=solicitacao.processo,
            )
            return redirect(next_url or "financeiro:detalhe_solicitacao", pk=solicitacao.pk)
    else:
        form = SolicitacaoFinanceiraForm(instance=solicitacao, processo_fixo=processo_fixo)

    return render(request, "financeiro/form_solicitacao.html", {
        "form": form,
        "processo_fixo": processo_fixo,
        "next_url": next_url,
        "modo": "editar",
        "solicitacao": solicitacao,
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def detalhe_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    solicitacao = get_object_or_404(_solicitacoes_no_escopo(request), pk=pk)
    return render(request, "financeiro/detalhe_solicitacao.html", {
        "solicitacao": solicitacao,
        "pode_processar": _tem_acesso_dados(request.user),
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def anexo_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    solicitacao = get_object_or_404(_solicitacoes_no_escopo(request), pk=pk)
    if not solicitacao.anexo:
        raise Http404
    return resposta_de_arquivo(request, solicitacao.anexo)


@login_required
def comprovante_pagamento_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    solicitacao = get_object_or_404(_solicitacoes_no_escopo(request), pk=pk)
    if not solicitacao.comprovante_pagamento:
        raise Http404
    return resposta_de_arquivo(request, solicitacao.comprovante_pagamento)


@login_required
def processar_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    solicitacao = get_object_or_404(SolicitacaoFinanceira, pk=pk)
    if request.method == "POST":
        acao = request.POST.get("acao")
        novo_status = _ACOES_SOLICITACAO.get(acao)
        if novo_status is None or not solicitacao.pode_transicionar_para(novo_status):
            raise PermissionDenied
        if acao == "pagar" and solicitacao.tipo == "pagamento":
            pago_por = request.POST.get("pago_por")
            comprovante = request.FILES.get("comprovante_pagamento")
            if pago_por not in dict(SolicitacaoFinanceira.PAGO_POR_CHOICES) or not comprovante:
                messages.error(
                    request,
                    "Para marcar a custa como paga, anexe o comprovante de pagamento e informe "
                    "se ela foi paga pelo escritório ou pelo cliente.",
                )
                return redirect("financeiro:detalhe_solicitacao", pk=solicitacao.pk)
            solicitacao.avancar_para(
                novo_status, pago_por=pago_por, comprovante_pagamento=comprovante, usuario=request.user,
            )
        else:
            solicitacao.avancar_para(novo_status, usuario=request.user)
        registrar_atividade(
            request.user, "solicitacao_processada",
            f"Alterou a solicitação {solicitacao.descricao} para {solicitacao.get_status_display()}",
            processo=solicitacao.processo,
        )
    return redirect("financeiro:detalhe_solicitacao", pk=solicitacao.pk)
