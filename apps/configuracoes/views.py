from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from apps.accounts.models import PerfilUsuario
from apps.accounts.forms import PerfilUsuarioForm
from .models import ConfiguracaoEscritorio
from .forms import ConfiguracaoEscritorioForm


def _obter_configuracao_escritorio():
    configuracao, _ = ConfiguracaoEscritorio.objects.get_or_create(pk=1)
    return configuracao


@login_required
def index(request):
    perfil_usuario = getattr(request.user, 'perfil', None)

    usuarios = User.objects.filter(is_active=True).select_related("perfil").order_by(
        "first_name", "last_name", "username"
    )
    usuarios_ativos = usuarios.count()
    configuracao_escritorio = _obter_configuracao_escritorio()

    return render(request, "configuracoes/index.html", {
        "perfil_usuario": perfil_usuario,
        "usuarios": usuarios,
        "plano_nome": "Mestre",
        "usuarios_ativos": usuarios_ativos,
        "limite_usuarios": 10,
        "configuracao_escritorio": configuracao_escritorio,
        "item_ativo": "configuracoes",
    })


@login_required
def editar_perfil(request):
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = PerfilUsuarioForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect("configuracoes:index")
    else:
        form = PerfilUsuarioForm(instance=perfil)

    return render(
        request,
        "configuracoes/editar_perfil.html",
        {
            "form": form,
            "perfil": perfil,
            "item_ativo": "configuracoes",
        },
    )


@login_required
def editar_escritorio(request):
    configuracao = _obter_configuracao_escritorio()

    if request.method == "POST":
        form = ConfiguracaoEscritorioForm(request.POST, instance=configuracao)
        if form.is_valid():
            form.save()
            return redirect("configuracoes:index")
    else:
        form = ConfiguracaoEscritorioForm(instance=configuracao)

    return render(
        request,
        "configuracoes/editar_escritorio.html",
        {
            "form": form,
            "configuracao": configuracao,
            "item_ativo": "configuracoes",
        },
    )
