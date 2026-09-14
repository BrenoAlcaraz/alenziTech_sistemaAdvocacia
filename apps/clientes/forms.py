from django import forms
from django.contrib.auth import get_user_model

from .models import Cliente
from .validators import cnpj_valido, cpf_valido, telefone_valido

User = get_user_model()


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo", "nome_razao_social", "cpf_cnpj", "email", "telefone",
            "estrangeiro", "nacionalidade", "estado_civil", "profissao", "rg",
            "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "estado",
            "observacoes",
        ]
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
            "estrangeiro": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "nacionalidade": forms.Select(attrs={"class": "select"}),
            "estado_civil": forms.Select(attrs={"class": "select"}),
            "profissao": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Profissão (opcional)",
            }),
            "rg": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "00.000.000-0",
            }),
            "cep": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "00000-000",
            }),
            "logradouro": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Rua, avenida...",
            }),
            "numero": forms.TextInput(attrs={"class": "input", "placeholder": "Número"}),
            "complemento": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Complemento (opcional)",
            }),
            "bairro": forms.TextInput(attrs={"class": "input", "placeholder": "Bairro"}),
            "cidade": forms.TextInput(attrs={"class": "input", "placeholder": "Cidade"}),
            "estado": forms.Select(attrs={"class": "select"}),
            "observacoes": forms.Textarea(attrs={
                "class": "input h-20 resize-none",
                "placeholder": "Informações adicionais...",
            }),
        }

    def clean(self):
        cleaned = super().clean()
        estrangeiro = cleaned.get("estrangeiro")

        if estrangeiro:
            # RG é exclusivo de brasileiro — trava/limpa mesmo que alguém
            # manipule a requisição manualmente (o campo vem desabilitado
            # na tela).
            cleaned["rg"] = ""
        else:
            cleaned["nacionalidade"] = "Brasileira"
            documento = (cleaned.get("cpf_cnpj") or "").strip()
            if documento:
                tipo = cleaned.get("tipo") or "PF"
                if tipo == "PJ":
                    if not cnpj_valido(documento):
                        self.add_error("cpf_cnpj", "CNPJ inválido.")
                elif not cpf_valido(documento):
                    self.add_error("cpf_cnpj", "CPF inválido.")

        telefone = (cleaned.get("telefone") or "").strip()
        if telefone and not telefone_valido(telefone):
            self.add_error("telefone", "Telefone inválido — informe DDD + número.")

        return cleaned


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
