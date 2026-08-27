from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.actions import delete_selected
from django.db.models import F

from .models import (
    AutoridadeProcessual,
    HistoricoClassificacaoParte,
    MovimentacaoProcessual,
    ParteProcesso,
    Processo,
    RepresentanteParte,
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
    list_display = [
        "nome_exibicao",
        "qualificacao",
        "posicao",
        "processo",
        "classificacao_pendente",
        "registro_legado",
    ]

    def get_readonly_fields(self, request, obj=None):
        campos = ["tipo_legado", "registro_legado", "classificacao_pendente"]
        if obj and obj.cliente_id:
            campos.extend(["nome", "cpf_cnpj"])
        return campos

    def save_model(self, request, obj, form, change):
        obj._usuario_alteracao = request.user
        super().save_model(request, obj, form, change)

    @staticmethod
    def _representa_cliente_atual(obj):
        return (
            obj is not None
            and obj.cliente_id is not None
            and obj.cliente_id == obj.processo.cliente_id
        )

    def has_delete_permission(self, request, obj=None):
        resolver_match = getattr(request, "resolver_match", None)
        exclusao_processo = (
            resolver_match is not None
            and resolver_match.url_name in {
                "processos_processo_delete",
                "processos_processo_changelist",
            }
        )
        if self._representa_cliente_atual(obj) and not exclusao_processo:
            return False
        return super().has_delete_permission(request, obj)

    def _delete_selected_preservando_cliente(self, request, queryset):
        if queryset.filter(
            cliente_id__isnull=False,
            cliente_id=F("processo__cliente_id"),
        ).exists():
            self.message_user(
                request,
                (
                    "A exclusão foi bloqueada: a seleção contém o participante "
                    "automático do Cliente atual de um Processo."
                ),
                level=messages.ERROR,
            )
            return None
        return delete_selected(self, request, queryset)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            _, nome, descricao = actions["delete_selected"]
            actions["delete_selected"] = (
                type(self)._delete_selected_preservando_cliente,
                nome,
                descricao,
            )
        return actions


@admin.register(AutoridadeProcessual)
class AutoridadeProcessualAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "vara_orgao", "processo"]


@admin.register(RepresentanteParte)
class RepresentanteParteAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "parte"]
    readonly_fields = ["fingerprint_externo"]


@admin.register(HistoricoClassificacaoParte)
class HistoricoClassificacaoParteAdmin(admin.ModelAdmin):
    list_display = [
        "parte",
        "qualificacao_anterior",
        "qualificacao_nova",
        "usuario",
        "alterado_em",
    ]
    readonly_fields = [
        "parte",
        "posicao_anterior",
        "qualificacao_anterior",
        "atuacao_mp_anterior",
        "posicao_nova",
        "qualificacao_nova",
        "atuacao_mp_nova",
        "usuario",
        "alterado_em",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
