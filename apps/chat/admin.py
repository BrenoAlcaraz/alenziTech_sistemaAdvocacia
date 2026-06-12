from django.contrib import admin
from .models import Conversa, Mensagem


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "tipo", "criada_em"]


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ["conversa", "autor", "enviada_em", "lida"]
