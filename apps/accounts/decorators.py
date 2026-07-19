from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url

# Slugs dos grupos — papéis técnicos ativos
GRUPO_ADMINISTRADOR_ESCRITORIO = "administrador_escritorio"
GRUPO_LIMITADO = "limitado"
GRUPO_FINANCEIRO = "financeiro"

# Slugs legados — mantidos para referência em migrations e fallback de exibição
GRUPO_GERENTE = "gerente"
GRUPO_ADVOGADO = "advogado"

GRUPOS_PADROES = [
    GRUPO_ADMINISTRADOR_ESCRITORIO,
    GRUPO_LIMITADO,
    GRUPO_FINANCEIRO,
]

# Grupos que podem ser atribuídos na criação de novos usuários (o admin é atribuído por flag)
GRUPOS_CRIACAO_USUARIO = [
    GRUPO_LIMITADO,
    GRUPO_FINANCEIRO,
]

# Nomes legíveis para exibição no UI
NOMES_GRUPOS = {
    GRUPO_ADMINISTRADOR_ESCRITORIO: "Administrador do Escritório",
    GRUPO_LIMITADO: "Limitado",
    GRUPO_FINANCEIRO: "Financeiro",
    # Legado — exibido enquanto houver usuários ainda no grupo antigo
    GRUPO_GERENTE: "Gerente (legado)",
    GRUPO_ADVOGADO: "Advogado (legado)",
}


def usuario_pertence_ao_grupo(user, nome_grupo):
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=nome_grupo).exists()


def usuario_admin_escritorio(user):
    """
    Verifica se o usuário pode agir como administrador do escritório.

    Três caminhos independentes:
    - is_superuser: bypass para desenvolvimento e suporte técnico
    - PerfilUsuario.is_admin_escritorio: escape hatch para o primeiro admin do tenant
      e recuperação de acesso sem depender de grupos
    - Grupo auth.Group "administrador_escritorio": papel real do administrador

    Nota: PerfilUsuario.cargo é apenas descritivo e não controla permissões aqui.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Escape hatch: primeiro admin do tenant ou recuperação de acesso
    perfil = getattr(user, "perfil", None)
    if perfil and perfil.is_admin_escritorio:
        return True

    return usuario_pertence_ao_grupo(user, GRUPO_ADMINISTRADOR_ESCRITORIO)


def nome_legivel_grupo(nome_grupo):
    return NOMES_GRUPOS.get(nome_grupo, nome_grupo)


def obter_papel_principal_usuario(user):
    """Retorna o primeiro grupo padrão do usuário, ou None se não tiver nenhum."""
    if not user or not user.is_authenticated:
        return None
    return user.groups.filter(name__in=GRUPOS_PADROES).first()


def requer_admin_escritorio(view_func):
    """
    Decorator que restringe o acesso à view a administradores do escritório.

    - Não autenticado → redireciona para login
    - Administrador (qualquer dos três caminhos) → acesso permitido
    - Qualquer outro usuário autenticado → PermissionDenied (403)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = resolve_url("accounts:login")
            return redirect_to_login(request.get_full_path(), login_url)

        if usuario_admin_escritorio(request.user):
            return view_func(request, *args, **kwargs)

        raise PermissionDenied

    return _wrapped_view
