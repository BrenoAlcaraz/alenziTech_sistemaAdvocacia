from django import forms
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Tarefa
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
    processo = forms.ModelChoiceField(
        queryset=Processo.objects.select_related("cliente").exclude(status="arquivado"),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    destinatario = forms.ModelChoiceField(
        queryset=_usuarios_atribuiveis(),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Eu mesmo",
        label="Atribuir a",
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
        qs = Processo.objects.select_related("cliente").exclude(status="arquivado")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        self.fields["processo"].queryset = qs
        self.fields["cliente"].widget.attrs["data-cliente-filtro"] = "1"
        self.fields["processo"].widget.attrs["data-processos-url"] = reverse("tarefas:processos_por_cliente")


class ReatribuirForm(forms.Form):
    destinatario = forms.ModelChoiceField(
        queryset=_usuarios_atribuiveis(),
        widget=forms.Select(attrs={"class": "select"}),
        label="Novo responsável",
    )
