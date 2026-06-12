from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Autenticação
    path("", include("apps.accounts.urls")),

    # Módulos do sistema (acessados por tenant)
    path("", include("apps.dashboard.urls")),
    path("", include("apps.processos.urls")),
    path("", include("apps.clientes.urls")),
    path("", include("apps.tarefas.urls")),
    path("", include("apps.financeiro.urls")),
    path("", include("apps.agenda.urls")),
    path("", include("apps.chat.urls")),
    path("", include("apps.modelos.urls")),
    path("", include("apps.laboratorio.urls")),
    path("", include("apps.configuracoes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
