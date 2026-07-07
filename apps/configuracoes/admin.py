from django.contrib import admin

from .models import ConfiguracaoEscritorio


@admin.register(ConfiguracaoEscritorio)
class ConfiguracaoEscritorioAdmin(admin.ModelAdmin):
    list_display = [
        "nome_escritorio",
        "nome_fantasia",
        "email",
        "telefone",
        "atualizado_em",
    ]
    search_fields = [
        "nome_escritorio",
        "nome_fantasia",
        "cnpj",
        "email",
    ]
    readonly_fields = [
        "criado_em",
        "atualizado_em",
    ]
