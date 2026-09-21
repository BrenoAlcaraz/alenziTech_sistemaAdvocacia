from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url

def usuario_admin_escritorio(user):
    """
    Verifica se o usuário pode agir como administrador do escritório.

    Único caminho: PerfilUsuario.is_admin_escritorio=True com is_active=True.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False
    perfil = getattr(user, "perfil", None)
    return perfil is not None and perfil.is_admin_escritorio


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
