from django.contrib import admin
from .models import CasoLaboratorio


@admin.register(CasoLaboratorio)
class CasoLaboratorioAdmin(admin.ModelAdmin):
    list_display = ["nome_cliente", "tipo_peca", "area_direito", "status", "criado_em"]
    list_filter = ["status", "tipo_peca"]
