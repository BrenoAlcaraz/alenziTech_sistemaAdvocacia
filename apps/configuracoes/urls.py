from django.urls import path
from . import views

app_name = "configuracoes"

urlpatterns = [
    path("configuracoes/", views.index, name="index"),
    path("configuracoes/perfil/editar/", views.editar_perfil, name="editar_perfil"),
]
