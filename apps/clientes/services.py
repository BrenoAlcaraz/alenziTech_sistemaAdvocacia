from apps.processos.models import ParteProcesso
from apps.processos.services import normalizar_documento

from .models import Cliente


def clientes_relacionados(cliente):
    """Outros Clientes ativos que estão do mesmo polo (ambos no polo
    ativo, ou ambos no polo passivo) que este cliente em algum Processo
    em comum — reunião de 13/09.

    Best-effort por CPF/CNPJ normalizado, mesmo critério de
    `apps.processos.services.patrocinio_do_processo`: só enxerga clientes
    que também foram cadastrados manualmente como Parte do processo. Sem
    documento cadastrado (cliente ou parte), não há como relacionar.
    """
    documento_cliente = normalizar_documento(cliente.cpf_cnpj)
    if not documento_cliente:
        return []

    partes = list(ParteProcesso.objects.only("processo_id", "cpf_cnpj", "papel"))
    processos_do_cliente = {
        (parte.processo_id, parte.grupo_visual)
        for parte in partes
        if normalizar_documento(parte.cpf_cnpj) == documento_cliente
    }
    if not processos_do_cliente:
        return []

    documentos_relacionados = {
        normalizar_documento(parte.cpf_cnpj)
        for parte in partes
        if (parte.processo_id, parte.grupo_visual) in processos_do_cliente
        and normalizar_documento(parte.cpf_cnpj) not in ("", documento_cliente)
    }
    if not documentos_relacionados:
        return []

    return [
        c for c in Cliente.objects.filter(ativo=True).exclude(pk=cliente.pk)
        if normalizar_documento(c.cpf_cnpj) in documentos_relacionados
    ]
