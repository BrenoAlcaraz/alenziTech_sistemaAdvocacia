from django.contrib import admin
from .models import LancamentoFinanceiro, CustaJudicial, SolicitacaoFinanceira


@admin.register(LancamentoFinanceiro)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "data_vencimento", "status", "cliente"]
    list_filter = ["tipo", "categoria", "status"]


@admin.register(CustaJudicial)
class CustaAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "data", "cliente"]


@admin.register(SolicitacaoFinanceira)
class SolicitacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ["descricao", "tipo", "valor", "status", "solicitante", "criado_em"]
    list_filter = ["tipo", "status"]
