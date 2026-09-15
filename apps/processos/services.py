import re

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Subquery

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_PROCESSOS

from .models import (
    Processo,
    VinculoProcessoApenso,
)


User = get_user_model()


def normalizar_documento(valor):
    """Retorna apenas os dígitos de CPF/CNPJ, sem aceitar comparação parcial."""
    return re.sub(r"\D", "", valor or "")


def cliente_do_processo_corresponde_documento(processo, documento, clientes=None):
    """Identifica o Cliente já vinculado ao próprio Processo (pode ter mais
    de um — PDR de múltiplos clientes por processo) cujo CPF/CNPJ bate com
    o documento informado."""
    documento_parte = normalizar_documento(documento)
    if not documento_parte:
        return None
    clientes = processo.clientes.all() if clientes is None else clientes
    for cliente in clientes:
        if normalizar_documento(cliente.cpf_cnpj) == documento_parte:
            return cliente
    return None


def patrocinio_do_processo(processo, partes=None, clientes=None):
    """
    Grupo processual (polo_ativo/polo_passivo/outros) do lado que o
    escritório patrocina, identificado por casamento best-effort entre
    qualquer um dos `Processo.clientes` e uma `ParteProcesso` do mesmo
    processo, por CPF/CNPJ normalizado. Sem correspondência possível
    (nenhum cliente cadastrado como parte, ou processo sem cliente),
    retorna None — quem chama decide como rotular ("Não identificado").
    """
    clientes = processo.clientes.all() if clientes is None else clientes
    documentos_clientes = {
        normalizar_documento(cliente.cpf_cnpj) for cliente in clientes
    }
    documentos_clientes.discard("")
    if not documentos_clientes:
        return None
    partes = processo.partes.all() if partes is None else partes
    for parte in partes:
        if normalizar_documento(parte.cpf_cnpj) in documentos_clientes:
            return parte.grupo_visual
    return None


def parte_contraria_do_processo(processo, partes=None):
    """Parte(s) no polo oposto ao do Cliente do processo — só uma cópia
    de leitura rápida do que já está detalhado na aba Partes, exibida no
    card superior do detalhe (reunião de 13/09). `None` quando o polo do
    cliente não pôde ser identificado (mesmo critério best-effort de
    `patrocinio_do_processo`) ou quando não há nenhuma parte do lado
    oposto cadastrada."""
    partes = list(processo.partes.all()) if partes is None else list(partes)
    grupo_cliente = patrocinio_do_processo(processo, partes=partes)
    if grupo_cliente not in ("polo_ativo", "polo_passivo"):
        return None
    grupo_oposto = "polo_passivo" if grupo_cliente == "polo_ativo" else "polo_ativo"
    partes_opostas = [p for p in partes if p.grupo_visual == grupo_oposto]
    if not partes_opostas:
        return None
    return {
        "nome": partes_opostas[0].nome,
        "papel": partes_opostas[0].get_papel_display(),
        "outros_total": len(partes_opostas) - 1,
    }


def faixa_status_do_processo(processo, movimentacoes=None):
    """Fase atual / tempo parado / tempo médio entre andamentos — sempre
    calculados a partir dos Andamentos existentes, nunca campos próprios
    do Processo (mesmo padrão do card 'Processos paralisados' do
    Dashboard). `None` em qualquer chave quando não há andamento
    suficiente para calcular."""
    from django.utils import timezone

    movimentacoes = (
        list(processo.movimentacoes.all()) if movimentacoes is None else list(movimentacoes)
    )
    datas = sorted(m.data for m in movimentacoes)

    ultima_movimentacao = max(movimentacoes, key=lambda m: m.data, default=None)
    fase_atual = ultima_movimentacao.get_tipo_display() if ultima_movimentacao else None

    parado_ha_dias = None
    referencia = datas[-1].date() if datas else processo.data_distribuicao
    if referencia:
        parado_ha_dias = (timezone.localdate() - referencia).days

    tempo_medio_dias = None
    if len(datas) >= 2:
        intervalos = [(datas[i + 1] - datas[i]).days for i in range(len(datas) - 1)]
        tempo_medio_dias = round(sum(intervalos) / len(intervalos))

    return {
        "fase_atual": fase_atual,
        "parado_ha_dias": parado_ha_dias,
        "tempo_medio_dias": tempo_medio_dias,
    }


def nome_exibicao_usuario(usuario):
    """Nome de exibição de um usuário interno, com fallback para o username."""
    return usuario.get_full_name() or usuario.username


