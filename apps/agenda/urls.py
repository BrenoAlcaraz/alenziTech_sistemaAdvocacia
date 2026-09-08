from django.urls import path
from . import views

app_name = "agenda"

urlpatterns = [
    path("agenda/", views.index, name="index"),
    path("agenda/cancelados/", views.cancelados, name="cancelados"),
    path("agenda/processos-por-cliente/", views.processos_por_cliente, name="processos_por_cliente"),
    path("agenda/novo/", views.form_compromisso, name="novo"),
    path("agenda/<int:pk>/editar/", views.editar, name="editar"),
    path("agenda/<int:pk>/concluir/", views.concluir, name="concluir"),
    path("agenda/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
    path("agenda/<int:pk>/reabrir/", views.reabrir, name="reabrir"),
    path("agenda/<int:pk>/excluir/", views.excluir, name="excluir"),
    path("agenda/<int:pk>/participantes/adicionar/", views.adicionar_participante, name="adicionar_participante"),
    path("agenda/<int:pk>/participantes/<int:usuario_pk>/remover/", views.remover_participante, name="remover_participante"),
    path("agenda/<int:pk>/confirmar-presenca/", views.confirmar_presenca, name="confirmar_presenca"),
    path("agenda/<int:pk>/recusar-presenca/", views.recusar_presenca, name="recusar_presenca"),
]
