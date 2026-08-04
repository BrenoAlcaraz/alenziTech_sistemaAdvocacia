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

_SENTINEL = object()


def _usuario_valido(user):
    return bool(
        user
        and getattr(user, "pk", None)
        and getattr(user, "is_active", False)
    )


def _nivel_admin(modulo):
    return NIVEIS_POR_MODULO.get(modulo, [""])[-1]


def _maior_nivel(modulo, niveis):
    """
    Retorna o maior nível dentre os fornecidos segundo a ordem de NIVEIS_POR_MODULO.

    - Lista vazia → ""
    - Há pelo menos um nível válido → maior nível válido (inválidos ignorados)
    - Lista não vazia com todos inválidos → menor nível válido do módulo
    """
    ordem = NIVEIS_POR_MODULO.get(modulo, [""])
    melhor_idx = -1
    melhor = None
    tem_entradas = False
    for n in niveis:
        tem_entradas = True
        try:
            idx = ordem.index(n)
            if idx > melhor_idx:
                melhor_idx = idx
                melhor = n
        except ValueError:
            pass
    if melhor is not None:
        return melhor
    if not tem_entradas:
        return ""
    # Lista não vazia, todos inválidos → mínimo seguro
    return ordem[0] if ordem else ""


def _menor_nivel_seguro(modulo, niveis):
    """
    Retorna o menor nível válido dentre os fornecidos.
    Se todos inválidos → menor nível configurado para o módulo.
    Se lista vazia → "".
    Usado para preservar nível em permissões inativas.
    """
    if not niveis:
        return ""
    ordem = NIVEIS_POR_MODULO.get(modulo, [""])
    melhor_idx = len(ordem)
    melhor = None
    for n in niveis:
        try:
            idx = ordem.index(n)
            if idx < melhor_idx:
                melhor_idx = idx
                melhor = n
        except ValueError:
            pass
    if melhor is not None:
        return melhor
    return ordem[0] if ordem else ""


