from django.contrib import admin
from .models import LancamentoFinanceiro, CustaJudicial


@admin.register(LancamentoFinanceiro)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "data", "cliente"]
    list_filter = ["tipo", "categoria"]


@admin.register(CustaJudicial)
class CustaAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "data", "cliente"]
