from django.contrib import admin
from .models import Conversa, LeituraConversa, Mensagem


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "tipo", "criada_em"]


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ["conversa", "autor", "enviada_em"]


@admin.register(LeituraConversa)
class LeituraConversaAdmin(admin.ModelAdmin):
    list_display = ["conversa", "usuario", "lida_em"]
