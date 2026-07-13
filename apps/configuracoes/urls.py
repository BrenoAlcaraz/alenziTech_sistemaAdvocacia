from django.urls import path
from . import views

app_name = "configuracoes"

urlpatterns = [
    path("configuracoes/", views.index, name="index"),
    path("configuracoes/perfil/editar/", views.editar_perfil, name="editar_perfil"),
    path("configuracoes/escritorio/", views.editar_escritorio, name="editar_escritorio"),
    path("configuracoes/usuarios/novo/", views.novo_usuario, name="novo_usuario"),
    path("configuracoes/departamentos/", views.departamentos, name="departamentos"),
    path("configuracoes/departamentos/novo/", views.novo_departamento, name="novo_departamento"),
    path("configuracoes/departamentos/<int:pk>/editar/", views.editar_departamento, name="editar_departamento"),
]
