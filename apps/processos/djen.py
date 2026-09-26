"""
Cliente do DJEN (Comunica PJe): comunicações publicadas para um número de
processo num período. API pública, sem autenticação.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

ITENS_POR_PAGINA = 100
# Guarda contra resposta inesperada; um processo não tem tantas
# comunicações num período de dias.
MAX_PAGINAS = 20
TIMEOUT_SEGUNDOS = 30


class ErroDjen(Exception):
    pass


@dataclass(frozen=True)
class Advogado:
    nome: str
    oab: str
    uf: str


@dataclass(frozen=True)
class Comunicacao:
    id: int
    hash: str
    data_disponibilizacao: date
    tipo: str
    texto: str
    link: str
    ativo: bool
    orgao: str = ""
    destinatarios: tuple = field(default_factory=tuple)
    advogados: tuple = field(default_factory=tuple)


def _comunicacao(item):
    advogados = tuple(
        Advogado(
            nome=(a.get("advogado") or {}).get("nome") or "",
            oab=str((a.get("advogado") or {}).get("numero_oab") or ""),
            uf=(a.get("advogado") or {}).get("uf_oab") or "",
        )
        for a in item.get("destinatarioadvogados") or []
    )
    return Comunicacao(
        id=int(item["id"]),
        hash=str(item.get("hash") or item["id"]),
        data_disponibilizacao=date.fromisoformat(item["data_disponibilizacao"]),
        tipo=item.get("tipoComunicacao") or "",
        texto=item.get("texto") or "",
        link=item.get("link") or "",
        ativo=bool(item.get("ativo", True)),
        orgao=item.get("nomeOrgao") or "",
        destinatarios=tuple(d.get("nome") or "" for d in item.get("destinatarios") or []),
        advogados=advogados,
    )


def _get(params):
    url = f"{settings.DJEN_URL}?{urlencode(params)}"
    # O DJEN não responde ao User-Agent padrão do urllib (conferido em
    # 26/09/2026: a conexão fica pendurada até o timeout).
    requisicao = Request(url, headers={"Accept": "application/json", "User-Agent": "LawSystem-Acompanhamento/1.0"})
    try:
        with urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except (OSError, ValueError) as erro:
        raise ErroDjen(f"DJEN indisponível: {erro}") from erro


def buscar_comunicacoes(numero_processo, inicio, fim):
    """Comunicações do número (só dígitos) disponibilizadas entre `inicio`
    e `fim`, inclusive."""
    comunicacoes = []
    for pagina in range(1, MAX_PAGINAS + 1):
        dados = _get({
            "numeroProcesso": numero_processo,
            "dataDisponibilizacaoInicio": inicio.isoformat(),
            "dataDisponibilizacaoFim": fim.isoformat(),
            "pagina": pagina,
            "itensPorPagina": ITENS_POR_PAGINA,
        })
        itens = dados.get("items") or []
        try:
            comunicacoes.extend(_comunicacao(item) for item in itens)
        except (KeyError, TypeError, ValueError) as erro:
            raise ErroDjen(f"Resposta do DJEN fora do contrato: {erro}") from erro
        if len(itens) < ITENS_POR_PAGINA or len(comunicacoes) >= int(dados.get("count") or 0):
            return comunicacoes
    return comunicacoes
