from django.urls import path
from . import views

app_name = "configuracoes"

urlpatterns = [
    path("configuracoes/", views.index, name="index"),
    path("configuracoes/perfil/editar/", views.editar_perfil, name="editar_perfil"),
    path("configuracoes/perfil/alterar-senha/", views.alterar_senha, name="alterar_senha"),
    path("configuracoes/escritorio/", views.editar_escritorio, name="editar_escritorio"),
    path("configuracoes/usuarios/novo/", views.novo_usuario, name="novo_usuario"),
    path("configuracoes/equipes/", views.equipes, name="equipes"),
    path("configuracoes/equipes/novo/", views.nova_equipe, name="nova_equipe"),
    path("configuracoes/equipes/<int:pk>/editar/", views.editar_equipe, name="editar_equipe"),
    path("configuracoes/equipes/<int:pk>/membros/", views.equipe_membros, name="equipe_membros"),
    path("configuracoes/equipes/<int:pk>/membros/<int:membro_pk>/remover/", views.remover_membro_equipe, name="remover_membro_equipe"),
    path("configuracoes/equipes/<int:pk>/membros/<int:membro_pk>/alternar-gerente/", views.alternar_gerente_equipe, name="alternar_gerente_equipe"),
    path("configuracoes/papeis/", views.papeis, name="papeis"),
    path("configuracoes/papeis/novo/", views.novo_papel, name="novo_papel"),
    path("configuracoes/papeis/<int:pk>/editar/", views.editar_papel, name="editar_papel"),
    path("configuracoes/papeis/<int:pk>/usuarios/", views.papel_usuarios, name="papel_usuarios"),
    path("configuracoes/papeis/<int:pk>/usuarios/<int:usuario_papel_pk>/remover/", views.remover_usuario_papel, name="remover_usuario_papel"),
    path("configuracoes/permissoes/", views.permissoes, name="permissoes"),
    path("configuracoes/usuarios/<int:user_pk>/permissoes/", views.usuario_overrides, name="usuario_overrides"),
]
