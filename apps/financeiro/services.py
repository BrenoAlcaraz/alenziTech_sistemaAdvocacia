from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.clientes.models import Cliente

from .models import (
    CustaJudicial, Honorario, LancamentoFinanceiro, MembroGrupoCustas, SolicitacaoFinanceira,
)

# Recorrência "indeterminado" não tem data final — gera um horizonte
# fixo de ocorrências futuras (PDR-0021 só decidiu as periodicidades,
# não como sustentar geração indefinida sem job periódico neste stack).
HORIZONTE_OCORRENCIAS_INDETERMINADO = {"mensal": 24, "anual": 5}

# Trava de segurança para recorrência com data final muito distante —
# nunca deveria ser atingida em uso normal.
MAXIMO_OCORRENCIAS_POR_SEGURANCA = 600

_CENTAVOS = Decimal("0.01")


def _somar_meses(data, meses):
    """`data` deslocada em `meses`, com o dia sempre válido no mês de
    destino (ex.: 31/01 + 1 mês vira 28/02, não erro)."""
    indice = data.year * 12 + (data.month - 1) + meses
    ano, mes = indice // 12, indice % 12 + 1
    dia = min(data.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def _passo_em_meses(periodicidade):
    return 1 if periodicidade == "mensal" else 12


def _copiar_para_ocorrencia(origem, data_vencimento):
    return LancamentoFinanceiro(
        tipo=origem.tipo,
        descricao=origem.descricao,
        valor=origem.valor,
        data_vencimento=data_vencimento,
        status="pendente",
        categoria=origem.categoria,
        cliente=origem.cliente,
        processo=origem.processo,
        responsavel=origem.responsavel,
        observacoes=origem.observacoes,
        classificacao=origem.classificacao,
        periodicidade=origem.periodicidade,
        lancamento_origem=origem,
        honorario=origem.honorario,
    )


def gerar_ocorrencias(lancamento):
    """Gera as ocorrências futuras de um lançamento parcelado ou
    recorrente recém-criado, vinculadas a ele via `lancamento_origem`
    (PDR-0021). Idempotente: não gera de novo se já existem ocorrências,
    então é seguro chamar tanto na criação quanto na edição.

    Parcelado: o valor digitado é o total a parcelar. É dividido
    igualmente entre as parcelas (arredondado ao centavo); a última
    parcela absorve o resíduo do arredondamento, para a soma bater
    exatamente com o total — mesma convenção do honorário contratual
    parcelado (PDR-0032, `gerar_lancamentos_do_honorario`).
    """
    if lancamento.classificacao not in ("parcelado", "recorrente"):
        return
    if lancamento.lancamento_origem_id:
        # Uma ocorrência já gerada nunca gera as suas próprias — só a
        # origem (duracao_tipo/duracao_quantidade/data_final vivem só
        # nela) dispara a geração.
        return
    if lancamento.ocorrencias.exists():
        return

    novas = []
    if lancamento.classificacao == "parcelado":
        total_parcelas = lancamento.numero_parcelas or 1
        # str() antes de Decimal(): aceita tanto Decimal quanto valor
        # ainda não normalizado pelo form (ex.: `.objects.create(valor="...")`
        # direto, fora do fluxo de tela), sem perder precisão.
        total = Decimal(str(lancamento.valor))
        valor_parcela = (total / total_parcelas).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
        if lancamento.valor != valor_parcela:
            lancamento.valor = valor_parcela
            lancamento.save(update_fields=["valor"])
        for i in range(1, total_parcelas):
            data = _somar_meses(lancamento.data_vencimento, i)
            novas.append(_copiar_para_ocorrencia(lancamento, data))
        if novas:
            novas[-1].valor = total - valor_parcela * (total_parcelas - 1)

    elif lancamento.classificacao == "recorrente":
        passo = _passo_em_meses(lancamento.periodicidade)
        if lancamento.duracao_tipo == "quantidade":
            total = lancamento.duracao_quantidade or 1
            for i in range(1, total):
                data = _somar_meses(lancamento.data_vencimento, passo * i)
                novas.append(_copiar_para_ocorrencia(lancamento, data))
        elif lancamento.duracao_tipo == "data_final":
            i = 1
            while i <= MAXIMO_OCORRENCIAS_POR_SEGURANCA:
                data = _somar_meses(lancamento.data_vencimento, passo * i)
                if data > lancamento.duracao_data_final:
                    break
                novas.append(_copiar_para_ocorrencia(lancamento, data))
                i += 1
        else:  # indeterminado
            total = HORIZONTE_OCORRENCIAS_INDETERMINADO.get(lancamento.periodicidade, 12)
            for i in range(1, total):
                data = _somar_meses(lancamento.data_vencimento, passo * i)
                novas.append(_copiar_para_ocorrencia(lancamento, data))

    LancamentoFinanceiro.objects.bulk_create(novas)


def cancelar_ocorrencias_futuras(lancamento):
    """Cancela as ocorrências pendentes ainda não vencidas de uma
    recorrência/parcelamento — sem apagar nem reescrever ocorrências já
    pagas, canceladas ou vencidas (PDR-0021: "cancelar recorrência
    futura não apaga nem reescreve ocorrências já realizadas").
    """
    origem_id = lancamento.lancamento_origem_id or lancamento.pk
    hoje = timezone.localdate()
    LancamentoFinanceiro.objects.filter(
        Q(pk=origem_id) | Q(lancamento_origem_id=origem_id),
        status="pendente",
        data_vencimento__gte=hoje,
    ).update(status="cancelado")


def _meses_entre(inicio, fim):
    """Meses completos decorridos entre duas datas (não conta o mês
    corrente se o dia de `fim` ainda não alcançou o dia de `inicio`)."""
    meses = (fim.year - inicio.year) * 12 + (fim.month - inicio.month)
    if fim.day < inicio.day:
        meses -= 1
    return meses


def calcular_correcao_honorario(*, valor_pendente, taxa_mensal, data_termo, referencia_anterior, ate_data):
    """Correção monetária/juros de um honorário (PDR-0022) — taxa mensal
    configurada manualmente, sem integração com índice externo. Sem
    taxa_mensal/data_termo, não há correção (comportamento idêntico ao
    honorário anterior a este PDR).

    Aplica a taxa sobre `valor_pendente`, pelo tempo decorrido desde
    `data_termo` ou `referencia_anterior` (a confirmação anterior), o
    que for mais recente.
    """
    if not taxa_mensal or not data_termo:
        return Decimal("0")
    referencia = referencia_anterior or data_termo
    if referencia < data_termo:
        referencia = data_termo
    meses = _meses_entre(referencia, ate_data)
    if meses <= 0:
        return Decimal("0")
    return valor_pendente * (taxa_mensal / Decimal("100")) * meses


# ── Integração Lançamentos ↔ Creditar (custas judiciais do cliente) ─────────

def _deve_creditar_custas(lancamento, *, de_grupo=False):
    return (
        lancamento.tipo == "receita"
        and lancamento.categoria == "reembolso"
        and lancamento.status == "pago"
        and (de_grupo or lancamento.cliente_id is not None)
    )


def sincronizar_credito_de_reembolso(lancamento):
    """Receita "Reembolso" já recebida de um cliente vira crédito nas
    custas judiciais dele; se deixa de valer (reaberta, cancelada, outra
    categoria, sem cliente), o crédito some. O lançamento é a origem.
    O crédito de um grupo (sem cliente) segue o mesmo ciclo, mas mantém
    o vínculo com o grupo."""
    existente = CustaJudicial.objects.filter(lancamento=lancamento).first()
    de_grupo = existente is not None and existente.grupo_id is not None
    if not _deve_creditar_custas(lancamento, de_grupo=de_grupo):
        if existente:
            existente.delete()
        return
    campos = {
        "descricao": lancamento.descricao,
        "valor": lancamento.valor,
        "data": lancamento.data_pagamento or lancamento.data_vencimento,
    }
    if not de_grupo:
        campos.update(cliente=lancamento.cliente, processo=lancamento.processo)
    if existente:
        for nome, valor in campos.items():
            setattr(existente, nome, valor)
        existente.save(update_fields=list(campos))
    else:
        CustaJudicial.objects.create(tipo="deposito_cliente", lancamento=lancamento, **campos)


def registrar_credito_cliente(*, cliente, valor, data, descricao, processo=None, anexo=None, responsavel=None):
    """Creditar do cliente: uma única receita "Reembolso" no financeiro
    geral que nasce já com o crédito correspondente nas custas dele.
    Devolve o crédito (`CustaJudicial` de depósito)."""
    with transaction.atomic():
        lancamento = LancamentoFinanceiro.objects.create(
            tipo="receita", categoria="reembolso", status="pago",
            descricao=descricao, valor=valor,
            data_vencimento=data, data_pagamento=data,
            cliente=cliente, processo=processo, responsavel=responsavel,
        )
        credito = CustaJudicial.objects.get(lancamento=lancamento)
        if anexo:
            credito.anexo = anexo
            credito.save(update_fields=["anexo"])
    return credito


def registrar_credito_grupo(*, grupo, valor, data, descricao, anexo=None, responsavel=None):
    """Creditar do grupo: receita "Reembolso" no financeiro geral (sem
    cliente) com o crédito correspondente no saldo do grupo."""
    with transaction.atomic():
        lancamento = LancamentoFinanceiro.objects.create(
            tipo="receita", categoria="reembolso", status="pago",
            descricao=descricao, valor=valor,
            data_vencimento=data, data_pagamento=data, responsavel=responsavel,
        )
        return CustaJudicial.objects.create(
            tipo="deposito_cliente", lancamento=lancamento, grupo=grupo,
            descricao=descricao, valor=valor, data=data, anexo=anexo,
        )


def reembolsar_custa(custa, *, data, comprovante, responsavel=None):
    """Cliente reembolsou uma custa adiantada pelo escritório: cria o
    crédito correspondente (com o comprovante) e marca a custa como
    reembolsada — o saldo devedor do cliente cai e o valor deixa de
    contar como despesa do escritório."""
    if not custa.pode_reembolsar:
        raise ValueError("Só custa adiantada pelo escritório e ainda não reembolsada pode ser reembolsada.")
    with transaction.atomic():
        credito = registrar_credito_cliente(
            cliente=custa.cliente, valor=custa.valor, data=data,
            descricao=f"Reembolso — {custa.descricao}",
            processo=custa.processo, anexo=comprovante, responsavel=responsavel,
        )
        custa.reembolsada_por = credito
        custa.save(update_fields=["reembolsada_por"])
    return credito


# ── Saldo de custas: cliente individual e grupo ─────────────────────────────

# Efeito de cada tipo de CustaJudicial sobre o saldo (PDR-0005):
# "paga_pelo_cliente" fica de fora — aparece no histórico, não entra na
# fórmula (não é crédito nem custa paga pelo escritório).
_EFEITO_SALDO_POR_TIPO = {"deposito_cliente": 1, "adiantamento": -1}


def saldo_liquido_custas(custas):
    return sum((_EFEITO_SALDO_POR_TIPO.get(c.tipo, 0) * c.valor for c in custas), Decimal("0"))


def saldo_individual_do_cliente(cliente):
    """Só as custas sem grupo: o que foi debitado do saldo de um grupo
    nunca mexe no saldo individual do membro."""
    return saldo_liquido_custas(CustaJudicial.objects.filter(cliente=cliente, grupo__isnull=True))


def saldo_do_grupo(grupo):
    return saldo_liquido_custas(CustaJudicial.objects.filter(grupo=grupo))


def saldo_de_custas_do(*, cliente=None, grupo=None):
    """Saldo que um lançamento para `cliente`/`grupo` movimenta: o do
    grupo (escolhido, ou o do grupo do cliente membro) ou o individual.
    Devolve `(dono, saldo)`, ou `(None, None)` sem cliente nem grupo."""
    if grupo is None and cliente is not None:
        membro = MembroGrupoCustas.objects.select_related("grupo").filter(cliente=cliente).first()
        grupo = membro.grupo if membro else None
    if grupo is not None:
        return grupo, saldo_do_grupo(grupo)
    if cliente is not None:
        return cliente, saldo_individual_do_cliente(cliente)
    return None, None


def adicionar_membro_ao_grupo(grupo, cliente):
    """Um cliente entra em no máximo um grupo e só com saldo individual
    zero (não há migração de saldo para o grupo)."""
    with transaction.atomic():
        if MembroGrupoCustas.objects.filter(cliente=cliente).exists():
            raise ValueError("Este cliente já pertence a um grupo.")
        if saldo_individual_do_cliente(cliente) != 0:
            raise ValueError("O saldo individual do cliente precisa estar zerado para entrar em um grupo.")
        return MembroGrupoCustas.objects.create(grupo=grupo, cliente=cliente)


def remover_membro_do_grupo(membro):
    """Só sem lançamentos vinculados ao membro no grupo — o histórico
    nunca é reescrito."""
    if CustaJudicial.objects.filter(grupo=membro.grupo, cliente=membro.cliente).exists():
        raise ValueError("Este membro tem lançamentos no grupo e não pode ser removido.")
    membro.delete()


def excluir_grupo(grupo):
    if CustaJudicial.objects.filter(grupo=grupo).exists():
        raise ValueError("O grupo tem lançamentos vinculados e não pode ser apagado.")
    grupo.delete()


# ── Totais e análises: reembolso/custas de cliente não são receita/despesa ─

def sem_reembolso_de_cliente(lancamentos):
    return lancamentos.exclude(tipo="receita", categoria="reembolso")


def sem_custas_do_cliente(lancamentos):
    return lancamentos.exclude(
        tipo="despesa", cliente__isnull=False,
        categoria__in=LancamentoFinanceiro.CATEGORIAS_CUSTA_DO_CLIENTE,
    )


def lancamentos_operacionais(lancamentos):
    """Lançamentos que contam como receita/despesa do escritório. Reembolso
    de cliente e custas do cliente ficam de fora: entram só como saldo
    devedor (`custas_a_recuperar`)."""
    return sem_custas_do_cliente(sem_reembolso_de_cliente(lancamentos))


def custas_a_recuperar(*, inicio=None, fim=None):
    """Saldo devedor dos clientes e dos grupos na janela — custas
    adiantadas pelo escritório menos o que foi creditado/reembolsado. Custa
    paga direto pelo cliente não entra. O que pertence a um grupo conta
    pelo saldo do grupo, nunca pelo do membro. Devolve
    `{("cliente", id) | ("grupo", id): valor}` só dos devedores."""
    custas = CustaJudicial.objects.filter(tipo__in=("adiantamento", "deposito_cliente")).filter(
        Q(grupo__isnull=False) | Q(cliente__isnull=False),
    )
    if inicio:
        custas = custas.filter(data__gte=inicio)
    if fim:
        custas = custas.filter(data__lte=fim)
    saldo = defaultdict(Decimal)
    for linha in custas.values("cliente_id", "grupo_id", "tipo").annotate(total=Sum("valor")):
        dono = ("grupo", linha["grupo_id"]) if linha["grupo_id"] else ("cliente", linha["cliente_id"])
        efeito = -1 if linha["tipo"] == "adiantamento" else 1
        saldo[dono] += efeito * linha["total"]
    return {dono: -valor for dono, valor in saldo.items() if valor < 0}


def total_custas_a_recuperar(*, inicio=None, fim=None):
    return sum(custas_a_recuperar(inicio=inicio, fim=fim).values(), Decimal("0"))


def _soma(lancamentos):
    return lancamentos.aggregate(total=Sum("valor"))["total"] or Decimal("0")


def totais_do_mes(escopo, ano, mes, *, incluir_custas):
    """Cards do mês: a receber, a pagar, recebido e pago. `incluir_custas`
    soma ao "pago" as custas adiantadas ainda não reembolsadas do mês —
    dado global do escritório, então só para quem enxerga todos os dados."""
    primeiro = date(ano, mes, 1)
    ultimo = date(ano, mes, monthrange(ano, mes)[1])
    operacionais = lancamentos_operacionais(escopo)
    no_mes = operacionais.filter(data_vencimento__gte=primeiro, data_vencimento__lte=ultimo)
    pagos_no_mes = operacionais.filter(
        status="pago", data_pagamento__year=ano, data_pagamento__month=mes,
    )
    pago = _soma(pagos_no_mes.filter(tipo="despesa"))
    if incluir_custas:
        pago += total_custas_a_recuperar(inicio=primeiro, fim=ultimo)
    return {
        "a_receber": _soma(no_mes.filter(tipo="receita", status="pendente")),
        "a_pagar": _soma(no_mes.filter(tipo="despesa", status="pendente")),
        "recebido": _soma(pagos_no_mes.filter(tipo="receita")),
        "pago": pago,
    }


def saldo_previsto(totais):
    """Saldo previsto do mês (PDR-0029) sobre o resultado de `totais_do_mes`."""
    return totais["a_receber"] + totais["recebido"] - totais["a_pagar"] - totais["pago"]


def vencendo_hoje(lancamentos, tipo, hoje):
    return lancamentos.filter(tipo=tipo, status="pendente", data_vencimento=hoje)


def atrasados(lancamentos, hoje, tipo=None):
    """Pendentes vencidos antes de hoje, de qualquer mês."""
    qs = lancamentos.filter(status="pendente", data_vencimento__lt=hoje)
    return qs.filter(tipo=tipo) if tipo else qs


def _total_e_quantidade(lancamentos):
    agregado = lancamentos.aggregate(total=Sum("valor"), quantidade=Count("id"))
    return {"total": agregado["total"] or Decimal("0"), "quantidade": agregado["quantidade"]}


def pendencias_do_dia(escopo, hoje):
    """Cards "A pagar/A receber hoje" do Painel: o que vence hoje e,
    separado, o que já está atrasado — mesmos conjuntos dos filtros da
    lista de Lançamentos para onde cada card leva."""
    return {
        chave: {
            "hoje": _total_e_quantidade(vencendo_hoje(escopo, tipo, hoje)),
            "atrasados": _total_e_quantidade(atrasados(escopo, hoje, tipo)),
        }
        for chave, tipo in (("a_pagar", "despesa"), ("a_receber", "receita"))
    }


_CATEGORIAS_HONORARIO = ("honorario", "honorario_sucumbencia")


def _pendente_do_honorario_unico(honorario):
    esperado = honorario.valor_efetivo or honorario.valor_estimado or Decimal("0")
    return max(esperado - (honorario.valor_recebido or Decimal("0")), Decimal("0"))


def honorarios_do_mes(ano, mes):
    """Card "Honorários do mês" do Painel (dado global do escritório).
    Receitas de honorário com vencimento no mês — o que já foi pago
    entra em recebido e em previsto — mais o saldo pendente do contratual
    de valor único ainda previsto no mês, que só vira lançamento ao ser
    confirmado (sem dupla contagem: esse não tem lançamentos vinculados).
    Sucumbência e êxito sem lançamento ficam de fora."""
    primeiro = date(ano, mes, 1)
    ultimo = date(ano, mes, monthrange(ano, mes)[1])
    receitas = LancamentoFinanceiro.objects.filter(
        tipo="receita", categoria__in=_CATEGORIAS_HONORARIO,
        data_vencimento__gte=primeiro, data_vencimento__lte=ultimo,
    )
    recebido = _soma(receitas.filter(status="pago"))
    pendente = _soma(receitas.filter(status="pendente"))
    unicos = Honorario.objects.filter(
        tipo__in=("contratual", "outro"), status="previsto",
        data_prevista__gte=primeiro, data_prevista__lte=ultimo,
    ).exclude(modalidade="exito").exclude(classificacao__in=("parcelado", "recorrente"))
    pendente += sum(
        (_pendente_do_honorario_unico(h) for h in unicos if not h.lancamentos.exists()),
        Decimal("0"),
    )
    return {"previsto": recebido + pendente, "recebido": recebido}


def custas_em_debito():
    """Card "Custas a cobrar" do Painel: os mesmos devedores que a tela de
    Custas lista no filtro "Em débito" — grupos e clientes ativos fora de
    grupo com saldo negativo."""
    devedores = custas_a_recuperar()
    ids_clientes = [id_ for tipo, id_ in devedores if tipo == "cliente"]
    listados = set(
        Cliente.objects.filter(pk__in=ids_clientes, ativo=True, grupo_custas__isnull=True)
        .values_list("pk", flat=True)
    )
    valores = [
        valor for (tipo, id_), valor in devedores.items() if tipo == "grupo" or id_ in listados
    ]
    return {"total": sum(valores, Decimal("0")), "quantidade": len(valores)}


def solicitacoes_vencidas(solicitacoes, hoje):
    return solicitacoes.filter(
        status__in=SolicitacaoFinanceira.STATUS_ABERTOS, vencimento__lt=hoje,
    )


def solicitacoes_vencendo_hoje(solicitacoes, hoje):
    return solicitacoes.filter(
        status__in=SolicitacaoFinanceira.STATUS_ABERTOS, vencimento=hoje,
    )


def resumo_solicitacoes_abertas(solicitacoes, hoje):
    """Fila de solicitações em aberto do Painel, pela etapa que falta."""
    abertas = solicitacoes.filter(status__in=SolicitacaoFinanceira.STATUS_ABERTOS)
    agregado = abertas.aggregate(total=Sum("valor"), quantidade=Count("id"))
    return {
        "quantidade": agregado["quantidade"],
        "total": agregado["total"] or Decimal("0"),
        "aguardando_analise": abertas.filter(status__in=("solicitada", "em_analise")).count(),
        "aguardando_pagamento": abertas.filter(status="aprovada").count(),
        "vencidas": solicitacoes_vencidas(solicitacoes, hoje).count(),
        "vencem_hoje": solicitacoes_vencendo_hoje(solicitacoes, hoje).count(),
    }


def inicio_da_janela(janela, hoje):
    """Início da janela de análise: 'sempre' (None), '12meses' ou 'exercicio'."""
    if janela == "exercicio":
        return date(hoje.year, 1, 1)
    if janela == "12meses":
        indice = hoje.year * 12 + (hoje.month - 1) - 11
        return date(indice // 12, indice % 12 + 1, 1)
    return None


def _ranking(linhas):
    """[(rótulo, valor)] → barras ordenadas, com percentual sobre o maior."""
    linhas = sorted(((r, v) for r, v in linhas if v), key=lambda x: -x[1])
    maior = linhas[0][1] if linhas else Decimal("1")
    total = sum((v for _, v in linhas), Decimal("0"))
    return {
        "total": total,
        "linhas": [
            {"rotulo": r, "valor": v, "pct": int(v / maior * 100)} for r, v in linhas
        ],
    }


def analise_de_dados(escopo, *, inicio, incluir_custas):
    """Fontes de receita/despesa, receita por área e por cliente — só o
    realizado (pago), sem reembolso de cliente e com as custas adiantadas
    não reembolsadas entrando como despesa (saldo devedor dos clientes)."""
    from apps.processos.models import Processo

    pagos = lancamentos_operacionais(escopo).filter(status="pago")
    if inicio:
        pagos = pagos.filter(data_pagamento__gte=inicio)
    receitas = pagos.filter(tipo="receita")
    despesas = pagos.filter(tipo="despesa")

    categorias = dict(LancamentoFinanceiro.CATEGORIA_CHOICES)
    fontes_receita = [
        (categorias.get(linha["categoria"], linha["categoria"]), linha["total"])
        for linha in receitas.values("categoria").annotate(total=Sum("valor"))
    ]
    fontes_despesa = [
        (categorias.get(linha["categoria"], linha["categoria"]), linha["total"])
        for linha in despesas.values("categoria").annotate(total=Sum("valor"))
    ]
    if incluir_custas:
        devedor = total_custas_a_recuperar(inicio=inicio)
        if devedor:
            fontes_despesa.append(("Custas adiantadas (a reembolsar)", devedor))

    areas = dict(Processo.AREAS_CHOICES)
    por_area = [
        (areas.get(linha["processo__area_direito"], linha["processo__area_direito"]) or "Sem processo vinculado",
         linha["total"])
        for linha in receitas.values("processo__area_direito").annotate(total=Sum("valor"))
    ]
    por_cliente = [
        (linha["cliente__nome_razao_social"] or "Sem cliente", linha["total"])
        for linha in receitas.values("cliente__nome_razao_social").annotate(total=Sum("valor"))
    ]
    return {
        "fontes_receita": _ranking(fontes_receita),
        "fontes_despesa": _ranking(fontes_despesa),
        "receita_por_area": _ranking(por_area),
        "receita_por_cliente": _ranking(por_cliente),
    }


# ── Honorário contratual: lançamentos gerados (PDR-0032) ────────────────────

def gerar_lancamentos_do_honorario(honorario, *, responsavel=None):
    """Honorário contratual parcelado/recorrente → receitas pendentes
    (categoria Honorários) vinculadas a ele, pelo gerador do PDR-0021.
    Idempotente: só gera se o honorário ainda não tem lançamentos.
    `valor_estimado` é sempre o total (parcelado ou não); no
    parcelamento, é o próprio `gerar_ocorrencias` que divide entre as
    parcelas e absorve o arredondamento na última."""
    if not honorario.recebimento_por_lancamentos or honorario.lancamentos.exists():
        return
    alvo = honorario.processo or honorario.cliente
    with transaction.atomic():
        origem = LancamentoFinanceiro.objects.create(
            tipo="receita",
            descricao=f"Honorário — {honorario.get_tipo_display()}" + (f" — {alvo}" if alvo else ""),
            valor=honorario.valor_estimado,
            data_vencimento=honorario.data_prevista,
            categoria="honorario",
            cliente=honorario.cliente,
            processo=honorario.processo,
            responsavel=responsavel,
            classificacao=honorario.classificacao,
            periodicidade=honorario.periodicidade,
            numero_parcelas=honorario.numero_parcelas,
            duracao_tipo=honorario.duracao_tipo,
            duracao_quantidade=honorario.duracao_quantidade,
            duracao_data_final=honorario.duracao_data_final,
            honorario=honorario,
        )
        gerar_ocorrencias(origem)


def cancelar_lancamentos_futuros_do_honorario(honorario):
    """Honorário cancelado: cancela só as receitas pendentes ainda não
    vencidas, sem reescrever o que já foi pago ou venceu (mesma regra do
    PDR-0021)."""
    LancamentoFinanceiro.objects.filter(
        honorario=honorario, status="pendente", data_vencimento__gte=timezone.localdate(),
    ).update(status="cancelado")


# ── Honorário sucumbencial calculado (PDR-0029) ─────────────────────────────

JUROS_MENSAL_PESSOA = Decimal("0.01")


def _meses_decorridos(inicio, ate, fim=None):
    """Meses completos entre `inicio` e `ate` (limitado por `fim`, quando
    há); sem data inicial, não há correção."""
    if not inicio:
        return 0
    if fim and fim < ate:
        ate = fim
    return max(0, _meses_entre(inicio, ate))


def _corrigir(valor_base, *, devedor_tipo, taxa_indice_mensal, data_correcao, data_juros, ate,
              data_correcao_fim=None, data_juros_fim=None):
    """Devedor comum: correção monetária pelo índice + juros de 1% a.m.,
    cada um no seu intervalo de incidência. Ente estatal: só a taxa
    (Selic), unificada, no intervalo da correção — sem juros à parte. Taxa
    informada à mão."""
    taxa = (taxa_indice_mensal or Decimal("0")) / Decimal("100")
    meses_correcao = _meses_decorridos(data_correcao, ate, data_correcao_fim)
    if devedor_tipo == "ente_estatal":
        return valor_base * (1 + taxa * meses_correcao)
    juros = valor_base * JUROS_MENSAL_PESSOA * _meses_decorridos(data_juros, ate, data_juros_fim)
    return valor_base + valor_base * taxa * meses_correcao + juros


def _base_da_sucumbencia(honorario):
    fixo = honorario.valor_fixo or Decimal("0")
    percentual = (honorario.percentual or Decimal("0")) / Decimal("100") * (honorario.valor_condenacao or Decimal("0"))
    if honorario.forma_condenacao == "percentual":
        return percentual
    if honorario.forma_condenacao == "fixo_percentual":
        return fixo + percentual
    return fixo


def contratos_de_exito_pelo_ganho(processo):
    """Contratos de êxito "pelo ganho" ativos do processo — os que a
    sucumbência avisa. "Pela economia" não entra (o cliente não recebe)."""
    if processo is None:
        return []
    return list(
        Honorario.objects.filter(
            processo=processo, tipo="contratual", modalidade__in=("exito", "valor_exito"), exito_base="ganho",
        ).exclude(status="cancelado")
    )


def calcular_honorario_sucumbencial(honorario, ate, contratos_exito=()):
    """Total do honorário na data `ate`: sucumbência corrigida + êxito.
    Êxito = o embutido em registros anteriores ao PDR-0032 + uma linha por
    contrato de êxito "pelo ganho" do processo (`contratos_exito`), sobre a
    condenação corrigida — sem condenação informada não há base e não há
    linha. Nunca é gravado — o valor exibido é sempre recalculado."""
    comum = {
        "devedor_tipo": honorario.devedor_tipo,
        "taxa_indice_mensal": honorario.taxa_indice_mensal,
        "ate": ate,
    }
    intervalos = {
        "data_correcao": honorario.data_correcao, "data_correcao_fim": honorario.data_correcao_fim,
        "data_juros": honorario.data_juros, "data_juros_fim": honorario.data_juros_fim,
    }
    sucumbencia = _corrigir(_base_da_sucumbencia(honorario), **intervalos, **comum)
    exito = Decimal("0")
    if honorario.exito_percentual is not None:
        ganho = _corrigir(
            honorario.exito_valor_ganho or Decimal("0"),
            data_correcao=honorario.exito_data_correcao, data_juros=honorario.exito_data_correcao, **comum,
        )
        exito = honorario.exito_percentual / Decimal("100") * ganho
    linhas = []
    if honorario.valor_condenacao:
        condenacao = _corrigir(honorario.valor_condenacao, **intervalos, **comum)
        for contrato in contratos_exito:
            valor = (contrato.exito_percentual / Decimal("100") * condenacao).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
            linhas.append({"contrato": contrato, "percentual": contrato.exito_percentual, "valor": valor})
    sucumbencia = sucumbencia.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
    exito = exito.quantize(_CENTAVOS, rounding=ROUND_HALF_UP) + sum((l["valor"] for l in linhas), Decimal("0"))
    return {"sucumbencia": sucumbencia, "exito": exito, "exito_contratos": linhas, "total": sucumbencia + exito}
