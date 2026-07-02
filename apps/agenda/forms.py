from django import forms
from django.contrib.auth.models import User
from .models import Compromisso
from apps.processos.models import Processo
from apps.clientes.models import Cliente


class CompromissoForm(forms.ModelForm):
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
    responsavel = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("first_name", "username"),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    data_hora_inicio = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "input", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    data_hora_fim = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "input", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = Compromisso
        fields = [
            "titulo", "descricao", "tipo", "dia_inteiro",
            "data_hora_inicio", "data_hora_fim", "local",
            "responsavel", "cliente", "processo",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Audiência de instrução – Construtora Horizonte",
            }),
            "descricao": forms.Textarea(attrs={
                "class": "input h-20 resize-none",
                "placeholder": "Detalhes adicionais...",
            }),
            "tipo": forms.Select(attrs={"class": "select"}),
            "dia_inteiro": forms.CheckboxInput(),
            "local": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Fórum Central, Sala 3",
            }),
        }
