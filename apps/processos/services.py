import re

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_PROCESSOS

from .models import ParteProcesso, Processo, RepresentanteParte


User = get_user_model()


def normalizar_documento(valor):
    """Retorna apenas os dígitos de CPF/CNPJ, sem aceitar comparação parcial."""
    return re.sub(r"\D", "", valor or "")


def cliente_do_processo_corresponde_documento(processo, documento):
    """Identifica somente o Cliente já vinculado ao próprio Processo."""
    if not processo.cliente_id:
        return None
    documento_parte = normalizar_documento(documento)
    documento_cliente = normalizar_documento(processo.cliente.cpf_cnpj)
    if not documento_parte or not documento_cliente:
        return None
    if documento_parte != documento_cliente:
        return None
    return processo.cliente


def vincular_responsavel_como_advogado(parte):
    """Cria idempotentemente a representação interna automática da parte."""
    return RepresentanteParte.objects.get_or_create(
        parte=parte,
        tipo="interno",
        usuario=parte.processo.responsavel,
        defaults={
            "nome_externo": "",
            "oab": "",
            "uf_oab": "",
            "telefone": "",
            "email": "",
        },
    )


def garantir_participante_cliente(processo):
    """Garante a Regra A por FK, inclusive quando o Cliente não tem documento."""
    if not processo.cliente_id:
        return None

    with transaction.atomic():
        processo_atual = (
            Processo.objects.select_for_update(of=("self",))
            .get(pk=processo.pk)
        )
        participante, _ = ParteProcesso.objects.get_or_create(
            processo=processo_atual,
            cliente=processo_atual.cliente,
            defaults={
                "nome": "",
                "cpf_cnpj": "",
                "vinculo_escritorio": "cliente",
                "posicao": None,
                "qualificacao": None,
                "atuacao_ministerio_publico": "",
                "classificacao_pendente": True,
            },
        )
        vincular_responsavel_como_advogado(participante)
        return participante


def obter_ou_criar_representante_externo(parte, representante):
    """Deduplica somente a mesma identidade externa normalizada na mesma Parte."""
    representante.parte = parte
    representante.normalizar_identidade_externa()
    defaults = {
        "usuario": None,
        "nome_externo": representante.nome_externo,
        "oab": representante.oab,
        "uf_oab": representante.uf_oab,
        "telefone": representante.telefone,
        "email": representante.email,
    }
    return RepresentanteParte.objects.get_or_create(
        parte=parte,
        tipo="externo",
        fingerprint_externo=representante.fingerprint_externo,
        defaults=defaults,
    )


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
        processo_ids = list(processos.values_list("pk", flat=True))
        transferidos += processos.update(responsavel=administrador)
        for processo in Processo.objects.filter(pk__in=processo_ids):
            garantir_participante_cliente(processo)
    return transferidos


def transferir_processos_se_sem_acesso(usuario):
    """Operação de domínio reutilizável por futuros fluxos reais de produto."""
    with transaction.atomic():
        return transferir_processos_de_usuarios_sem_acesso([usuario.pk])
