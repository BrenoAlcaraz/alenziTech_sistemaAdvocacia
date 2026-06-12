from django.contrib import admin
from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ["user", "nome_completo", "cargo", "is_admin_escritorio", "criado_em"]
    list_filter = ["is_admin_escritorio"]
    search_fields = ["nome_completo", "user__username"]
