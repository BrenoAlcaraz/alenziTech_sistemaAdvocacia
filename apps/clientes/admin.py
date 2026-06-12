from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nome_razao_social", "tipo", "cpf_cnpj", "email", "criado_em"]
    list_filter = ["tipo"]
    search_fields = ["nome_razao_social", "cpf_cnpj"]
