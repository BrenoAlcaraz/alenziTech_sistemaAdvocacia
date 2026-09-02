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
    path("processos/<int:pk>/movimentacoes/nova/", views.adicionar_movimentacao, name="adicionar_movimentacao"),
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
]
