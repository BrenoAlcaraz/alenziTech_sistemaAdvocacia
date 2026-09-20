from apps.processos.models import ParteProcesso
from apps.processos.services import normalizar_documento

from .models import Cliente


def clientes_relacionados(cliente, *, base=None):
    """Outros Clientes ativos relacionados a este.

    Duas fontes, somadas:
    1. Clientes vinculados ao mesmo Processo (`Processo.clientes`) — o
       escritório representa o mesmo lado nele, então estão no mesmo polo.
    2. Best-effort por CPF/CNPJ normalizado (mesmo critério de
       `apps.processos.services.patrocinio_do_processo`): clientes que
       aparecem como Parte do mesmo polo (ambos ativo, ou ambos passivo)
       de um Processo em comum. Sem documento cadastrado, não relaciona.

    `base` restringe o universo (ex.: clientes que o usuário pode ver).
    """
    universo = Cliente.objects.filter(ativo=True) if base is None else base
    universo = universo.exclude(pk=cliente.pk)

    ids = set(
        universo.filter(processos__in=cliente.processos.all())
        .values_list("pk", flat=True)
    )

    documento_cliente = normalizar_documento(cliente.cpf_cnpj)
    if documento_cliente:
        partes = list(ParteProcesso.objects.only("processo_id", "cpf_cnpj", "papel"))
        processos_do_cliente = {
            (parte.processo_id, parte.grupo_visual)
            for parte in partes
            if normalizar_documento(parte.cpf_cnpj) == documento_cliente
        }
        documentos_relacionados = {
            normalizar_documento(parte.cpf_cnpj)
            for parte in partes
            if (parte.processo_id, parte.grupo_visual) in processos_do_cliente
            and normalizar_documento(parte.cpf_cnpj) not in ("", documento_cliente)
        }
        if documentos_relacionados:
            ids.update(
                c.pk for c in universo
                if normalizar_documento(c.cpf_cnpj) in documentos_relacionados
            )

    return list(universo.filter(pk__in=ids).order_by("nome_razao_social"))
