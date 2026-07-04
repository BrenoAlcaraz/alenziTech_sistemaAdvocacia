from django.urls import path
from . import views

app_name = "financeiro"

urlpatterns = [
    path("financeiro/", views.index, name="index"),
    path("financeiro/custas/", views.custas, name="custas"),
    path("financeiro/lancamentos/novo/", views.form_lancamento, name="form_lancamento"),
    path("financeiro/lancamentos/<int:pk>/editar/", views.editar_lancamento, name="editar_lancamento"),
    path("financeiro/lancamentos/<int:pk>/marcar-pago/", views.marcar_pago, name="marcar_pago"),
    path("financeiro/lancamentos/<int:pk>/cancelar/", views.cancelar_lancamento, name="cancelar_lancamento"),
    path("financeiro/lancamentos/<int:pk>/reabrir/", views.reabrir_lancamento, name="reabrir_lancamento"),
    path("financeiro/custas/nova/", views.form_custa, name="form_custa"),
]
