from django.contrib import admin
from .models import (
    Equipe,
    HabilitacaoPapel,
    HabilitacaoUsuario,
    MembroEquipe,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    PermissaoUsuario,
    UsuarioPapel,
)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ["user", "nome_completo", "cargo", "is_admin_escritorio", "criado_em"]
    list_filter = ["is_admin_escritorio"]
    search_fields = ["nome_completo", "user__username"]


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ["nome", "equipe_pai", "ativo", "criado_em", "atualizado_em"]
    list_filter = ["ativo", "equipe_pai"]
    search_fields = ["nome", "descricao"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(MembroEquipe)
class MembroEquipeAdmin(admin.ModelAdmin):
    list_display = ["usuario", "equipe", "eh_gerente", "ativo", "criado_em"]
    list_filter = ["eh_gerente", "ativo", "equipe"]
    search_fields = ["usuario__username", "usuario__email", "equipe__nome"]
    readonly_fields = ["criado_em"]


@admin.register(PapelAcesso)
class PapelAcessoAdmin(admin.ModelAdmin):
    list_display = ["nome", "ativo", "protegido_sistema", "codigo_preset", "criado_em"]
    list_filter = ["ativo", "protegido_sistema"]
    search_fields = ["nome", "codigo_preset"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(UsuarioPapel)
class UsuarioPapelAdmin(admin.ModelAdmin):
    list_display = ["usuario", "papel", "ativo", "atribuido_por", "criado_em"]
    list_filter = ["ativo", "papel"]
    search_fields = ["usuario__username", "usuario__email", "papel__nome"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(PermissaoPapel)
class PermissaoPapelAdmin(admin.ModelAdmin):
    list_display = ["__str__", "tipo_conta", "papel", "modulo", "nivel", "ativo"]
    list_filter = ["modulo", "ativo", "nivel", "tipo_conta"]
    search_fields = ["papel__nome"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(PermissaoUsuario)
class PermissaoUsuarioAdmin(admin.ModelAdmin):
    list_display = ["usuario", "modulo", "nivel", "ativo"]
    list_filter = ["modulo", "ativo", "nivel"]
    search_fields = ["usuario__username", "usuario__email"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(HabilitacaoPapel)
class HabilitacaoPapelAdmin(admin.ModelAdmin):
    list_display = ["__str__", "tipo_conta", "papel", "modulo", "item", "ativo"]
    list_filter = ["modulo", "item", "ativo", "tipo_conta"]
    search_fields = ["papel__nome"]
    readonly_fields = ["criado_em", "atualizado_em"]


@admin.register(HabilitacaoUsuario)
class HabilitacaoUsuarioAdmin(admin.ModelAdmin):
    list_display = ["usuario", "modulo", "item", "ativo"]
    list_filter = ["modulo", "item", "ativo"]
    search_fields = ["usuario__username", "usuario__email"]
    readonly_fields = ["criado_em", "atualizado_em"]
