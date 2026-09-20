from collections import defaultdict

from apps.processos.models import ParteProcesso, Processo
from apps.processos.services import normalizar_documento

from .models import Cliente

LIMITE_PROCESSOS_EM_COMUM = 3


def _processos_por_documento_no_mesmo_polo(cliente):
    """{documento normalizado: {ids de Processo}} das Partes que aparecem no
    mesmo polo (ambos ativo, ou ambos passivo) que o cliente, casando por
    CPF/CNPJ normalizado (mesmo critério de
    `apps.processos.services.patrocinio_do_processo`). Sem documento
    cadastrado no cliente, não relaciona."""
    documento_cliente = normalizar_documento(cliente.cpf_cnpj)
    if not documento_cliente:
        return {}
    partes = list(ParteProcesso.objects.only("processo_id", "cpf_cnpj", "papel"))
    polos_do_cliente = {
        (parte.processo_id, parte.grupo_visual)
        for parte in partes
        if normalizar_documento(parte.cpf_cnpj) == documento_cliente
    }
    processos_por_documento = defaultdict(set)
    for parte in partes:
        documento = normalizar_documento(parte.cpf_cnpj)
        if (
            documento not in ("", documento_cliente)
            and (parte.processo_id, parte.grupo_visual) in polos_do_cliente
        ):
            processos_por_documento[documento].add(parte.processo_id)
    return processos_por_documento


def clientes_relacionados(cliente, *, base=None):
    """Outros Clientes ativos relacionados a este.

    Duas fontes, somadas:
    1. Clientes vinculados ao mesmo Processo (`Processo.clientes`) — o
       escritório representa o mesmo lado nele, então estão no mesmo polo.
    2. Best-effort por CPF/CNPJ normalizado: clientes que aparecem como
       Parte do mesmo polo de um Processo em comum (ver
       `_processos_por_documento_no_mesmo_polo`).

    `base` restringe o universo (ex.: clientes que o usuário pode ver).
    """
    universo = Cliente.objects.filter(ativo=True) if base is None else base
    universo = universo.exclude(pk=cliente.pk)

    ids = set(
        universo.filter(processos__in=cliente.processos.all())
        .values_list("pk", flat=True)
    )

    documentos_relacionados = set(_processos_por_documento_no_mesmo_polo(cliente))
    if documentos_relacionados:
        ids.update(
            c.pk for c in universo
            if normalizar_documento(c.cpf_cnpj) in documentos_relacionados
        )

    return list(universo.filter(pk__in=ids).order_by("nome_razao_social"))


def processos_em_comum(cliente, relacionados, *, processos_visiveis):
    """Processos em comum entre `cliente` e cada cliente relacionado, pelas
    duas fontes de `clientes_relacionados`, restritos a `processos_visiveis`
    (escopo de leitura de Processos de quem consulta).

    Retorna {pk do relacionado: {"lista": [até LIMITE_PROCESSOS_EM_COMUM
    processos], "restantes": N}}; relacionados sem processo visível ficam
    fora do dicionário.
    """
    ids_por_relacionado = defaultdict(set)

    compartilhados = Processo.clientes.through.objects.filter(
        cliente_id__in=[c.pk for c in relacionados],
        processo_id__in=cliente.processos.values("pk"),
    ).values_list("cliente_id", "processo_id")
    for cliente_id, processo_id in compartilhados:
        ids_por_relacionado[cliente_id].add(processo_id)

    processos_por_documento = _processos_por_documento_no_mesmo_polo(cliente)
    for relacionado in relacionados:
        documento = normalizar_documento(relacionado.cpf_cnpj)
        ids_por_relacionado[relacionado.pk] |= processos_por_documento.get(documento, set())

    ids_todos = set().union(*ids_por_relacionado.values())
    visiveis = {
        p.pk: p for p in processos_visiveis.filter(pk__in=ids_todos).order_by("-criado_em")
    }

    resultado = {}
    for relacionado_id, ids in ids_por_relacionado.items():
        lista = [p for pk, p in visiveis.items() if pk in ids]
        if lista:
            resultado[relacionado_id] = {
                "lista": lista[:LIMITE_PROCESSOS_EM_COMUM],
                "restantes": max(len(lista) - LIMITE_PROCESSOS_EM_COMUM, 0),
            }
    return resultado
