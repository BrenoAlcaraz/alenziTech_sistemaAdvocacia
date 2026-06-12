from django.urls import path
from . import views

app_name = "tarefas"

urlpatterns = [
    path("tarefas/", views.quadro, name="quadro"),
    path("tarefas/lista/", views.lista, name="lista"),
    path("tarefas/nova/", views.nova, name="nova"),
]
