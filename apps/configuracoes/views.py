from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from apps.accounts.decorators import (
    nome_legivel_grupo,
    obter_papel_principal_usuario,
    requer_admin_escritorio,
    usuario_admin_escritorio,
)
from apps.accounts.forms import CriarUsuarioEscritorioForm, PerfilUsuarioForm
from apps.accounts.models import PerfilUsuario
from .models import ConfiguracaoEscritorio
from .forms import ConfiguracaoEscritorioForm


def _obter_configuracao_escritorio():
    configuracao, _ = ConfiguracaoEscritorio.objects.get_or_create(pk=1)
    return configuracao


@login_required
def index(request):
    perfil_usuario = getattr(request.user, 'perfil', None)

    usuarios = (
        User.objects.filter(is_active=True)
        .select_related("perfil")
        .prefetch_related("groups")
        .order_by("first_name", "last_name", "username")
    )
    usuarios_ativos = usuarios.count()

    usuarios_contexto = []
    for usuario in usuarios:
        grupo = obter_papel_principal_usuario(usuario)
        usuarios_contexto.append({
            "usuario": usuario,
            "papel": grupo.name if grupo else "",
            "papel_nome": nome_legivel_grupo(grupo.name) if grupo else "Sem papel definido",
        })

    configuracao_escritorio = _obter_configuracao_escritorio()
    usuario_e_admin_escritorio = usuario_admin_escritorio(request.user)

    return render(request, "configuracoes/index.html", {
        "perfil_usuario": perfil_usuario,
        "usuarios_contexto": usuarios_contexto,
        "plano_nome": "Mestre",
        "usuarios_ativos": usuarios_ativos,
        "limite_usuarios": 10,
        "configuracao_escritorio": configuracao_escritorio,
        "usuario_e_admin_escritorio": usuario_e_admin_escritorio,
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


@requer_admin_escritorio
def novo_usuario(request):
    if request.method == "POST":
        form = CriarUsuarioEscritorioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("configuracoes:index")
    else:
        form = CriarUsuarioEscritorioForm()

    return render(
        request,
        "configuracoes/novo_usuario.html",
        {
            "form": form,
            "item_ativo": "configuracoes",
        },
    )


@requer_admin_escritorio
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
