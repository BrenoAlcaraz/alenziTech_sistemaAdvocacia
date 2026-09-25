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
    Carrega is_admin apenas se necessário (lazy).
    Nunca reutilizar entre requests, usuários ou tenants.
    """

    def __init__(self, user):
        self._user = user
        self._ups = _SENTINEL
        self._is_admin = _SENTINEL

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


def nomes_papeis_usuario(user):
    """Nomes dos papéis ativos do usuário, para exibição. Usa
    `atribuicoes_papel__papel` já carregado por prefetch, se houver."""
    nomes = [
        up.papel.nome
        for up in user.atribuicoes_papel.all()
        if up.ativo and up.papel.ativo
    ]
    return ", ".join(sorted(nomes)) or "Sem papel definido"


# ── Permissão efetiva de módulo ────────────────────────────────────────────────

def permissao_efetiva(user, modulo):
    """
    Resolve a permissão efetiva de um usuário para um módulo.

    Retorna dict com:
      tem_acesso (bool), modulo (str), nivel (str),
      origem ('admin'|'individual'|'papel'|'inativo'|'nenhuma').

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
      6. Usuário tem UsuarioPapel → o papel ativo dele (origem="papel"; no
         máximo um, garantido por constraint)
      7. Negação padrão
    """
    _sem_acesso = {
        "tem_acesso": False,
        "modulo": modulo,
        "nivel": "",
        "origem": "nenhuma",
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
        }

    individual = PermissaoUsuario.objects.filter(usuario=user, modulo=modulo).first()
    if individual is not None:
        return {
            "tem_acesso": individual.ativo,
            "modulo": modulo,
            "nivel": individual.nivel,
            "origem": "individual",
        }

    if ctx.tem_qualquer_up:
        ids_ativos = ctx.ids_papeis_ativos
        if not ids_ativos:
            # UP existe mas todos inativos ou com PapelAcesso inativo
            return {**_sem_acesso, "origem": "papel"}

        # Carregar todas as linhas sem filtrar ativo — separar em memória
        linhas = list(
            PermissaoPapel.objects.filter(
                papel_id__in=ids_ativos,
                modulo=modulo,
            )
        )
        if not linhas:
            return {**_sem_acesso, "origem": "papel"}

        concessoes = [pp for pp in linhas if pp.ativo]
        if concessoes:
            nivel = _maior_nivel(modulo, [pp.nivel for pp in concessoes])
            return {
                "tem_acesso": True,
                "modulo": modulo,
                "nivel": nivel,
                "origem": "papel",
            }

        # Linhas existem mas todas inativas — preservar nível seguro conservador
        nivel = _menor_nivel_seguro(modulo, [pp.nivel for pp in linhas])
        return {
            "tem_acesso": False,
            "modulo": modulo,
            "nivel": nivel,
            "origem": "papel",
        }

    return _sem_acesso


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
      origem ('admin'|'individual'|'papel'|'permissao_desligada'|
              'inativo'|'nenhuma').

    Cria contexto interno e reutiliza em _permissao_efetiva_com_contexto.
    """
    ctx = _AupContexto(user)
    return _habilitacao_efetiva_com_contexto(user, modulo, item, ctx)


def _habilitacao_efetiva_com_contexto(user, modulo, item, ctx):
    """
    Resolve habilitação reutilizando contexto para evitar queries repetidas.
    """
    _nao_habilitado = {
        "habilitado": False,
        "modulo": modulo,
        "item": item,
        "origem": "nenhuma",
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
        }

    perm = _permissao_efetiva_com_contexto(user, modulo, ctx)
    if not perm["tem_acesso"]:
        return {
            "habilitado": False,
            "modulo": modulo,
            "item": item,
            "origem": "permissao_desligada",
        }

    individual = HabilitacaoUsuario.objects.filter(
        usuario=user, modulo=modulo, item=item
    ).first()
    if individual is not None:
        return {
            "habilitado": individual.ativo,
            "modulo": modulo,
            "item": item,
            "origem": "individual",
        }

    if ctx.tem_qualquer_up:
        ids_ativos = ctx.ids_papeis_ativos
        if ids_ativos and HabilitacaoPapel.objects.filter(
            papel_id__in=ids_ativos,
            modulo=modulo,
            item=item,
            ativo=True,
        ).exists():
            return {
                "habilitado": True,
                "modulo": modulo,
                "item": item,
                "origem": "papel",
            }
        return {**_nao_habilitado, "origem": "papel"}

    return _nao_habilitado


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
