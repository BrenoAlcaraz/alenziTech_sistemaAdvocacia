from django.contrib import admin
from .models import Plano, Assinatura


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ["nome", "preco_mensal", "limite_processos", "limite_usuarios", "ativo"]
    list_filter = ["ativo"]


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ["escritorio", "plano", "status", "inicio", "proximo_vencimento"]
    list_filter = ["status", "plano"]
