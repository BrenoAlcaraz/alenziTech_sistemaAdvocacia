"""
Extração do prazo escrito no texto da intimação — padrão textual, não IA
jurídica (PDR-0037). Na dúvida não chuta: devolve None ("prazo a
definir").
"""

import html
import re
from dataclasses import dataclass

from django.utils.html import strip_tags

_NUMERO_ENTRE_PARENTESES = r"(?:\s*\([^)]{1,40}\))?"
_PRAZO_EM_DIAS = re.compile(
    r"\b(\d{1,3})" + _NUMERO_ENTRE_PARENTESES + r"\s*dias?\b(?:\s+(úteis|uteis|corridos))?"
)
# Número só por extenso ("cinco dias") não é o padrão "N dias"; entre
# parênteses depois do algarismo ("15 (quinze) dias") não casa aqui.
_NUMEROS_POR_EXTENSO = (
    "um|uma|dois|duas|três|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|treze|"
    "quatorze|catorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte|trinta|quarenta|"
    "quarenta e cinco|sessenta|noventa"
)
# Horas/meses/extenso só contam como prazo com um marcador antes ("prazo
# de", "em", "até", "dentro de"): "extratos dos últimos três meses" é
# período, não prazo.
_MARCADOR_DE_PRAZO = r"\b(?:prazo\s*:?\s*(?:de\s+)?|em\s+(?:até\s+)?|até\s+|dentro\s+de\s+)"
_OUTROS_FORMATOS = [
    re.compile(_MARCADOR_DE_PRAZO + r"\d{1,3}" + _NUMERO_ENTRE_PARENTESES + r"\s*(?:horas?|meses|mês|mes|anos?)\b"),
    re.compile(_MARCADOR_DE_PRAZO + r"(?:" + _NUMEROS_POR_EXTENSO + r")\s+(?:dias?|horas?|meses|mês|anos?)\b"),
    re.compile(r"\bprazo\s+(?:legal|de\s+lei|da\s+lei)\b"),
    re.compile(r"\bimediatamente\b"),
]


@dataclass(frozen=True)
class PrazoExtraido:
    dias: int
    corridos: bool = False


def texto_da_intimacao(conteudo_html):
    texto = html.unescape(strip_tags(conteudo_html or ""))
    return re.sub(r"\s+", " ", texto).strip()


def extrair_prazo(texto):
    """O prazo quando o texto tem exatamente um prazo em "N dias" (o mesmo
    prazo repetido conta uma vez) e nenhum em outro formato."""
    texto = texto_da_intimacao(texto).lower()
    if any(padrao.search(texto) for padrao in _OUTROS_FORMATOS):
        return None
    prazos = {
        PrazoExtraido(dias=int(numero), corridos=contagem == "corridos")
        for numero, contagem in _PRAZO_EM_DIAS.findall(texto)
    }
    if len(prazos) != 1:
        return None
    prazo = prazos.pop()
    return prazo if prazo.dias > 0 else None
