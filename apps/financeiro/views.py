from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import FileResponse, Http404, JsonResponse
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
from apps.clientes.models import Cliente
from apps.notificacoes.models import Notificacao
from apps.processos.services import processos_do_cliente
from apps.saas_tenants.storage import nome_do_arquivo

from .forms import (
    ConfirmarRecebimentoHonorarioForm,
    CustaJudicialForm,
    HonorarioForm,
    LancamentoFinanceiroForm,
    SolicitacaoFinanceiraForm,
)
from .models import CustaJudicial, Honorario, LancamentoFinanceiro, SolicitacaoFinanceira
from .services import calcular_correcao_honorario, cancelar_ocorrencias_futuras, gerar_ocorrencias


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
    "pendentes",
    "pagos",
    "atrasados",
    "receitas",
    "despesas",
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


def _lancamentos_no_escopo(user):
    qs = LancamentoFinanceiro.objects.select_related("cliente", "processo", "responsavel")
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
    ano, mes = _resolver_mes_ano(request, hoje)
    _, dias_no_mes = monthrange(ano, mes)
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, dias_no_mes)

    escopo = _lancamentos_no_escopo(request.user)
    escopo_mes = escopo.filter(data_vencimento__gte=primeiro_dia, data_vencimento__lte=ultimo_dia)

    lancamentos = escopo_mes
    if filtro == "pendentes":
        lancamentos = lancamentos.filter(status="pendente")
    elif filtro == "pagos":
        lancamentos = lancamentos.filter(status="pago")
    elif filtro == "atrasados":
        lancamentos = lancamentos.filter(
            status="pendente",
            data_vencimento__lt=hoje,
        )
    elif filtro == "receitas":
        lancamentos = lancamentos.filter(tipo="receita")
    elif filtro == "despesas":
        lancamentos = lancamentos.filter(tipo="despesa")

    a_receber = (
        escopo_mes.filter(tipo="receita", status="pendente")
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )
    a_pagar = (
        escopo_mes.filter(tipo="despesa", status="pendente")
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )
    recebido_mes = (
        escopo.filter(
            tipo="receita",
            status="pago",
            data_pagamento__year=ano,
            data_pagamento__month=mes,
        )
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )
    pago_mes = (
        escopo.filter(
            tipo="despesa",
            status="pago",
            data_pagamento__year=ano,
            data_pagamento__month=mes,
        )
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )
    saldo_atual_mes = recebido_mes - pago_mes

    resumo = {
        "a_receber": _formatar_moeda(a_receber),
        "a_pagar": _formatar_moeda(a_pagar),
        "recebido_mes": _formatar_moeda(recebido_mes),
        "pago_mes": _formatar_moeda(pago_mes),
        "saldo_previsto": _formatar_moeda(a_receber - a_pagar),
        "saldo_atual_mes": _formatar_saldo(saldo_atual_mes),
        "saldo_atual_mes_positivo": saldo_atual_mes >= 0,
    }

    ano_anterior, mes_anterior = _mes_adjacente(ano, mes, -1)
    ano_seguinte, mes_seguinte = _mes_adjacente(ano, mes, 1)

    return render(request, "financeiro/index.html", {
        "resumo": resumo,
        "lancamentos": lancamentos,
        "filtro": filtro,
        "next_url": request.get_full_path(),
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

    escopo = _lancamentos_no_escopo(request.user).filter(status="pago", data_pagamento__gte=data_inicio)
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

    return render(request, "financeiro/grafico.html", {
        "barras": barras,
        "periodo": periodo,
        "ano_exercicio": hoje.year,
        "aba_ativa": "grafico",
        "item_ativo": "financeiro",
    })


# Efeito de cada tipo de CustaJudicial sobre o saldo do cliente
# (PDR-0005): "paga_pelo_cliente" fica de fora — aparece no histórico,
# não entra na fórmula (não é crédito nem custa paga pelo escritório).
_EFEITO_SALDO_POR_TIPO = {"deposito_cliente": 1, "adiantamento": -1}


def _saldo_liquido_custas(custas):
    return sum((_EFEITO_SALDO_POR_TIPO.get(c.tipo, 0) * c.valor for c in custas), Decimal("0"))


@login_required
def custas(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    custas_qs = list(
        CustaJudicial.objects.select_related("cliente", "processo").order_by("-data", "-criado_em")
    )

    por_cliente = defaultdict(list)
    nomes_clientes = {}
    for c in custas_qs:
        if not c.cliente_id:
            continue
        nomes_clientes[c.cliente_id] = str(c.cliente)
        por_cliente[c.cliente_id].append(c)

    saldo_clientes = []
    for cid in sorted(nomes_clientes, key=lambda k: nomes_clientes[k]):
        saldo = _saldo_liquido_custas(por_cliente[cid])
        credito = saldo >= 0
        if saldo == 0:
            rotulo_saldo = "Sem saldo pendente"
        else:
            prefixo = "Crédito: " if credito else "A cobrar: "
            rotulo_saldo = prefixo + _formatar_moeda(abs(saldo))
        saldo_clientes.append({
            "cliente_id": cid,
            "cliente": nomes_clientes[cid],
            "saldo": rotulo_saldo,
            "credito": credito,
        })

    return render(request, "financeiro/custas.html", {
        "custas": custas_qs,
        "saldo_clientes": saldo_clientes,
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
        CustaJudicial.objects.filter(cliente=cliente).select_related("processo").order_by("-data", "-criado_em")
    )
    lancamentos = [c for c in custas_cliente if c.tipo in ("adiantamento", "paga_pelo_cliente")]
    creditos = [c for c in custas_cliente if c.tipo == "deposito_cliente"]
    saldo = _saldo_liquido_custas(custas_cliente)

    return render(request, "financeiro/extrato_custas_cliente.html", {
        "cliente": cliente,
        "lancamentos": lancamentos,
        "creditos": creditos,
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
        "processos": [{"id": p.id, "label": str(p)} for p in processos],
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
                lancamento.cliente = lancamento.processo.cliente
            lancamento.save()
            gerar_ocorrencias(lancamento)
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

    if request.method == "POST":
        form = LancamentoFinanceiroForm(request.POST, request.FILES, instance=lancamento)
        if form.is_valid():
            lancamento = form.save(commit=False)
            if not lancamento.responsavel:
                lancamento.responsavel = request.user
            if lancamento.processo and not lancamento.cliente:
                lancamento.cliente = lancamento.processo.cliente
            lancamento.save()
            gerar_ocorrencias(lancamento)
            return redirect("financeiro:index")
    else:
        form = LancamentoFinanceiroForm(instance=lancamento)

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
    if request.method == "POST":
        lancamento.status = "pago"
        lancamento.data_pagamento = timezone.localdate()
        lancamento.save(update_fields=["status", "data_pagamento"])
    return _redirect_seguro(request)


@login_required
def cancelar_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if request.method == "POST":
        lancamento.status = "cancelado"
        lancamento.save(update_fields=["status"])
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
    if request.method == "POST":
        cancelar_ocorrencias_futuras(lancamento)
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
    origem = getattr(lancamento, "solicitacao_origem", None)
    if origem is not None and not tem_habilitacao(
        request.user, MODULO_FINANCEIRO, HAB_FINANCEIRO_REABRIR_LANCAMENTO_PAGO
    ):
        raise PermissionDenied
    if request.method == "POST":
        lancamento.status = "pendente"
        lancamento.data_pagamento = None
        lancamento.save(update_fields=["status", "data_pagamento"])
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
    if request.method == "POST":
        lancamento.delete()
    return _redirect_seguro(request)


@login_required
def anexo_lancamento(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if not lancamento.anexo:
        raise Http404
    return FileResponse(lancamento.anexo.open("rb"), filename=nome_do_arquivo(lancamento.anexo))


@login_required
def anexar_lancamento(request, pk):
    """Ação inline da lista de lançamentos: anexa boleto/comprovante sem
    navegar para a tela de edição completa."""
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    lancamento = get_object_or_404(_lancamentos_no_escopo(request.user), pk=pk)
    if request.method == "POST" and request.FILES.get("anexo"):
        lancamento.anexo = request.FILES["anexo"]
        lancamento.save(update_fields=["anexo"])
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
            if custa.cliente_id:
                return redirect("financeiro:extrato_custas_cliente", cliente_id=custa.cliente_id)
            return redirect("financeiro:custas")
    else:
        initial = {"data": timezone.localdate()}
        if request.GET.get("cliente"):
            initial["cliente"] = request.GET["cliente"]
        form = CustaJudicialForm(initial=initial)

    return render(request, "financeiro/form_custa.html", {
        "form": form,
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
    return FileResponse(custa.anexo.open("rb"), filename=nome_do_arquivo(custa.anexo))


def _honorarios_no_escopo():
    return Honorario.objects.select_related("cliente", "processo")


@login_required
def honorarios_lista(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    return render(request, "financeiro/honorarios_lista.html", {
        "honorarios": _honorarios_no_escopo().order_by("-criado_em"),
        "is_admin": usuario_admin_escritorio(request.user),
        "aba_ativa": "honorarios",
        "item_ativo": "financeiro",
    })


@login_required
def form_honorario(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    if request.method == "POST":
        form = HonorarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("financeiro:honorarios_lista")
    else:
        form = HonorarioForm()

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
        form = HonorarioForm(request.POST, instance=honorario)
        if form.is_valid():
            form.save()
            return redirect("financeiro:honorarios_lista")
    else:
        form = HonorarioForm(instance=honorario)

    return render(request, "financeiro/form_honorario.html", {
        "form": form,
        "modo": "editar",
        "honorario": honorario,
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
    # Capturados antes de validar o form: ModelForm._post_clean() já
    # escreve os valores novos em `honorario` (mesma instância) durante
    # form.is_valid(), então ler `honorario.<campo>` depois disso
    # devolveria o valor recém-submetido, não o valor anterior.
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
                with transaction.atomic():
                    honorario_atualizado.valor_recebido = novo_valor_recebido
                    honorario_atualizado.status = (
                        "recebido" if novo_valor_recebido >= honorario_atualizado.valor_efetivo else "previsto"
                    )
                    honorario_atualizado.save()

                    LancamentoFinanceiro.objects.create(
                        tipo="receita",
                        descricao=f"Honorário — {honorario.get_tipo_display()}",
                        valor=valor_recebido_agora,
                        data_vencimento=data_recebida_nova,
                        data_pagamento=data_recebida_nova,
                        status="pago",
                        categoria="exito" if honorario.tipo == "exito" else "honorario",
                        cliente=honorario.cliente,
                        processo=honorario.processo,
                        responsavel=request.user,
                        anexo=form.cleaned_data.get("anexo"),
                    )

                    responsavel_id = honorario.processo.responsavel_id if honorario.processo_id else None
                    if responsavel_id and responsavel_id != request.user.id:
                        Notificacao.objects.create(
                            destinatario=honorario.processo.responsavel,
                            mensagem=f"Honorário recebido: \"{honorario.get_tipo_display()}\" — {honorario.processo}",
                        )
                return redirect("financeiro:honorarios_lista")
    else:
        form = ConfirmarRecebimentoHonorarioForm(
            instance=honorario,
            initial={
                "valor_efetivo": honorario.valor_efetivo or honorario.valor_estimado,
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
def cancelar_honorario(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    honorario = get_object_or_404(_honorarios_no_escopo(), pk=pk)
    if request.method == "POST":
        honorario.status = "cancelado"
        honorario.save(update_fields=["status"])
    return redirect("financeiro:honorarios_lista")


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


@login_required
def solicitacoes_lista(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    return render(request, "financeiro/solicitacoes_lista.html", {
        "solicitacoes": _solicitacoes_no_escopo(request),
        "tem_acesso_dados": _tem_acesso_dados(request.user),
        "aba_ativa": "solicitacoes",
        "item_ativo": "financeiro",
    })


@login_required
def form_solicitacao(request):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    if request.method == "POST":
        form = SolicitacaoFinanceiraForm(request.POST, request.FILES)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.solicitante = request.user
            if solicitacao.processo and not solicitacao.cliente:
                solicitacao.cliente = solicitacao.processo.cliente
            solicitacao.save()
            return redirect("financeiro:solicitacoes_lista")
    else:
        form = SolicitacaoFinanceiraForm()

    return render(request, "financeiro/form_solicitacao.html", {
        "form": form,
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
    return FileResponse(solicitacao.anexo.open("rb"), filename=nome_do_arquivo(solicitacao.anexo))


@login_required
def processar_solicitacao(request, pk):
    if not tem_permissao_modulo(request.user, MODULO_FINANCEIRO):
        raise PermissionDenied
    _exige_nivel_dados(request.user)
    solicitacao = get_object_or_404(SolicitacaoFinanceira, pk=pk)
    if request.method == "POST":
        novo_status = _ACOES_SOLICITACAO.get(request.POST.get("acao"))
        if novo_status is None or not solicitacao.pode_transicionar_para(novo_status):
            raise PermissionDenied
        solicitacao.avancar_para(novo_status)
    return redirect("financeiro:detalhe_solicitacao", pk=solicitacao.pk)
