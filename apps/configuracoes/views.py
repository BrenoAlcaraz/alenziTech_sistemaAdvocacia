from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from apps.accounts.decorators import (
    nome_legivel_grupo,
    obter_papel_principal_usuario,
    requer_admin_escritorio,
    usuario_admin_escritorio,
)
from apps.accounts.forms import CriarUsuarioEscritorioForm, DepartamentoForm, MembroDepartamentoForm, PerfilUsuarioForm
from apps.accounts.models import Departamento, MembroDepartamento, PerfilUsuario
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
        .prefetch_related(
            "groups",
            "membros_departamento",
            "membros_departamento__departamento",
        )
        .order_by("first_name", "last_name", "username")
    )
    usuarios_ativos = usuarios.count()

    usuarios_contexto = []
    for usuario in usuarios:
        grupo = obter_papel_principal_usuario(usuario)
        membros_departamento = [
            membro
            for membro in usuario.membros_departamento.all()
            if membro.ativo and membro.departamento.ativo
        ]
        usuarios_contexto.append({
            "usuario": usuario,
            "papel": grupo.name if grupo else "",
            "papel_nome": nome_legivel_grupo(grupo.name) if grupo else "Sem papel definido",
            "membros_departamento": membros_departamento,
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
def departamentos(request):
    deps = (
        Departamento.objects
        .select_related("departamento_pai")
        .prefetch_related("membros", "membros__usuario")
        .order_by("nome")
    )

    departamentos_contexto = []
    for dep in deps:
        membros_list = list(dep.membros.all())
        departamentos_contexto.append({
            "departamento": dep,
            "total_membros": len(membros_list),
            "total_gerentes": sum(1 for m in membros_list if m.eh_gerente),
        })

    return render(
        request,
        "configuracoes/departamentos.html",
        {
            "departamentos_contexto": departamentos_contexto,
            "item_ativo": "configuracoes",
        },
    )


@requer_admin_escritorio
def novo_departamento(request):
    if request.method == "POST":
        form = DepartamentoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("configuracoes:departamentos")
    else:
        form = DepartamentoForm()

    return render(
        request,
        "configuracoes/departamento_form.html",
        {
            "form": form,
            "modo": "novo",
            "titulo": "Novo departamento",
            "item_ativo": "configuracoes",
        },
    )


@requer_admin_escritorio
def editar_departamento(request, pk):
    departamento = get_object_or_404(Departamento, pk=pk)

    if request.method == "POST":
        form = DepartamentoForm(request.POST, instance=departamento)
        if form.is_valid():
            form.save()
            return redirect("configuracoes:departamentos")
    else:
        form = DepartamentoForm(instance=departamento)

    return render(
        request,
        "configuracoes/departamento_form.html",
        {
            "form": form,
            "departamento": departamento,
            "modo": "editar",
            "titulo": "Editar departamento",
            "item_ativo": "configuracoes",
        },
    )


@requer_admin_escritorio
def departamento_membros(request, pk):
    departamento = get_object_or_404(Departamento, pk=pk)

    if request.method == "POST":
        form = MembroDepartamentoForm(request.POST, departamento=departamento)
        if form.is_valid():
            membro = form.save(commit=False)
            membro.departamento = departamento
            membro.ativo = True
            membro.save()
            return redirect("configuracoes:departamento_membros", pk=departamento.pk)
    else:
        form = MembroDepartamentoForm(departamento=departamento)

    membros = (
        MembroDepartamento.objects
        .filter(departamento=departamento)
        .select_related("usuario", "usuario__perfil")
        .order_by("-eh_gerente", "usuario__username")
    )

    return render(
        request,
        "configuracoes/departamento_membros.html",
        {
            "departamento": departamento,
            "form": form,
            "membros": membros,
            "item_ativo": "configuracoes",
        },
    )


@requer_admin_escritorio
def remover_membro_departamento(request, pk, membro_pk):
    departamento = get_object_or_404(Departamento, pk=pk)
    membro = get_object_or_404(
        MembroDepartamento,
        pk=membro_pk,
        departamento=departamento,
    )

    if request.method == "POST":
        membro.delete()

    return redirect("configuracoes:departamento_membros", pk=departamento.pk)


@requer_admin_escritorio
def alternar_gerente_departamento(request, pk, membro_pk):
    departamento = get_object_or_404(Departamento, pk=pk)
    membro = get_object_or_404(
        MembroDepartamento,
        pk=membro_pk,
        departamento=departamento,
    )

    if request.method == "POST":
        membro.eh_gerente = not membro.eh_gerente
        membro.save(update_fields=["eh_gerente"])

    return redirect("configuracoes:departamento_membros", pk=departamento.pk)



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
