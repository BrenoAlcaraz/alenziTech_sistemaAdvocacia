from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["tipo", "nome_razao_social", "cpf_cnpj", "email", "telefone", "endereco", "observacoes"]
        widgets = {
            "tipo": forms.HiddenInput(),
            "nome_razao_social": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Nome completo ou razão social",
            }),
            "cpf_cnpj": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "000.000.000-00",
            }),
            "email": forms.EmailInput(attrs={
                "class": "input",
                "placeholder": "email@exemplo.com",
            }),
            "telefone": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "(00) 00000-0000",
            }),
            "endereco": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Rua, número, bairro, cidade — UF",
            }),
            "observacoes": forms.Textarea(attrs={
                "class": "input h-20 resize-none",
                "placeholder": "Informações adicionais...",
            }),
        }
