"""URLs do domínio da plataforma (schema `public`) — só o Django Admin.

Telas de escritório ficam em `config/urls.py` (ROOT_URLCONF), servido
apenas nos domínios de escritório; ver `PUBLIC_SCHEMA_URLCONF`.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    # LOGOUT_REDIRECT_URL aponta para o login do escritório, que não existe aqui.
    path("admin/logout/", LogoutView.as_view(next_page="admin:login")),
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
