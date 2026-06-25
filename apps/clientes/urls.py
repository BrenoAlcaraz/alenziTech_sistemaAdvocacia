from django.urls import path
from . import views

app_name = "clientes"

urlpatterns = [
    path("clientes/", views.lista, name="lista"),
    path("clientes/novo/", views.novo, name="novo"),
    path("clientes/<int:pk>/", views.detalhe, name="detalhe"),
    path("clientes/<int:pk>/editar/", views.editar, name="editar"),
    path("clientes/<int:pk>/desativar/", views.desativar, name="desativar"),
]
