from django.urls import path
from . import views

app_name = "tarefas"

urlpatterns = [
    path("tarefas/", views.quadro, name="quadro"),
    path("tarefas/processos-por-cliente/", views.processos_por_cliente, name="processos_por_cliente"),
    path("tarefas/lista/", views.lista, name="lista"),
    path("tarefas/convites/<int:pk>/responder/", views.convite_responder, name="convite_responder"),
    path("tarefas/nova/", views.nova, name="nova"),
    path("tarefas/<int:pk>/editar/", views.editar, name="editar"),
    path(
        "tarefas/<int:pk>/participantes/adicionar/",
        views.adicionar_participante,
        name="adicionar_participante",
    ),
    path(
        "tarefas/<int:pk>/participantes/<int:usuario_pk>/remover/",
        views.remover_participante,
        name="remover_participante",
    ),
    path(
        "tarefas/<int:pk>/participantes/equipe/adicionar/",
        views.adicionar_equipe_participante,
        name="adicionar_equipe_participante",
    ),
    path("tarefas/<int:pk>/reatribuir/", views.reatribuir, name="reatribuir"),
    path("tarefas/<int:pk>/concluir/", views.concluir, name="concluir"),
    path("tarefas/<int:pk>/reabrir/", views.reabrir, name="reabrir"),
    path("tarefas/<int:pk>/iniciar/", views.iniciar, name="iniciar"),
    path("tarefas/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
    path("tarefas/<int:pk>/excluir/", views.excluir, name="excluir"),
]
