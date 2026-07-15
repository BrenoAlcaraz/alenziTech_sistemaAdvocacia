"""
Helpers de consulta de departamentos e escopo de dados por usuário.

Estes helpers ainda não aplicam filtros nos módulos operacionais.
Eles apenas expõem consultas de departamentos para uso futuro.
"""

from apps.accounts.decorators import usuario_admin_escritorio
from apps.accounts.models import Departamento, MembroDepartamento

# ---------------------------------------------------------------------------
# Constantes de escopo (preparação para fases futuras)
# ---------------------------------------------------------------------------

ESCOPO_TUDO = "tudo"
ESCOPO_DEPARTAMENTOS_GERENCIADOS = "departamentos_gerenciados"
ESCOPO_DEPARTAMENTO = "departamento"
ESCOPO_PROPRIOS_ITENS = "proprios_itens"
ESCOPO_NENHUM = "nenhum"

ESCOPOS_DADOS = [
    ESCOPO_TUDO,
    ESCOPO_DEPARTAMENTOS_GERENCIADOS,
    ESCOPO_DEPARTAMENTO,
    ESCOPO_PROPRIOS_ITENS,
    ESCOPO_NENHUM,
]


# ---------------------------------------------------------------------------
# Helpers de departamentos do usuário
# ---------------------------------------------------------------------------

def departamentos_do_usuario(user, somente_ativos=True):
    """Retorna QuerySet de Departamento vinculados ao usuário."""
    if not user or not user.is_authenticated:
        return Departamento.objects.none()

    membros = MembroDepartamento.objects.filter(usuario=user)

    if somente_ativos:
        membros = membros.filter(ativo=True, departamento__ativo=True)

    return (
        Departamento.objects
        .filter(membros__in=membros)
        .distinct()
        .order_by("nome")
    )


def departamentos_gerenciados_pelo_usuario(user, somente_ativos=True):
    """Retorna QuerySet de Departamento em que o usuário é gerente."""
    if not user or not user.is_authenticated:
        return Departamento.objects.none()

    membros = MembroDepartamento.objects.filter(usuario=user, eh_gerente=True)

    if somente_ativos:
        membros = membros.filter(ativo=True, departamento__ativo=True)

    return (
        Departamento.objects
        .filter(membros__in=membros)
        .distinct()
        .order_by("nome")
    )


def usuario_gerencia_departamento(user, departamento):
    """Retorna True se o usuário é gerente ativo do departamento."""
    if not user or not user.is_authenticated or not departamento:
        return False

    return MembroDepartamento.objects.filter(
        usuario=user,
        departamento=departamento,
        departamento__ativo=True,
        eh_gerente=True,
        ativo=True,
    ).exists()


def ids_departamentos_do_usuario(user, somente_ativos=True):
    """Retorna lista de ids dos departamentos do usuário."""
    return list(
        departamentos_do_usuario(user, somente_ativos=somente_ativos)
        .values_list("id", flat=True)
    )


def ids_departamentos_gerenciados_pelo_usuario(user, somente_ativos=True):
    """Retorna lista de ids dos departamentos gerenciados pelo usuário."""
    return list(
        departamentos_gerenciados_pelo_usuario(user, somente_ativos=somente_ativos)
        .values_list("id", flat=True)
    )


# ---------------------------------------------------------------------------
# Helper de departamento padrão para criação de registros
# ---------------------------------------------------------------------------

def departamento_padrao_para_usuario(user):
    """
    Retorna um departamento padrão seguro para atribuição automática na criação de registros.

    Regras:
    - Usuário inválido ou não autenticado → None
    - Administrador do escritório ou superuser → None (admin vê tudo, sem departamento fixo)
    - Exatamente 1 departamento ativo → retorna esse departamento
    - 0 ou 2+ departamentos ativos → None (não é possível inferir qual é o correto)

    Não aplica filtros de escopo. Apenas sugere um departamento para novo registro.
    """
    if not user or not user.is_authenticated:
        return None

    if usuario_admin_escritorio(user):
        return None

    departamentos = list(departamentos_do_usuario(user, somente_ativos=True)[:2])

    if len(departamentos) == 1:
        return departamentos[0]

    return None


# ---------------------------------------------------------------------------
# Helper de hierarquia
# ---------------------------------------------------------------------------

def departamentos_descendentes(departamento, incluir_proprio=False, somente_ativos=True):
    """
    Retorna lista de Departamento abaixo de um departamento (recursivo).
    Útil para consultas que devem incluir subdepartamentos.
    """
    if not departamento:
        return []

    if somente_ativos and not departamento.ativo:
        return []

    resultado = [departamento] if incluir_proprio else []

    filhos_qs = Departamento.objects.filter(departamento_pai=departamento)
    if somente_ativos:
        filhos_qs = filhos_qs.filter(ativo=True)

    for filho in filhos_qs.order_by("nome"):
        resultado.append(filho)
        resultado.extend(
            departamentos_descendentes(filho, incluir_proprio=False, somente_ativos=somente_ativos)
        )

    return resultado
