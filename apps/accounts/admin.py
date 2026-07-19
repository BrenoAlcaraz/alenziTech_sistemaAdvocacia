from django.contrib import admin
from .models import Equipe, MembroEquipe, PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ["user", "nome_completo", "cargo", "is_admin_escritorio", "criado_em"]
    list_filter = ["is_admin_escritorio"]
    search_fields = ["nome_completo", "user__username"]


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ["nome", "equipe_pai", "ativo", "criado_em", "atualizado_em"]
    list_filter = ["ativo", "equipe_pai"]
    search_fields = ["nome", "descricao"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(MembroEquipe)
class MembroEquipeAdmin(admin.ModelAdmin):
    list_display = ["usuario", "equipe", "eh_gerente", "ativo", "criado_em"]
    list_filter = ["eh_gerente", "ativo", "equipe"]
    search_fields = ["usuario__username", "usuario__email", "equipe__nome"]
    readonly_fields = ["criado_em"]
