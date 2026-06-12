from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import Escritorio, Dominio, ConfiguracaoVisual


@admin.register(Escritorio)
class EscritorioAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ["nome", "slug", "schema_name", "ativo", "criado_em"]
    list_filter = ["ativo"]
    search_fields = ["nome", "slug"]


@admin.register(Dominio)
class DominioAdmin(admin.ModelAdmin):
    list_display = ["domain", "tenant", "is_primary"]


@admin.register(ConfiguracaoVisual)
class ConfiguracaoVisualAdmin(admin.ModelAdmin):
    list_display = ["escritorio", "nome_exibicao", "cor_primaria"]
