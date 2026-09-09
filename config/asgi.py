import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# get_asgi_application() carrega o app registry antes de qualquer import
# que toque em models (consumers, middleware de tenant) — mesma ordem
# exigida pelo Channels.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from apps.saas_tenants.channels_middleware import TenantWebsocketMiddleware  # noqa: E402
from config.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": TenantWebsocketMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
