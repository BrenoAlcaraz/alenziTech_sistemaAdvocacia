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
        "processos/<int:pk>/partes/<int:parte_pk>/advogados/novo/",
        views.adicionar_advogado,
        name="adicionar_advogado",
    ),
    path(
        "processos/<int:pk>/partes/<int:parte_pk>/classificacao/",
        views.alterar_classificacao_parte,
        name="alterar_classificacao_parte",
    ),
    path(
        "processos/<int:pk>/partes/<int:parte_pk>/advogados/<int:representante_pk>/remover/",
        views.remover_advogado,
        name="remover_advogado",
    ),
]
