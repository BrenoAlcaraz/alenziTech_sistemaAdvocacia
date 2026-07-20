from django.urls import path
from . import views

app_name = "configuracoes"

urlpatterns = [
    path("configuracoes/", views.index, name="index"),
    path("configuracoes/perfil/editar/", views.editar_perfil, name="editar_perfil"),
    path("configuracoes/escritorio/", views.editar_escritorio, name="editar_escritorio"),
    path("configuracoes/usuarios/novo/", views.novo_usuario, name="novo_usuario"),
    path("configuracoes/equipes/", views.equipes, name="equipes"),
    path("configuracoes/equipes/novo/", views.nova_equipe, name="nova_equipe"),
    path("configuracoes/equipes/<int:pk>/editar/", views.editar_equipe, name="editar_equipe"),
    path("configuracoes/equipes/<int:pk>/membros/", views.equipe_membros, name="equipe_membros"),
    path("configuracoes/equipes/<int:pk>/membros/<int:membro_pk>/remover/", views.remover_membro_equipe, name="remover_membro_equipe"),
    path("configuracoes/equipes/<int:pk>/membros/<int:membro_pk>/alternar-gerente/", views.alternar_gerente_equipe, name="alternar_gerente_equipe"),
    path("configuracoes/permissoes/", views.permissoes, name="permissoes"),
]
