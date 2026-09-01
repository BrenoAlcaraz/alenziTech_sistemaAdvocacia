from django.contrib import admin
from .models import ReatribuicaoTarefa, Tarefa


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "status", "prioridade", "responsavel", "criador", "prazo"]
    list_filter = ["status", "prioridade"]
    search_fields = ["titulo"]


@admin.register(ReatribuicaoTarefa)
class ReatribuicaoTarefaAdmin(admin.ModelAdmin):
    list_display = ["tarefa", "responsavel_anterior", "responsavel_novo", "autor", "criado_em"]
