from django.urls import path
from . import views

app_name = "agenda"

urlpatterns = [
    path("agenda/", views.index, name="index"),
    path("agenda/novo/", views.form_compromisso, name="novo"),
    path("agenda/<int:pk>/editar/", views.editar, name="editar"),
]
