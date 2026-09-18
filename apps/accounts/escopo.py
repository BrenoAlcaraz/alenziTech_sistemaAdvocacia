"""
Helpers de consulta de equipes e escopo de dados por usuário.

Estes helpers ainda não aplicam filtros nos módulos operacionais.
Eles apenas expõem consultas de equipes para uso futuro.
"""

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.models import Equipe, MembroEquipe

# ---------------------------------------------------------------------------
# Constantes de escopo (preparação para fases futuras)
# ---------------------------------------------------------------------------

ESCOPO_TUDO = "tudo"
ESCOPO_EQUIPES_GERENCIADAS = "equipes_gerenciadas"
ESCOPO_EQUIPE = "equipe"
ESCOPO_PROPRIOS_ITENS = "proprios_itens"
ESCOPO_NENHUM = "nenhum"

ESCOPOS_DADOS = [
    ESCOPO_TUDO,
    ESCOPO_EQUIPES_GERENCIADAS,
    ESCOPO_EQUIPE,
    ESCOPO_PROPRIOS_ITENS,
    ESCOPO_NENHUM,
]


# ---------------------------------------------------------------------------
# Helpers de equipes do usuário
# ---------------------------------------------------------------------------

def equipes_do_usuario(user, somente_ativos=True):
    """Retorna QuerySet de Equipe vinculadas ao usuário."""
    if not user or not user.is_authenticated:
        return Equipe.objects.none()

    membros = MembroEquipe.objects.filter(usuario=user)

    if somente_ativos:
        membros = membros.filter(ativo=True, equipe__ativo=True)

    return (
        Equipe.objects
        .filter(membros__in=membros)
        .distinct()
        .order_by("nome")
    )


def equipes_gerenciadas_pelo_usuario(user, somente_ativos=True):
    """Retorna QuerySet de Equipe em que o usuário é gerente."""
    if not user or not user.is_authenticated:
        return Equipe.objects.none()

    membros = MembroEquipe.objects.filter(usuario=user, eh_gerente=True)

    if somente_ativos:
        membros = membros.filter(ativo=True, equipe__ativo=True)

    return (
        Equipe.objects
        .filter(membros__in=membros)
        .distinct()
        .order_by("nome")
    )


def usuario_gerencia_equipe(user, equipe):
    """Retorna True se o usuário é gerente ativo da equipe."""
    if not user or not user.is_authenticated or not equipe:
        return False

    return MembroEquipe.objects.filter(
        usuario=user,
        equipe=equipe,
        equipe__ativo=True,
        eh_gerente=True,
        ativo=True,
    ).exists()


def ids_equipes_do_usuario(user, somente_ativos=True):
    """Retorna lista de ids das equipes do usuário."""
    return list(
        equipes_do_usuario(user, somente_ativos=somente_ativos)
        .values_list("id", flat=True)
    )


def ids_equipes_gerenciadas_pelo_usuario(user, somente_ativos=True):
    """Retorna lista de ids das equipes gerenciadas pelo usuário."""
    return list(
        equipes_gerenciadas_pelo_usuario(user, somente_ativos=somente_ativos)
        .values_list("id", flat=True)
    )


# ---------------------------------------------------------------------------
# Helper de equipe padrão para criação de registros
# ---------------------------------------------------------------------------

def equipe_padrao_para_usuario(user):
    """
    Retorna uma equipe padrão segura para atribuição automática na criação de registros.

    Regras:
    - Usuário inválido ou não autenticado → None
    - Administrador do escritório ou superuser → None (admin vê tudo, sem equipe fixa)
    - Exatamente 1 equipe ativa → retorna essa equipe
    - 0 ou 2+ equipes ativas → None (não é possível inferir qual é a correta)

    Não aplica filtros de escopo. Apenas sugere uma equipe para novo registro.
    """
    if not user or not user.is_authenticated:
        return None

    if usuario_admin_escritorio(user):
        return None

    equipes = list(equipes_do_usuario(user, somente_ativos=True)[:2])

    if len(equipes) == 1:
        return equipes[0]

    return None
