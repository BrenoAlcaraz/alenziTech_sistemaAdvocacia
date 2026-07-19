from apps.accounts.decorators import (
    usuario_admin_escritorio,
    GRUPO_GERENTE,
    GRUPO_ADVOGADO,
)
from apps.accounts.models import (
    MembroEquipe,
    PermissaoPapel,
    PermissaoUsuario,
    HabilitacaoPapel,
    HabilitacaoUsuario,
)
from apps.accounts.permissoes_constants import (
    TIPO_CONTA_ADMINISTRADOR,
    TIPO_CONTA_LIMITADO,
    TIPO_CONTA_FINANCEIRO,
    NIVEIS_POR_MODULO,
)

_GRUPOS_LEGADOS = {GRUPO_GERENTE, GRUPO_ADVOGADO}


def _usuario_valido(user):
    return bool(
        user
        and getattr(user, "pk", None)
        and getattr(user, "is_active", False)
    )


def _nivel_admin(modulo):
    """Retorna o nível máximo válido para administradores no módulo dado."""
    return NIVEIS_POR_MODULO.get(modulo, [""])[-1]


# ── Tipo de conta ──────────────────────────────────────────────────────────────

def tipo_conta_usuario(user):
    """
    Resolve o tipo de conta técnico do usuário.

    Retorna um dos slugs: 'administrador_escritorio', 'financeiro', 'limitado',
    ou None se o usuário não tiver tipo de conta reconhecido.

    PerfilUsuario.cargo é descritivo e não entra nessa resolução.
    MembroEquipe.eh_gerente não substitui o tipo de conta.
    """
    if not _usuario_valido(user):
        return None

    if usuario_admin_escritorio(user):
        return TIPO_CONTA_ADMINISTRADOR

    grupos = set(user.groups.values_list("name", flat=True))

    if TIPO_CONTA_FINANCEIRO in grupos:
        return TIPO_CONTA_FINANCEIRO

    if TIPO_CONTA_LIMITADO in grupos:
        return TIPO_CONTA_LIMITADO

    if grupos & _GRUPOS_LEGADOS:
        return TIPO_CONTA_LIMITADO

    return None


# ── Permissão efetiva de módulo ────────────────────────────────────────────────

def permissao_efetiva(user, modulo):
    """
    Resolve a permissão efetiva de um usuário para um módulo.

    Retorna dict com:
      tem_acesso (bool), modulo (str), nivel (str),
      origem ('admin'|'individual'|'papel'|'nenhuma'), tipo_conta (str|None).

    Precedência: admin > individual > papel > nenhuma.
    Admin nunca depende de registros no banco.
    """
    _sem_acesso = {
        "tem_acesso": False,
        "modulo": modulo,
        "nivel": "",
        "origem": "nenhuma",
        "tipo_conta": None,
    }

    if not _usuario_valido(user):
        return _sem_acesso

    if usuario_admin_escritorio(user):
        return {
            "tem_acesso": True,
            "modulo": modulo,
            "nivel": _nivel_admin(modulo),
            "origem": "admin",
            "tipo_conta": TIPO_CONTA_ADMINISTRADOR,
        }

    tipo = tipo_conta_usuario(user)

    individual = PermissaoUsuario.objects.filter(usuario=user, modulo=modulo).first()
    if individual is not None:
        return {
            "tem_acesso": individual.ativo,
            "modulo": modulo,
            "nivel": individual.nivel,
            "origem": "individual",
            "tipo_conta": tipo,
        }

    if tipo is None:
        return {**_sem_acesso, "tipo_conta": None}

    papel = PermissaoPapel.objects.filter(tipo_conta=tipo, modulo=modulo).first()
    if papel is not None:
        return {
            "tem_acesso": papel.ativo,
            "modulo": modulo,
            "nivel": papel.nivel,
            "origem": "papel",
            "tipo_conta": tipo,
        }

    return {**_sem_acesso, "tipo_conta": tipo}


def tem_permissao_modulo(user, modulo):
    """Retorna True se o usuário tiver acesso ativo ao módulo."""
    return permissao_efetiva(user, modulo)["tem_acesso"]


def nivel_acesso_modulo(user, modulo):
    """Retorna o nível de acesso efetivo do usuário ao módulo."""
    return permissao_efetiva(user, modulo)["nivel"]


# ── Habilitação efetiva de item ────────────────────────────────────────────────

def habilitacao_efetiva(user, modulo, item):
    """
    Resolve a habilitação efetiva de um usuário para um item dentro de um módulo.

    A habilitação só é verificada se a permissão do módulo estiver ativa.
    Se a permissão estiver desligada, retorna habilitado=False com
    origem='permissao_desligada', independente dos registros de habilitação.

    Retorna dict com:
      habilitado (bool), modulo (str), item (str),
      origem ('admin'|'individual'|'papel'|'permissao_desligada'|'nenhuma'),
      tipo_conta (str|None).
    """
    _nao_habilitado = {
        "habilitado": False,
        "modulo": modulo,
        "item": item,
        "origem": "nenhuma",
        "tipo_conta": None,
    }

    if not _usuario_valido(user):
        return _nao_habilitado

    if usuario_admin_escritorio(user):
        return {
            "habilitado": True,
            "modulo": modulo,
            "item": item,
            "origem": "admin",
            "tipo_conta": TIPO_CONTA_ADMINISTRADOR,
        }

    perm = permissao_efetiva(user, modulo)
    if not perm["tem_acesso"]:
        return {
            "habilitado": False,
            "modulo": modulo,
            "item": item,
            "origem": "permissao_desligada",
            "tipo_conta": perm["tipo_conta"],
        }

    tipo = perm["tipo_conta"]

    individual = HabilitacaoUsuario.objects.filter(
        usuario=user, modulo=modulo, item=item
    ).first()
    if individual is not None:
        return {
            "habilitado": individual.ativo,
            "modulo": modulo,
            "item": item,
            "origem": "individual",
            "tipo_conta": tipo,
        }

    if tipo is None:
        return {**_nao_habilitado, "tipo_conta": None}

    papel = HabilitacaoPapel.objects.filter(
        tipo_conta=tipo, modulo=modulo, item=item
    ).first()
    if papel is not None:
        return {
            "habilitado": papel.ativo,
            "modulo": modulo,
            "item": item,
            "origem": "papel",
            "tipo_conta": tipo,
        }

    return {**_nao_habilitado, "tipo_conta": tipo}


def tem_habilitacao(user, modulo, item):
    """Retorna True se o usuário tiver o item habilitado no módulo."""
    return habilitacao_efetiva(user, modulo, item)["habilitado"]


# ── Gerência de equipe ─────────────────────────────────────────────────────────

def usuario_eh_gerente_de_alguma_equipe(user):
    """
    Retorna True se o usuário for gerente ativo de pelo menos uma equipe ativa.

    Não afeta permissões de módulo ainda — reservado para fase futura.
    """
    if not _usuario_valido(user):
        return False
    return MembroEquipe.objects.filter(
        usuario=user,
        eh_gerente=True,
        ativo=True,
        equipe__ativo=True,
    ).exists()
