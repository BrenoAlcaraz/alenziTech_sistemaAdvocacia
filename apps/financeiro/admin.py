from django.contrib import admin
from .models import LancamentoFinanceiro, CustaJudicial


@admin.register(LancamentoFinanceiro)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "data_vencimento", "status", "cliente"]
    list_filter = ["tipo", "categoria", "status"]


@admin.register(CustaJudicial)
class CustaAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "data", "cliente"]
