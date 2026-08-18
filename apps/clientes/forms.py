from django import forms
from django.contrib.auth import get_user_model

from .models import Cliente

User = get_user_model()


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


class ResponsavelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        nome = obj.get_full_name()
        return f"{nome} (@{obj.username})" if nome else f"@{obj.username}"


class ClienteResponsavelForm(ClienteForm):
    """
    Variante de ClienteForm usada apenas pelo Administrador do escritório,
    que também expõe e permite reatribuir o responsável do cliente.
    """

    responsavel = ResponsavelChoiceField(
        queryset=User.objects.none(),
        required=True,
        label="Responsável",
        widget=forms.Select(attrs={"class": "select", "id": "id_responsavel"}),
    )

    class Meta(ClienteForm.Meta):
        fields = ClienteForm.Meta.fields + ["responsavel"]

    def __init__(self, *args, usuarios_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuarios_queryset is not None:
            self.fields["responsavel"].queryset = usuarios_queryset
