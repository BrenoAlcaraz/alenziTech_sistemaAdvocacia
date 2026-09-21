from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import CustaJudicial, LancamentoFinanceiro, MembroGrupoCustas

# Recorrência "indeterminado" não tem data final — gera um horizonte
# fixo de ocorrências futuras (PDR-0021 só decidiu as periodicidades,
# não como sustentar geração indefinida sem job periódico neste stack).
HORIZONTE_OCORRENCIAS_INDETERMINADO = {"mensal": 24, "anual": 5}

# Trava de segurança para recorrência com data final muito distante —
# nunca deveria ser atingida em uso normal.
MAXIMO_OCORRENCIAS_POR_SEGURANCA = 600


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
    )


def gerar_ocorrencias(lancamento):
    """Gera as ocorrências futuras de um lançamento parcelado ou
    recorrente recém-criado, vinculadas a ele via `lancamento_origem`
    (PDR-0021). Idempotente: não gera de novo se já existem ocorrências,
    então é seguro chamar tanto na criação quanto na edição.
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
        total = lancamento.numero_parcelas or 1
        for i in range(1, total):
            data = _somar_meses(lancamento.data_vencimento, i)
            novas.append(_copiar_para_ocorrencia(lancamento, data))

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


# ── Honorário sucumbencial calculado (PDR-0029) ─────────────────────────────

JUROS_MENSAL_PESSOA = Decimal("0.01")
_CENTAVOS = Decimal("0.01")


def _meses_decorridos(inicio, ate):
    """Meses completos entre `inicio` e `ate`; sem data, não há correção."""
    if not inicio:
        return 0
    return max(0, _meses_entre(inicio, ate))


def _corrigir(valor_base, *, devedor_tipo, taxa_indice_mensal, data_correcao, data_juros, ate):
    """Devedor comum: correção monetária pelo índice + juros de 1% a.m.,
    cada um desde a sua data. Ente estatal: só a taxa (Selic), unificada,
    desde a data de correção — sem juros à parte. Taxa informada à mão."""
    taxa = (taxa_indice_mensal or Decimal("0")) / Decimal("100")
    meses_correcao = _meses_decorridos(data_correcao, ate)
    if devedor_tipo == "ente_estatal":
        return valor_base * (1 + taxa * meses_correcao)
    juros = valor_base * JUROS_MENSAL_PESSOA * _meses_decorridos(data_juros, ate)
    return valor_base + valor_base * taxa * meses_correcao + juros


def calcular_honorario_sucumbencial(honorario, ate):
    """Total do honorário na data `ate`: sucumbência corrigida + êxito
    contratual (percentual sobre o valor ganho, também corrigido). Nunca
    é gravado — o valor exibido é sempre recalculado."""
    if honorario.forma_condenacao == "percentual":
        base = (honorario.percentual or Decimal("0")) / Decimal("100") * (honorario.valor_causa or Decimal("0"))
    else:
        base = honorario.valor_fixo or Decimal("0")
    comum = {
        "devedor_tipo": honorario.devedor_tipo,
        "taxa_indice_mensal": honorario.taxa_indice_mensal,
        "ate": ate,
    }
    sucumbencia = _corrigir(
        base, data_correcao=honorario.data_correcao, data_juros=honorario.data_juros, **comum,
    )
    exito = Decimal("0")
    if honorario.exito_percentual is not None:
        ganho = _corrigir(
            honorario.exito_valor_ganho or Decimal("0"),
            data_correcao=honorario.exito_data_correcao, data_juros=honorario.exito_data_correcao, **comum,
        )
        exito = honorario.exito_percentual / Decimal("100") * ganho
    sucumbencia = sucumbencia.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
    exito = exito.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
    return {"sucumbencia": sucumbencia, "exito": exito, "total": sucumbencia + exito}