def rotulo_processo(processo):
    """Rótulo padrão "Título — Número" de Processo em qualquer seletor
    do sistema (ver ProcessoChoiceField, apps/processos/forms.py)."""
    if processo.numero:
        return f"{processo.titulo} — {processo.numero}"
    return processo.titulo


def processos_do_cliente(cliente_id):
    """Processos ativos vinculados a um cliente, para seletores dependentes."""
    try:
        cliente_id = int(cliente_id)
    except (TypeError, ValueError):
        return Processo.objects.none()
    return Processo.objects.filter(clientes__id=cliente_id).exclude(status="arquivado")


def processo_pertence_ao_cliente(cliente, processo):
    """False apenas quando os dois estão preenchidos e o cliente não é um
    dos clientes vinculados ao processo."""
    if not cliente or not processo:
        return True
    return processo.clientes.filter(pk=cliente.pk).exists()


def vincular_processos_apensos(processo_a, processo_b):
    """Cria idempotentemente um único vínculo físico para o par A ↔ B."""
    if processo_a.pk == processo_b.pk:
        raise ValueError("Um Processo não pode ser apenso a ele mesmo.")
    processo_menor_id, processo_maior_id = sorted([processo_a.pk, processo_b.pk])
    return VinculoProcessoApenso.objects.get_or_create(
        processo_menor_id=processo_menor_id,
        processo_maior_id=processo_maior_id,
    )


def vinculos_apensos_do(processo, *, processos_visiveis=None):
    """Centraliza a consulta simétrica e, opcionalmente, seu escopo de leitura."""
    vinculos = VinculoProcessoApenso.objects.filter(
        Q(processo_menor=processo) | Q(processo_maior=processo)
    )
    if processos_visiveis is None:
        return vinculos

    ids_visiveis = Subquery(
        processos_visiveis.order_by().values("pk")
    )
    return vinculos.filter(
        Q(
            processo_menor=processo,
            processo_maior_id__in=ids_visiveis,
        )
        | Q(
            processo_maior=processo,
            processo_menor_id__in=ids_visiveis,
        )
    )


def ids_processos_apensos_do(processo):
    """Retorna os IDs relacionados sem inferir hierarquia ou transitividade."""
    vinculos = vinculos_apensos_do(processo)
    ids_menores = vinculos.filter(processo_maior=processo).values(
        "processo_menor_id"
    )
    ids_maiores = vinculos.filter(processo_menor=processo).values(
        "processo_maior_id"
    )
    return ids_menores.union(ids_maiores)


class AdministradorResponsavelIndisponivel(RuntimeError):
    """Não há um único Administrador ativo para receber os processos."""


def responsaveis_elegiveis():
    """Usuários ativos do tenant com acesso efetivo atual a Processos."""
    usuarios = User.objects.filter(is_active=True).order_by(
        "first_name", "last_name", "username"
    )
    ids_elegiveis = [
        usuario.pk
        for usuario in usuarios
        if tem_permissao_modulo(usuario, MODULO_PROCESSOS)
    ]
    return usuarios.filter(pk__in=ids_elegiveis)


def usuarios_com_acesso_processos():
    """Snapshot dos usuários ativos atualmente autorizados ao módulo."""
    return [
        usuario.pk
        for usuario in User.objects.filter(is_active=True)
        if tem_permissao_modulo(usuario, MODULO_PROCESSOS)
    ]


def _administrador_ativo():
    try:
        return User.objects.select_for_update().get(
            is_active=True,
            perfil__is_admin_escritorio=True,
        )
    except (User.DoesNotExist, User.MultipleObjectsReturned) as exc:
        raise AdministradorResponsavelIndisponivel(
            "A transferência exige um único Administrador do escritório ativo."
        ) from exc


def transferir_processos_de_usuarios_sem_acesso(usuario_ids):
    """
    Transfere processos apenas de quem perdeu o acesso desde um snapshot.

    O chamador deve executar esta função na mesma transação da alteração de
    permissões. Ganho posterior de acesso não provoca devolução automática.
    """
    transferidos = 0
    for usuario in User.objects.filter(pk__in=usuario_ids):
        if tem_permissao_modulo(usuario, MODULO_PROCESSOS):
            continue

        processos = Processo.objects.select_for_update().filter(responsavel=usuario)
        if not processos.exists():
            continue

        administrador = _administrador_ativo()
        transferidos += processos.update(responsavel=administrador)
    return transferidos


def transferir_processos_se_sem_acesso(usuario):
    """Operação de domínio reutilizável por futuros fluxos reais de produto."""
    with transaction.atomic():
        return transferir_processos_de_usuarios_sem_acesso([usuario.pk])
