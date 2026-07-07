from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


@login_required
def index(request):
    perfil_usuario = getattr(request.user, 'perfil', None)

    usuarios = User.objects.filter(is_active=True).select_related("perfil").order_by(
        "first_name", "last_name", "username"
    )
    usuarios_ativos = usuarios.count()

    return render(request, "configuracoes/index.html", {
        "perfil_usuario": perfil_usuario,
        "usuarios": usuarios,
        "plano_nome": "Mestre",
        "usuarios_ativos": usuarios_ativos,
        "limite_usuarios": 10,
        "item_ativo": "configuracoes",
    })
