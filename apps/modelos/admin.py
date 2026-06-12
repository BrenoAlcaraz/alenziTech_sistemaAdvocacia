from django.contrib import admin
from .models import ModeloPeca, EstiloEscritorio


@admin.register(ModeloPeca)
class ModeloPecaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "categoria", "area_direito", "criado_por", "criado_em"]
    search_fields = ["titulo", "categoria"]


@admin.register(EstiloEscritorio)
class EstiloAdmin(admin.ModelAdmin):
    list_display = ["atualizado_em"]
