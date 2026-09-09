from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("chat/", views.lista, name="lista"),
    path("chat/global/", views.global_sala, name="global"),
    path("chat/nova/individual/", views.nova_individual, name="nova_individual"),
    path("chat/nova/grupo/", views.nova_grupo, name="nova_grupo"),
    path("chat/<int:pk>/", views.detalhe, name="detalhe"),
    path("chat/mensagem/<int:pk>/anexo/", views.anexo_mensagem, name="anexo_mensagem"),
]
