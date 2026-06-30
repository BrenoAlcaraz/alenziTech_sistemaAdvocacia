from django.urls import path
from . import views

app_name = "tarefas"

urlpatterns = [
    path("tarefas/", views.quadro, name="quadro"),
    path("tarefas/lista/", views.lista, name="lista"),
    path("tarefas/nova/", views.nova, name="nova"),
    path("tarefas/<int:pk>/editar/", views.editar, name="editar"),
    path("tarefas/<int:pk>/concluir/", views.concluir, name="concluir"),
    path("tarefas/<int:pk>/reabrir/", views.reabrir, name="reabrir"),
    path("tarefas/<int:pk>/iniciar/", views.iniciar, name="iniciar"),
    path("tarefas/<int:pk>/excluir/", views.excluir, name="excluir"),
]
