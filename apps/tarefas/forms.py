from django import forms
from .models import Tarefa
from apps.processos.models import Processo
from apps.clientes.models import Cliente


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
