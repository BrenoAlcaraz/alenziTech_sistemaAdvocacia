from django.urls import path
from . import views

app_name = "processos"

urlpatterns = [
    path("processos/", views.lista, name="lista"),
    path("processos/novo/", views.novo, name="novo"),
    path("processos/arquivados/", views.arquivados, name="arquivados"),
    path("processos/<int:pk>/", views.detalhe, name="detalhe"),
    path("processos/<int:pk>/editar/", views.editar, name="editar"),
    path("processos/<int:pk>/arquivar/", views.arquivar, name="arquivar"),
    path("processos/<int:pk>/reabrir/", views.reabrir, name="reabrir"),
    path("processos/<int:pk>/excluir/", views.excluir, name="excluir"),
    path("processos/<int:pk>/movimentacoes/nova/", views.adicionar_movimentacao, name="adicionar_movimentacao"),
    path(
        "processos/<int:pk>/andamentos/<int:andamento_pk>/confirmar/",
        views.confirmar_sugestao,
        name="confirmar_sugestao",
    ),
    path(
        "processos/<int:pk>/andamentos/<int:andamento_pk>/rejeitar/",
        views.rejeitar_sugestao,
        name="rejeitar_sugestao",
    ),
    path(
        "processos/<int:pk>/andamentos/<int:andamento_pk>/editar/",
        views.editar_sugestao,
        name="editar_sugestao",
    ),
    path("processos/<int:pk>/partes/nova/", views.adicionar_parte, name="adicionar_parte"),
    path(
        "processos/<int:pk>/apensos/adicionar/",
        views.adicionar_apenso,
        name="adicionar_apenso",
    ),
    path(
        "processos/<int:pk>/apensos/<int:vinculo_pk>/remover/",
        views.remover_apenso,
        name="remover_apenso",
    ),
    path(
        "processos/<int:pk>/partes/<int:parte_pk>/editar/",
        views.editar_parte,
        name="editar_parte",
    ),
    path(
        "processos/<int:pk>/integrantes/adicionar/",
        views.adicionar_integrante,
        name="adicionar_integrante",
    ),
    path(
        "processos/<int:pk>/integrantes/<int:usuario_pk>/remover/",
        views.remover_integrante,
        name="remover_integrante",
    ),
    path(
        "processos/<int:pk>/integrantes/equipe/adicionar/",
        views.adicionar_equipe_integrante,
        name="adicionar_equipe_integrante",
    ),
    path(
        "processos/<int:pk>/documentos/nova/",
        views.adicionar_documento,
        name="adicionar_documento",
    ),
    path(
        "processos/<int:pk>/documentos/<int:documento_pk>/excluir/",
        views.excluir_documento,
        name="excluir_documento",
    ),
    path(
        "processos/documentos/<int:documento_pk>/baixar/",
        views.baixar_documento,
        name="baixar_documento",
    ),
    path(
        "processos/custas/<int:solicitacao_pk>/comprovante/",
        views.baixar_comprovante_custa,
        name="baixar_comprovante_custa",
    ),
    path("processos/intimacoes/nova/", views.nova_intimacao, name="nova_intimacao"),
    path(
        "processos/intimacoes/<int:pk>/manifestar/",
        views.manifestar_intimacao,
        name="manifestar_intimacao",
    ),
]
