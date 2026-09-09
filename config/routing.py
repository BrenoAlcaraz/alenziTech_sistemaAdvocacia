from django.urls import path

from apps.chat.consumers import ConversaConsumer, ListaConsumer, SalaGlobalConsumer

websocket_urlpatterns = [
    path("ws/chat/lista/", ListaConsumer.as_asgi()),
    path("ws/chat/global/", SalaGlobalConsumer.as_asgi()),
    path("ws/chat/<int:pk>/", ConversaConsumer.as_asgi()),
]
