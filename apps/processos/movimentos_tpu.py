"""
Movimentos do DataJud que viram andamento sugerido (padrão provisório da
spec de acompanhamento): lista de códigos TPU relevantes e o tipo de
andamento equivalente do catálogo. Publicação/disponibilização no DJe
(92, 1061) fica de fora — chega pelo DJEN. Códigos conferidos contra
amostra real do DataJud (TJSP, TRT2, TRF1) em 26/09/2026.
"""

import unicodedata

from .models import MovimentacaoProcessual

SENTENCA_OU_ACORDAO = "julgamento"
DECISAO = "decisao"
DESPACHO = "despacho"
AUDIENCIA = "audiencia"
TRANSITO = "transito"
JUNTADA = "juntada"
BAIXA = "baixa"
ARQUIVAMENTO = "arquivamento"
ALVARA = "alvara"

CODIGOS_RELEVANTES = {
    # Julgamento: Procedência, Improcedência, Extinção, Homologação de
    # Transação, (Não-)Provimento, Embargos de Declaração etc.
    **dict.fromkeys(
        [193, 196, 198, 200, 219, 220, 221, 230, 235, 236, 237, 238, 239, 454, 458, 459,
         461, 463, 466, 473, 871, 972, 11373, 12252, 12253, 12259, 14099],
        SENTENCA_OU_ACORDAO,
    ),
    # Decisão: tutela, liminar, gratuidade, efeito do recurso, saneamento,
    # incompetência, outras decisões.
    **dict.fromkeys(
        [3, 332, 334, 335, 339, 371, 374, 394, 785, 787, 788, 792, 804, 889, 941, 1059,
         12164, 12185, 12387],
        DECISAO,
    ),
    **dict.fromkeys([11009, 11010], DESPACHO),
    **dict.fromkeys([970, 12740, 12747, 12749, 12751], AUDIENCIA),
    848: TRANSITO,
    **dict.fromkeys([67, 85, 581], JUNTADA),
    22: BAIXA,
    **dict.fromkeys([245, 246, 861], ARQUIVAMENTO),
}
# "Expedição de documento" só conta quando o documento é alvará.
EXPEDICAO_DE_DOCUMENTO = 60

ROTULOS = {
    "sentenca": "Sentença",
    "acordao": "Acórdão",
    DECISAO: "Decisão",
    DESPACHO: "Despacho",
    AUDIENCIA: "Audiência",
    TRANSITO: "Trânsito em julgado",
    JUNTADA: "Juntada",
    BAIXA: "Baixa",
    ARQUIVAMENTO: "Arquivamento",
    ALVARA: "Expedição de alvará",
}

# Tipos equivalentes do catálogo, em ordem de preferência; o primeiro que
# existe na área do processo vence, senão "Andamento".
TIPOS_EQUIVALENTES = {
    "sentenca": ["sentenca"],
    "acordao": ["acordao"],
    DECISAO: ["decisao_interlocutoria"],
    DESPACHO: ["despacho"],
    TRANSITO: ["transito_em_julgado"],
    JUNTADA: ["juntada_de_documento"],
    ARQUIVAMENTO: ["arquivamento", "arquivamento_inquerito"],
}
TIPO_SEM_EQUIVALENTE = "andamento"

# Julgamento fora do 1º grau/juizado é acórdão (ou decisão do relator).
GRAUS_DE_PRIMEIRA_INSTANCIA = {"G1", "JE"}


def normalizado(texto):
    """Compara nomes ignorando acento, caixa e espaços."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.casefold().split())


def _categoria(movimento, grau):
    if movimento.codigo == EXPEDICAO_DE_DOCUMENTO:
        eh_alvara = any("alvara" in normalizado(c) for c in movimento.complementos)
        return ALVARA if eh_alvara else None
    categoria = CODIGOS_RELEVANTES.get(movimento.codigo)
    if categoria == SENTENCA_OU_ACORDAO:
        return "sentenca" if grau in GRAUS_DE_PRIMEIRA_INSTANCIA else "acordao"
    return categoria


def _tipo(categoria, processo):
    do_catalogo = {
        valor for _, opcoes in MovimentacaoProcessual.catalogo_por_area(processo) for valor, _ in opcoes
    }
    return next((t for t in TIPOS_EQUIVALENTES.get(categoria, []) if t in do_catalogo), TIPO_SEM_EQUIVALENTE)


def _descricao(categoria, movimento):
    rotulo = ROTULOS[categoria]
    descricao = movimento.nome
    if normalizado(rotulo) not in normalizado(movimento.nome):
        descricao = f"{rotulo}: {movimento.nome}"
    if movimento.complementos:
        descricao += f" ({', '.join(movimento.complementos)})"
    return descricao


def classificar(movimento, grau, processo):
    """(tipo, descrição) do andamento sugerido, ou None se o movimento
    não é relevante."""
    categoria = _categoria(movimento, grau)
    if categoria is None:
        return None
    return _tipo(categoria, processo), _descricao(categoria, movimento)
