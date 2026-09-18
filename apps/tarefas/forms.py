from django import forms
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Tarefa
from apps.accounts.models import Equipe
from apps.processos.forms import PROCESSO_SELECT_ATTRS, ProcessoChoiceField
from apps.processos.models import Processo
from apps.clientes.models import Cliente


def _usuarios_atribuiveis():
    return User.objects.filter(is_active=True).order_by("first_name", "username")


class TarefaForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    processo = ProcessoChoiceField(
        queryset=Processo.objects.prefetch_related("clientes").exclude(status="arquivado"),
        required=False,
        widget=forms.Select(attrs=PROCESSO_SELECT_ATTRS),
        empty_label="Nenhum",
    )
    atribuidos = forms.ModelMultipleChoiceField(
        queryset=_usuarios_atribuiveis(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "select", "size": "6", "id": "id_atribuidos"}),
        label="Atribuir a",
    )
    # Nome do campo preservado (`destinatario`, não `responsavel`) para
    # não quebrar contrato/testes já existentes do fluxo de atribuição
    # simples de hoje — só o rótulo muda, para refletir que agora é a
    # escolha do responsável dentro do grupo de `atribuidos`.
    destinatario = forms.ModelChoiceField(
        queryset=_usuarios_atribuiveis(),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Eu mesmo",
        label="Responsável",
    )
    prazo = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            attrs={"class": "input", "type": "date"},
            format="%Y-%m-%d",
        ),
    )

    class Meta:
        model = Tarefa
        fields = ["titulo", "descricao", "prioridade", "prazo", "cliente", "processo"]
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Descreva a tarefa...",
            }),
            "descricao": forms.Textarea(attrs={
                "class": "input h-20 resize-none",
                "placeholder": "Detalhes adicionais...",
            }),
            "prioridade": forms.Select(attrs={"class": "select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cliente_id = self.data.get("cliente") or self.initial.get("cliente") or getattr(self.instance, "cliente_id", None)
        qs = Processo.objects.prefetch_related("clientes").exclude(status="arquivado")
        if cliente_id:
            qs = qs.filter(clientes__id=cliente_id)
        self.fields["processo"].queryset = qs
        self.fields["cliente"].widget.attrs["data-cliente-filtro"] = "1"
        self.fields["processo"].widget.attrs["data-processos-url"] = reverse("tarefas:processos_por_cliente")

    def clean(self):
        cleaned = super().clean()
        atribuidos = list(cleaned.get("atribuidos") or [])
        destinatario = cleaned.get("destinatario")

        if not destinatario and len(atribuidos) == 1:
            # Um só atribuído: é o responsável, sem precisar escolher de
            # novo (mesmo comportamento de sempre de "Atribuir a").
            destinatario = atribuidos[0]
            cleaned["destinatario"] = destinatario

        if destinatario and atribuidos and destinatario not in atribuidos:
            self.add_error("destinatario", "O responsável precisa estar entre os atribuídos.")
        elif len(atribuidos) > 1 and not destinatario:
            self.add_error("destinatario", "Escolha quem é o responsável entre os atribuídos.")

        return cleaned


class ReatribuirForm(forms.Form):
    destinatario = forms.ModelChoiceField(
        queryset=_usuarios_atribuiveis(),
        widget=forms.Select(attrs={"class": "select"}),
        label="Novo responsável",
    )


class AdicionarParticipanteTarefaForm(forms.Form):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Usuário",
        widget=forms.Select(attrs={"class": "select"}),
    )

    def __init__(self, *args, usuarios_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = usuarios_queryset


class AdicionarEquipeParticipanteTarefaForm(forms.Form):
    """Vínculo dinâmico de Equipe inteira como participante da tarefa
    (specs/grupo-integrante-participante-dinamico.md)."""

    equipe = forms.ModelChoiceField(
        queryset=Equipe.objects.none(),
        label="Equipe",
        widget=forms.Select(attrs={"class": "select"}),
    )

    def __init__(self, *args, equipes_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipe"].queryset = equipes_queryset
