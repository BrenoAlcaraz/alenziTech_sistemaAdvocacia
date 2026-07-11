from django.contrib import admin
from .models import Departamento, MembroDepartamento, PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ["user", "nome_completo", "cargo", "is_admin_escritorio", "criado_em"]
    list_filter = ["is_admin_escritorio"]
    search_fields = ["nome_completo", "user__username"]


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ["nome", "departamento_pai", "ativo", "criado_em", "atualizado_em"]
    list_filter = ["ativo", "departamento_pai"]
    search_fields = ["nome", "descricao"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(MembroDepartamento)
class MembroDepartamentoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "departamento", "eh_gerente", "ativo", "criado_em"]
    list_filter = ["eh_gerente", "ativo", "departamento"]
    search_fields = ["usuario__username", "usuario__email", "departamento__nome"]
    readonly_fields = ["criado_em"]
