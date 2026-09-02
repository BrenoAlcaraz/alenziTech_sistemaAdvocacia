from django.contrib import admin

from .models import (
    MovimentacaoProcessual,
    ParteProcesso,
    Processo,
    VinculoProcessoApenso,
)


@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "area_direito", "status", "cliente", "prazo_proximo"]
    list_filter = ["area_direito", "status"]
    search_fields = ["titulo", "numero"]


@admin.register(MovimentacaoProcessual)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ["processo", "tipo", "data", "autor"]


@admin.register(VinculoProcessoApenso)
class VinculoProcessoApensoAdmin(admin.ModelAdmin):
    list_display = ["processo_menor", "processo_maior", "criado_em"]
    search_fields = [
        "processo_menor__titulo",
        "processo_menor__numero",
        "processo_maior__titulo",
        "processo_maior__numero",
    ]
    readonly_fields = ["criado_em"]


@admin.register(ParteProcesso)
class ParteAdmin(admin.ModelAdmin):
    list_display = ["nome", "papel", "processo"]
    list_filter = ["papel"]
    search_fields = ["nome", "cpf_cnpj"]
