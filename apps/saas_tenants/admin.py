from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
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


admin.site.unregister(User)


@admin.register(User)
class UsuarioPlataformaAdmin(UserAdmin):
    # Excluir User no public quebra: o collector do ORM consulta tabelas de
    # escritório (PerfilUsuario, Processo...) que só existem nos schemas de tenant.
    def has_delete_permission(self, request, obj=None):
        return False
