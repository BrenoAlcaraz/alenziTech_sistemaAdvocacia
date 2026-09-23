from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Identidade visual pública, resolvida pelo tenant da requisição
    path("", include("apps.saas_tenants.urls")),

    # Autenticação
    path("", include("apps.accounts.urls")),

    # Módulos do sistema (acessados por tenant)
    path("", include("apps.dashboard.urls")),
    path("", include("apps.processos.urls")),
    path("", include("apps.clientes.urls")),
    path("", include("apps.financeiro.urls")),
    path("", include("apps.agenda.urls")),
    # Tarefas foi incorporado à Agenda Jurídica (PDR-0034).
    re_path(r"^tarefas/", RedirectView.as_view(pattern_name="agenda:index", query_string=True)),
    path("", include("apps.chat.urls")),
    path("", include("apps.modelos.urls")),
    path("", include("apps.laboratorio.urls")),
    path("", include("apps.configuracoes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
