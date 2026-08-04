from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.models import (
    MembroEquipe,
    PermissaoPapel,
    PermissaoUsuario,
    HabilitacaoPapel,
    HabilitacaoUsuario,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    TIPO_CONTA_ADMINISTRADOR,
    TIPO_CONTA_LIMITADO,
    TIPO_CONTA_FINANCEIRO,
    NIVEIS_POR_MODULO,
    ITENS_POR_MODULO,
)


def _usuario_valido(user):
    return bool(
        user
        and getattr(user, "pk", None)
        and getattr(user, "is_active", False)
    )


def _nivel_admin(modulo):
    """Retorna o nível máximo válido para administradores no módulo dado."""
    return NIVEIS_POR_MODULO.get(modulo, [""])[-1]


def _maior_nivel(modulo, niveis):
    """Retorna o maior nível dentre os fornecidos segundo a ordem de NIVEIS_POR_MODULO."""
    ordem = NIVEIS_POR_MODULO.get(modulo, [""])
    melhor_idx = -1
    melhor = ""
    for n in niveis:
        try:
            idx = ordem.index(n)
            if idx > melhor_idx:
                melhor_idx = idx
                melhor = n
        except ValueError:
            pass
    return melhor


def _papeis_ativos_ids(user):
    """IDs de PapelAcesso com vínculo ativo: UP.ativo=True + PapelAcesso.ativo=True."""
    return list(
        UsuarioPapel.objects.filter(
            usuario=user,
            ativo=True,
            papel__ativo=True,
        ).values_list("papel_id", flat=True)
    )


def _tem_qualquer_up(user):
    """True se o usuário tiver ao menos um UsuarioPapel (qualquer estado)."""
    return UsuarioPapel.objects.filter(usuario=user).exists()


# ── Tipo de conta ──────────────────────────────────────────────────────────────

def tipo_conta_usuario(user):
    """
    Resolve o tipo de conta técnico do usuário via Group legado.

    Retorna 'financeiro' ou 'limitado', ou None.

    Casos que retornam None:
      - usuário inativo ou inválido
      - nenhum grupo técnico
      - duplo grupo (limitado + financeiro ao mesmo tempo)

    Administradores são tratados por usuario_admin_escritorio() antes de aqui.
    Grupos legados ('advogado', 'gerente') não concedem acesso.
    PerfilUsuario.cargo é descritivo e não entra nessa resolução.
    """
    if not _usuario_valido(user):
        return None

    grupos_tecnicos = set(
        user.groups.filter(
            name__in=[TIPO_CONTA_LIMITADO, TIPO_CONTA_FINANCEIRO]
        ).values_list("name", flat=True)
    )

    if len(grupos_tecnicos) != 1:
        return None

    return grupos_tecnicos.pop()


# ── Permissão efetiva de módulo ────────────────────────────────────────────────

def permissao_efetiva(user, modulo):
    """
    Resolve a permissão efetiva de um usuário para um módulo.

    Retorna dict com:
      tem_acesso (bool), modulo (str), nivel (str),
      origem ('admin'|'individual'|'papel'|'nenhuma'), tipo_conta (str|None).

    Ordem de avaliação:
      1. Módulo inválido → negar sem consultar o banco
      2. Usuário inativo ou inválido → negar
      3. Administrador → acesso total
      4. Override individual (PermissaoUsuario)
      5. Usuário tem UsuarioPapel → caminho de papéis (agrega pelo maior nível)
      6. Sem UsuarioPapel → fallback de grupo legado (tipo_conta via Group)
      7. Negação padrão
    """
    _sem_acesso = {
        "tem_acesso": False,
        "modulo": modulo,
        "nivel": "",
        "origem": "nenhuma",
        "tipo_conta": None,
    }

    if modulo not in NIVEIS_POR_MODULO:
        return _sem_acesso

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

    individual = PermissaoUsuario.objects.filter(usuario=user, modulo=modulo).first()
    if individual is not None:
        tipo = tipo_conta_usuario(user)
        return {
            "tem_acesso": individual.ativo,
            "modulo": modulo,
            "nivel": individual.nivel,
            "origem": "individual",
            "tipo_conta": tipo,
        }

    if _tem_qualquer_up(user):
        ids_ativos = _papeis_ativos_ids(user)
        if not ids_ativos:
            return _sem_acesso
        pps = list(
            PermissaoPapel.objects.filter(
                papel_id__in=ids_ativos,
                modulo=modulo,
                ativo=True,
            )
        )
        if not pps:
            return _sem_acesso
        nivel = _maior_nivel(modulo, [pp.nivel for pp in pps])
        return {
            "tem_acesso": True,
            "modulo": modulo,
            "nivel": nivel,
            "origem": "papel",
            "tipo_conta": None,
        }

    # Fallback legado: usar tipo_conta via Group
    tipo = tipo_conta_usuario(user)
    if tipo is None:
        return _sem_acesso

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

    A combinação módulo/item é validada antes de qualquer consulta ao banco.
    A habilitação só é verificada se a permissão do módulo estiver ativa.

    Retorna dict com:
      habilitado (bool), modulo (str), item (str),
      origem ('admin'|'individual'|'papel'|'permissao_desligada'|'nenhuma'),
      tipo_conta (str|None).

    Nega sem consultar o banco quando:
      - módulo não existe em ITENS_POR_MODULO
      - módulo sem habilitações definidas nesta versão (chat, financeiro, painel)
      - item não pertence ao módulo
      - usuário inativo ou inválido (após validação da combinação)

    Admin recebe habilitado=True apenas para combinações módulo/item válidas.
    """
    _nao_habilitado = {
        "habilitado": False,
        "modulo": modulo,
        "item": item,
        "origem": "nenhuma",
        "tipo_conta": None,
    }

    itens_validos = ITENS_POR_MODULO.get(modulo)
    if not itens_validos or item not in itens_validos:
        return _nao_habilitado

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
        # Caminho de papéis (new kernel): agrega HP de todos os papéis ativos
        ids_ativos = _papeis_ativos_ids(user)
        if ids_ativos:
            for hp in HabilitacaoPapel.objects.filter(
                papel_id__in=ids_ativos,
                modulo=modulo,
                item=item,
            ):
                if hp.ativo:
                    return {
                        "habilitado": True,
                        "modulo": modulo,
                        "item": item,
                        "origem": "papel",
                        "tipo_conta": None,
                    }
        return {**_nao_habilitado, "tipo_conta": None}

    # Fallback legado: HP por tipo_conta
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
