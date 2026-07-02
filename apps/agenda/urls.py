from django.urls import path
from . import views

app_name = "agenda"

urlpatterns = [
    path("agenda/", views.index, name="index"),
    path("agenda/novo/", views.form_compromisso, name="novo"),
    path("agenda/<int:pk>/editar/", views.editar, name="editar"),
    path("agenda/<int:pk>/concluir/", views.concluir, name="concluir"),
    path("agenda/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
    path("agenda/<int:pk>/reabrir/", views.reabrir, name="reabrir"),
    path("agenda/<int:pk>/excluir/", views.excluir, name="excluir"),
]
