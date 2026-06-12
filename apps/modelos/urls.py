from django.urls import path
from . import views

app_name = "modelos"

urlpatterns = [
    path("modelos/", views.lista, name="lista"),
    path("modelos/novo/", views.novo, name="novo"),
    path("modelos/<int:pk>/", views.detalhe, name="detalhe"),
]
