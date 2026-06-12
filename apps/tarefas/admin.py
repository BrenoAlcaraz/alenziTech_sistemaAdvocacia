from django.contrib import admin
from .models import Tarefa


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "status", "prioridade", "responsavel", "prazo"]
    list_filter = ["status", "prioridade"]
    search_fields = ["titulo"]