class _AupContexto:
    """
    Contexto interno de autorização para uma chamada de permissao/habilitacao.

    Carrega UsuarioPapel uma única vez via select_related("papel").
    Deriva tem_qualquer_up e ids_papeis_ativos em memória.
    Carrega is_admin e tipo_conta apenas se necessário (lazy).
    Nunca reutilizar entre requests, usuários ou tenants.
    """

    def __init__(self, user):
        self._user = user
        self._ups = _SENTINEL
        self._is_admin = _SENTINEL
        self._tipo_conta = _SENTINEL

    def _carregar_ups(self):
        if self._ups is _SENTINEL:
            self._ups = list(
                UsuarioPapel.objects.filter(usuario=self._user)
                .select_related("papel")
            )
        return self._ups

    @property
    def is_admin(self):
        if self._is_admin is _SENTINEL:
            self._is_admin = usuario_admin_escritorio(self._user)
        return self._is_admin

    @property
    def tem_qualquer_up(self):
        return bool(self._carregar_ups())

    @property
    def ids_papeis_ativos(self):
        return [
            up.papel_id
            for up in self._carregar_ups()
            if up.ativo and up.papel.ativo
        ]

    @property
    def tipo_conta(self):
        if self._tipo_conta is _SENTINEL:
            self._tipo_conta = tipo_conta_usuario(self._user)
        return self._tipo_conta


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
      origem ('admin'|'individual'|'papel'|'grupo_legado'|'inativo'|'nenhuma'),
      tipo_conta (str|None).

    Cria um contexto interno para evitar queries repetidas.
    """
    ctx = _AupContexto(user)
    return _permissao_efetiva_com_contexto(user, modulo, ctx)


def _permissao_efetiva_com_contexto(user, modulo, ctx):
    """
    Resolve a permissão efetiva reutilizando um contexto existente.

    Ordem de avaliação:
      1. Módulo inválido → negar sem consultar o banco
      2. Usuário sem pk → negar
      3. Usuário inativo → negar (origem="inativo")
      4. Administrador → acesso total (origem="admin")
      5. Override individual (PermissaoUsuario) → origem="individual"
      6. Usuário tem UsuarioPapel → caminho de papéis (origem="papel")
      7. Sem UsuarioPapel → fallback de grupo legado (origem="grupo_legado")
      8. Negação padrão
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

    if not user or not getattr(user, "pk", None):
        return _sem_acesso

    if not getattr(user, "is_active", False):
        return {**_sem_acesso, "origem": "inativo"}

    if ctx.is_admin:
        return {
            "tem_acesso": True,
            "modulo": modulo,
            "nivel": _nivel_admin(modulo),
            "origem": "admin",
            "tipo_conta": TIPO_CONTA_ADMINISTRADOR,
        }

    individual = PermissaoUsuario.objects.filter(usuario=user, modulo=modulo).first()
    if individual is not None:
        # tipo_conta=None quando UP existe (contexto dinâmico, não legado)
        tipo = None if ctx.tem_qualquer_up else ctx.tipo_conta
        return {
            "tem_acesso": individual.ativo,
            "modulo": modulo,
            "nivel": individual.nivel,
            "origem": "individual",
            "tipo_conta": tipo,
        }

    if ctx.tem_qualquer_up:
        ids_ativos = ctx.ids_papeis_ativos
        if not ids_ativos:
            # UP existe mas todos inativos ou com PapelAcesso inativo
            return {**_sem_acesso, "origem": "papel", "tipo_conta": None}

        # Carregar todas as linhas sem filtrar ativo — separar em memória
        linhas = list(
            PermissaoPapel.objects.filter(
                papel_id__in=ids_ativos,
                modulo=modulo,
            )
        )
        if not linhas:
            return {**_sem_acesso, "origem": "papel", "tipo_conta": None}

        concessoes = [pp for pp in linhas if pp.ativo]
        if concessoes:
            nivel = _maior_nivel(modulo, [pp.nivel for pp in concessoes])
            return {
                "tem_acesso": True,
                "modulo": modulo,
                "nivel": nivel,
                "origem": "papel",
                "tipo_conta": None,
            }

        # Linhas existem mas todas inativas — preservar nível seguro conservador
        nivel = _menor_nivel_seguro(modulo, [pp.nivel for pp in linhas])
        return {
            "tem_acesso": False,
            "modulo": modulo,
            "nivel": nivel,
            "origem": "papel",
            "tipo_conta": None,
        }

    # Fallback legado: usar tipo_conta via Group
    tipo = ctx.tipo_conta
    if tipo is None:
        return _sem_acesso

    papel = PermissaoPapel.objects.filter(tipo_conta=tipo, modulo=modulo).first()
    if papel is not None:
        return {
            "tem_acesso": papel.ativo,
            "modulo": modulo,
            "nivel": papel.nivel,
            "origem": "grupo_legado",
            "tipo_conta": tipo,
        }

    return {**_sem_acesso, "origem": "grupo_legado", "tipo_conta": tipo}


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
      origem ('admin'|'individual'|'papel'|'grupo_legado'|
              'permissao_desligada'|'inativo'|'nenhuma'),
      tipo_conta (str|None).

    Cria contexto interno e reutiliza em _permissao_efetiva_com_contexto.
    """
    ctx = _AupContexto(user)
    return _habilitacao_efetiva_com_contexto(user, modulo, item, ctx)


def _habilitacao_efetiva_com_contexto(user, modulo, item, ctx):
    """
    Resolve habilitação reutilizando contexto para evitar queries repetidas.

    Caminho de papéis (contexto.tem_qualquer_up=True):
      nunca consulta HabilitacaoPapel por tipo_conta.

    Fallback legado (contexto.tem_qualquer_up=False):
      somente então usa tipo_conta e HabilitacaoPapel por tipo_conta.
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

    if not user or not getattr(user, "pk", None):
        return _nao_habilitado

    if not getattr(user, "is_active", False):
        return {**_nao_habilitado, "origem": "inativo"}

    if ctx.is_admin:
        return {
            "habilitado": True,
            "modulo": modulo,
            "item": item,
            "origem": "admin",
            "tipo_conta": TIPO_CONTA_ADMINISTRADOR,
        }

    perm = _permissao_efetiva_com_contexto(user, modulo, ctx)
    if not perm["tem_acesso"]:
        return {
            "habilitado": False,
            "modulo": modulo,
            "item": item,
            "origem": "permissao_desligada",
            "tipo_conta": perm["tipo_conta"],
        }

    # tipo_conta=None quando existe qualquer UP — mesmo para override individual
    tipo = None if ctx.tem_qualquer_up else ctx.tipo_conta

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

    if ctx.tem_qualquer_up:
        # Caminho dinâmico: nunca consultar por tipo_conta
        ids_ativos = ctx.ids_papeis_ativos
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
        return {**_nao_habilitado, "origem": "papel", "tipo_conta": None}

    # Fallback legado: somente quando não existe nenhum UP
    if tipo is None:
        return _nao_habilitado

    papel = HabilitacaoPapel.objects.filter(
        tipo_conta=tipo, modulo=modulo, item=item
    ).first()
    if papel is not None:
        return {
            "habilitado": papel.ativo,
            "modulo": modulo,
            "item": item,
            "origem": "grupo_legado",
            "tipo_conta": tipo,
        }

    return {**_nao_habilitado, "origem": "grupo_legado", "tipo_conta": tipo}


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
