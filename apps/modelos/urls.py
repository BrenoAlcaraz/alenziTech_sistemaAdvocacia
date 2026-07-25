from django.urls import path
from . import views

app_name = "modelos"

urlpatterns = [
    path("modelos/", views.lista, name="lista"),
    path("modelos/novo/", views.novo, name="novo"),
    path("modelos/importar/", views.importar, name="importar"),
    path("modelos/<int:pk>/editar/", views.editar, name="editar"),
    path("modelos/<int:pk>/", views.detalhe, name="detalhe"),
]
