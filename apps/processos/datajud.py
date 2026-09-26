"""
Cliente do DataJud (API Pública do CNJ): registros de um número de
processo — um por grau/órgão em que tramitou — com órgão julgador, grau
e movimentos (código TPU, nome, data). Não traz texto nem prazo.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_timezone
from urllib.request import Request, urlopen

from django.conf import settings

TIMEOUT_SEGUNDOS = 60
# Um número tem um registro por grau/órgão; mais que isso é resposta
# inesperada.
MAX_REGISTROS = 20

# Segmento TR do número CNJ na Justiça Estadual (J=8) e Eleitoral (J=6).
UF_POR_TR = {
    "01": "ac", "02": "al", "03": "ap", "04": "am", "05": "ba", "06": "ce",
    "07": "df", "08": "es", "09": "go", "10": "ma", "11": "mt", "12": "ms",
    "13": "mg", "14": "pa", "15": "pb", "16": "pr", "17": "pe", "18": "pi",
    "19": "rj", "20": "rn", "21": "rs", "22": "ro", "23": "rr", "24": "sc",
    "25": "se", "26": "sp", "27": "to",
}
TJM_POR_TR = {"13": "tjmmg", "21": "tjmrs", "26": "tjmsp"}


class ErroDatajud(Exception):
    pass


@dataclass(frozen=True)
class Movimento:
    codigo: int
    nome: str
    data_hora: datetime
    complementos: tuple = field(default_factory=tuple)

    @property
    def chave(self):
        # O DataJud repete o mesmo movimento (mesmo código e data).
        return f"{self.codigo}|{self.data_hora.isoformat()}"


@dataclass(frozen=True)
class RegistroDatajud:
    grau: str
    orgao_julgador: str
    movimentos: tuple = field(default_factory=tuple)


def alias_do_tribunal(numero):
    """Índice do DataJud deduzido dos segmentos J.TR do número CNJ (só
    dígitos). None quando o segmento não tem índice (STF, CNJ)."""
    justica, tr = numero[13], numero[14:16]
    if justica == "8":
        uf = UF_POR_TR.get(tr)
        return None if uf is None else ("tjdft" if uf == "df" else f"tj{uf}")
    if justica == "6":
        uf = UF_POR_TR.get(tr)
        return f"tre-{uf}" if uf else None
    if justica == "5":
        return "tst" if tr == "00" else f"trt{int(tr)}"
    if justica == "4":
        return f"trf{int(tr)}" if tr != "00" else None
    if justica == "9":
        return TJM_POR_TR.get(tr)
    return {"3": "stj", "7": "stm"}.get(justica)


def _data_hora(valor):
    try:
        data = datetime.fromisoformat(valor)
    except ValueError:
        data = datetime.strptime(valor, "%Y%m%d%H%M%S")
    return data if data.tzinfo else data.replace(tzinfo=dt_timezone.utc)


def _movimentos(itens):
    # Alguns tribunais mandam movimento sem código; não há o que classificar.
    return tuple(
        Movimento(
            codigo=int(item["codigo"]),
            nome=item.get("nome") or "",
            data_hora=_data_hora(item["dataHora"]),
            complementos=tuple(
                c.get("nome") or "" for c in item.get("complementosTabelados") or [] if c.get("nome")
            ),
        )
        for item in itens or []
        if item.get("codigo") is not None and item.get("dataHora")
    )


def _registro(fonte):
    return RegistroDatajud(
        grau=fonte.get("grau") or "",
        orgao_julgador=(fonte.get("orgaoJulgador") or {}).get("nome") or "",
        movimentos=_movimentos(fonte.get("movimentos")),
    )


def _post(alias, corpo):
    chave = settings.DATAJUD_API_KEY
    if not chave:
        raise ErroDatajud("Chave do DataJud não configurada (DATAJUD_API_KEY)")
    requisicao = Request(
        f"{settings.DATAJUD_URL}/api_publica_{alias}/_search",
        data=json.dumps(corpo).encode("utf-8"),
        headers={
            "Authorization": f"APIKey {chave}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "LawSystem-Acompanhamento/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(requisicao, timeout=TIMEOUT_SEGUNDOS) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except (OSError, ValueError) as erro:
        raise ErroDatajud(f"DataJud indisponível: {erro}") from erro


def buscar_processo(numero_processo):
    """Registros do número (só dígitos); lista vazia se o DataJud não o
    encontra. None se o tribunal do número não está no DataJud."""
    alias = alias_do_tribunal(numero_processo)
    if alias is None:
        return None
    dados = _post(alias, {"size": MAX_REGISTROS, "query": {"match": {"numeroProcesso": numero_processo}}})
    # Sobrecarga do DataJud volta como JSON de erro, não como HTTP de erro
    # (conferido em 26/09/2026).
    if "error" in dados or "hits" not in dados:
        raise ErroDatajud(f"Resposta do DataJud fora do contrato: {str(dados)[:300]}")
    try:
        return [_registro(hit["_source"]) for hit in dados["hits"]["hits"]]
    except (KeyError, TypeError, ValueError) as erro:
        raise ErroDatajud(f"Resposta do DataJud fora do contrato: {erro}") from erro
