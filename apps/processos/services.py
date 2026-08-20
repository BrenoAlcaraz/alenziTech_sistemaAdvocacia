from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_PROCESSOS

from .models import Processo


User = get_user_model()


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
