from django.contrib import admin
from .models import Compromisso


@admin.register(Compromisso)
class CompromissoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "tipo", "data_hora_inicio", "responsavel"]
    list_filter = ["tipo"]
