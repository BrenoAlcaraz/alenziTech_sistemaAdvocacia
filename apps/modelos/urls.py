from django.urls import path
from . import views

app_name = "modelos"

urlpatterns = [
    path("modelos/", views.lista, name="lista"),
    path("modelos/novo/", views.novo, name="novo"),
    path("modelos/importar/", views.importar, name="importar"),
    path("modelos/estilo/editar/", views.editar_estilo, name="editar_estilo"),
    path(
        "modelos/estilo/documento/editar/",
        views.editar_estilo_documento,
        name="editar_estilo_documento",
    ),
    path(
        "modelos/estilo/documento/imagem/<str:slot>/",
        views.imagem_estilo_documento,
        name="imagem_estilo_documento",
    ),
    path("modelos/categorias/", views.categorias, name="categorias"),
    path("modelos/categorias/<int:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("modelos/categorias/<int:pk>/excluir/", views.categoria_excluir, name="categoria_excluir"),
    path("modelos/<int:pk>/editar/", views.editar, name="editar"),
    path("modelos/<int:pk>/excluir/", views.excluir, name="excluir"),
    path("modelos/<int:pk>/reverter/<int:versao_pk>/", views.reverter, name="reverter"),
    path("modelos/<int:pk>/", views.detalhe, name="detalhe"),
]
