from django.urls import path
from . import views

app_name = "financeiro"

urlpatterns = [
    path("financeiro/", views.index, name="index"),
    path("financeiro/custas/", views.custas, name="custas"),
    path("financeiro/lancamentos/novo/", views.form_lancamento, name="form_lancamento"),
    path("financeiro/custas/nova/", views.form_custa, name="form_custa"),
]
