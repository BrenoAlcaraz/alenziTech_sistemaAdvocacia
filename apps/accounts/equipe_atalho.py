"""
Equipe como atalho de seleção (PDR-0028): escolher uma equipe só marca
seus membros ativos como pessoas individuais — nenhum vínculo com a
equipe é gravado. Usado por Processos (integrantes), Tarefas
(participantes) e Agenda (participantes).
"""

from django import forms
from django.contrib.auth import get_user_model

from .models import Equipe

User = get_user_model()

SEM_EQUIPE = "Nenhuma equipe cadastrada ainda"


def equipes_ativas():
    return Equipe.objects.filter(ativo=True).order_by("nome")


def membros_ativos(equipe):
    """Usuários com `MembroEquipe.ativo=True` na equipe (e conta ativa)."""
    return User.objects.filter(
        is_active=True, membros_equipe__equipe=equipe, membros_equipe__ativo=True
    )


def _nome(usuario):
    return usuario.get_full_name() or usuario.username


def dados_para_js(usuarios_elegiveis, presentes=()):
    """Estrutura serializável (via `json_script`) que alimenta os botões
    de atalho e a lista de conferência: só os membros de cada equipe
    ativa que também são elegíveis no contexto (a lista nunca oferece
    quem o servidor rejeitaria). `presentes` = já selecionados no alvo."""
    elegiveis_ids = set(usuarios_elegiveis.values_list("pk", flat=True))
    equipes = {}
    for equipe in equipes_ativas():
        membros = [
            {"id": usuario.pk, "nome": _nome(usuario)}
            for usuario in membros_ativos(equipe).order_by("first_name", "username")
            if usuario.pk in elegiveis_ids
        ]
        equipes[str(equipe.pk)] = {"nome": equipe.nome, "membros": membros}
    return {"equipes": equipes, "presentes": sorted(presentes)}


class SelecionarMembrosEquipeForm(forms.Form):
    """Confirmação da lista de conferência: cada usuário recebido precisa
    ser elegível no contexto e membro ativo da equipe informada. Não
    confia no JS — a lista só sugere."""

    equipe = forms.ModelChoiceField(queryset=Equipe.objects.none())
    usuarios = forms.ModelMultipleChoiceField(queryset=User.objects.none(), required=False)

    def __init__(self, *args, usuarios_elegiveis, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipe"].queryset = equipes_ativas()
        self._usuarios_elegiveis = usuarios_elegiveis
        self.fields["usuarios"].queryset = usuarios_elegiveis

    def clean(self):
        cleaned = super().clean()
        equipe = cleaned.get("equipe")
        usuarios = cleaned.get("usuarios")
        if equipe and usuarios:
            ids_membros = set(membros_ativos(equipe).values_list("pk", flat=True))
            if any(usuario.pk not in ids_membros for usuario in usuarios):
                raise forms.ValidationError("Usuário não é membro ativo da equipe informada.")
        return cleaned
