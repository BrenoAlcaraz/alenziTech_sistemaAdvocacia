from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("chat/", views.lista, name="lista"),
    path("chat/<int:pk>/", views.detalhe, name="detalhe"),
]
