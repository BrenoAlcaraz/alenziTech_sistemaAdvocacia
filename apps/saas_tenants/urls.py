from django.urls import path

from . import views


app_name = "saas_tenants"

urlpatterns = [
    path(
        "identidade-visual/<str:tipo_arquivo>/",
        views.arquivo_identidade_visual,
        name="arquivo_identidade_visual",
    ),
]
