from django.contrib import admin
from .models import Processo, MovimentacaoProcessual, ParteProcesso


@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "area_direito", "status", "cliente", "prazo_proximo"]
    list_filter = ["area_direito", "status"]
    search_fields = ["titulo", "numero"]


@admin.register(MovimentacaoProcessual)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ["processo", "tipo", "data", "autor"]


@admin.register(ParteProcesso)
class ParteAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "processo"]
