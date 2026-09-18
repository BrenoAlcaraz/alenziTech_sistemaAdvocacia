from django.urls import path
from . import views

app_name = "modelos"

urlpatterns = [
    path("modelos/", views.lista, name="lista"),
    path("modelos/novo/", views.novo, name="novo"),
    path("modelos/importar/", views.importar, name="importar"),
    path("modelos/repetitivas/gerar/", views.gerar_pecas_repetitivas, name="gerar_pecas_repetitivas"),
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
    path(
        "modelos/estilo/assinaturas/adicionar/",
        views.adicionar_assinatura_estilo,
        name="adicionar_assinatura_estilo",
    ),
    path(
        "modelos/estilo/assinaturas/<int:pk>/remover/",
        views.remover_assinatura_estilo,
        name="remover_assinatura_estilo",
    ),
    path(
        "modelos/estilo/assinaturas/<int:pk>/imagem/",
        views.imagem_assinatura_estilo,
        name="imagem_assinatura_estilo",
    ),
    path("modelos/categorias/", views.categorias, name="categorias"),
    path("modelos/categorias/<int:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("modelos/categorias/<int:pk>/excluir/", views.categoria_excluir, name="categoria_excluir"),
    path("modelos/<int:pk>/editar/", views.editar, name="editar"),
    path("modelos/<int:pk>/excluir/", views.excluir, name="excluir"),
    path("modelos/<int:pk>/reverter/<int:versao_pk>/", views.reverter, name="reverter"),
    path("modelos/<int:pk>/baixar/pdf/", views.baixar_pdf, name="baixar_pdf"),
    path("modelos/<int:pk>/baixar/docx/", views.baixar_docx, name="baixar_docx"),
    path("modelos/<int:pk>/", views.detalhe, name="detalhe"),
]
