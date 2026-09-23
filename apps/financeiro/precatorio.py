"""Sub-aba Precatório de Honorários: quais sucumbências a Fazenda paga e
qual regime (RPV/precatório) sugerir. A sugestão é só exibida — o regime
gravado é sempre escolha do usuário (`Honorario.regime_pagamento`)."""

from decimal import Decimal

from apps.processos.models import ParteProcesso

# Atualização manual a cada ano (decreto do salário mínimo).
SALARIO_MINIMO_POR_ANO = {
    2024: Decimal("1412.00"),
    2025: Decimal("1518.00"),
    2026: Decimal("1621.00"),
}

# Teto de RPV em salários mínimos. Estadual é o padrão do ADCT art. 87,
# que cede à lei própria do estado; municipal não entra por variar demais.
LIMITE_RPV_EM_SALARIOS = {"federal": 60, "estadual": 40}

ROTULO_ESFERA = {"federal": "Federal", "estadual": "Estadual/DF", "municipal": "Municipal"}

_POLOS = ("polo_ativo", "polo_passivo")


def salario_minimo_vigente(data):
    anos = [ano for ano in SALARIO_MINIMO_POR_ANO if ano <= data.year]
    return SALARIO_MINIMO_POR_ANO[max(anos)] if anos else None


def esferas_publicas_do_processo(processo):
    """Esferas dos entes públicos entre as partes dos polos — sem vínculo
    Cliente↔Parte não dá para saber qual polo é o adverso."""
    if processo is None:
        return []
    return sorted({
        parte.ente_publico for parte in processo.partes.all()
        if parte.ente_publico and ParteProcesso.GRUPO_POR_PAPEL.get(parte.papel) in _POLOS
    })


def elegivel_para_precatorio(honorario):
    if honorario.tipo != "sucumbencial" or honorario.status == "cancelado":
        return False
    return honorario.devedor_tipo == "ente_estatal" or bool(esferas_publicas_do_processo(honorario.processo))


def sugerir_regime(*, esferas, valor, data):
    """Retorna {"regime": "rpv"|"precatorio"|None, "limite": Decimal|None,
    "motivo": str}. `regime` None = sem sugestão, o usuário decide."""
    if not esferas:
        return {"regime": None, "limite": None, "motivo": "Informe a esfera do ente público na parte do processo."}
    if len(esferas) > 1:
        return {"regime": None, "limite": None, "motivo": "Mais de um ente público no processo: decida o regime."}
    esfera = esferas[0]
    salarios = LIMITE_RPV_EM_SALARIOS.get(esfera)
    if salarios is None:
        return {"regime": None, "limite": None, "motivo": "Município: o teto depende da lei municipal, decida o regime."}
    salario = salario_minimo_vigente(data)
    if salario is None or valor is None:
        return {"regime": None, "limite": None, "motivo": "Sem valor ou salário mínimo para comparar."}
    limite = salario * salarios
    regime = "precatorio" if valor > limite else "rpv"
    motivo = f"Teto de {salarios} salários mínimos"
    if esfera == "estadual":
        motivo += " (padrão; confira se o estado tem lei própria)"
    return {"regime": regime, "limite": limite, "motivo": motivo}
