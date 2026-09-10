from django.contrib import admin
from .models import CategoriaModeloPeca, ModeloPeca, EstiloEscritorio, VersaoModeloPeca


@admin.register(ModeloPeca)
class ModeloPecaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "categoria", "area_direito", "criado_por", "criado_em"]
    search_fields = ["titulo", "categoria__nome"]


@admin.register(CategoriaModeloPeca)
class CategoriaModeloPecaAdmin(admin.ModelAdmin):
    list_display = ["nome"]
    search_fields = ["nome"]


@admin.register(VersaoModeloPeca)
class VersaoModeloPecaAdmin(admin.ModelAdmin):
    list_display = ["modelo", "titulo", "editado_por", "criado_em"]
    search_fields = ["titulo", "modelo__titulo"]


@admin.register(EstiloEscritorio)
class EstiloAdmin(admin.ModelAdmin):
    list_display = ["atualizado_em"]
