from calendar import monthrange
from datetime import date

from django.db.models import Q
from django.utils import timezone

from .models import LancamentoFinanceiro

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
