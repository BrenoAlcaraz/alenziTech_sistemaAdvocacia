from django import forms
from .models import Processo
from apps.clientes.models import Cliente


INSTANCIA_CHOICES = [
    ("1ª Instância", "1ª Instância"),
    ("2ª Instância", "2ª Instância"),
    ("STJ", "STJ"),
    ("STF", "STF"),
]


class ProcessoForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        required=True,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Selecionar cliente...",
    )
    instancia = forms.ChoiceField(
        choices=INSTANCIA_CHOICES,
        initial="1ª Instância",
        widget=forms.Select(attrs={"class": "select"}),
    )

    class Meta:
        model = Processo
        fields = [
            "titulo", "numero", "cliente", "area_direito", "fase",
            "instancia", "vara_juizo", "valor_causa",
            "data_distribuicao", "gratuidade_justica_status", "prazo_proximo",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Construtora Horizonte vs. Município",
            }),
            "numero": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "0000000-00.0000.0.00.0000",
            }),
            "area_direito": forms.Select(attrs={"class": "select"}),
            "fase": forms.Select(attrs={"class": "select"}),
            "vara_juizo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: 11ª Vara Cível",
            }),
            "valor_causa": forms.NumberInput(attrs={
                "class": "input",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00",
            }),
            "data_distribuicao": forms.DateInput(attrs={
                "class": "input",
                "type": "date",
            }, format="%Y-%m-%d"),
            "gratuidade_justica_status": forms.Select(attrs={"class": "select"}),
            "prazo_proximo": forms.DateInput(attrs={
                "class": "input",
                "type": "date",
            }, format="%Y-%m-%d"),
        }
