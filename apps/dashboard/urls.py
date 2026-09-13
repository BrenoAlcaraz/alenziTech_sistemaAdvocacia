from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("analise/", views.analise, name="analise"),
    path("gestor/", views.gestor, name="gestor"),
    path("gestor/<int:user_pk>/", views.gestor_usuario, name="gestor_usuario"),
]
