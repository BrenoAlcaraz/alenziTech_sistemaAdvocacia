from django import forms
from django.contrib.auth import get_user_model

from .models import Cliente, Documento
from .validators import cnpj_valido, cpf_valido, telefone_valido

User = get_user_model()


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo", "nome_razao_social", "nome_fantasia", "cpf_cnpj", "email", "telefone",
            "estrangeiro", "nacionalidade", "estado_civil", "profissao", "rg",
            "data_nascimento",
            "representante_nome", "representante_cpf", "representante_cargo",
            "representante_telefone", "representante_email",
            "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "estado",
            "observacoes",
        ]
        widgets = {
            "tipo": forms.HiddenInput(),
            "nome_razao_social": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Nome completo",
            }),
            "nome_fantasia": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Nome fantasia (opcional)",
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
                "placeholder": "Número do RG",
            }),
            "data_nascimento": forms.DateInput(attrs={"class": "input", "type": "date"}),
            "representante_nome": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Nome completo do representante",
            }),
            "representante_cpf": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "000.000.000-00",
            }),
            "representante_cargo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Sócio-administrador, Procurador",
            }),
            "representante_telefone": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "(00) 00000-0000",
            }),
            "representante_email": forms.EmailInput(attrs={
                "class": "input",
                "placeholder": "email@exemplo.com",
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

    def clean_nome_razao_social(self):
        # Nome sempre em maiúsculas: evita o mesmo cliente/parte aparecer
        # com grafias diferentes conforme quem digitou.
        return (self.cleaned_data.get("nome_razao_social") or "").strip().upper()

    def clean_cidade(self):
        return (self.cleaned_data.get("cidade") or "").strip().upper()

    def clean_bairro(self):
        return (self.cleaned_data.get("bairro") or "").strip().upper()

    def clean_nome_fantasia(self):
        return (self.cleaned_data.get("nome_fantasia") or "").strip().upper()

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo") or "PF"
        documento = (cleaned.get("cpf_cnpj") or "").strip()

        if tipo == "PJ":
            # Estado civil, profissão, RG e nacionalidade só fazem sentido
            # para o próprio cliente Pessoa Física — trava/limpa mesmo que
            # alguém manipule a requisição manualmente (os campos vêm
            # ocultos na tela para PJ). `estrangeiro` vale para PJ como
            # "empresa estrangeira": documento livre, sem validar CNPJ.
            cleaned["nacionalidade"] = "Brasileira"
            cleaned["estado_civil"] = ""
            cleaned["profissao"] = ""
            cleaned["rg"] = ""
            cleaned["data_nascimento"] = None

            if documento and not cleaned.get("estrangeiro") and not cnpj_valido(documento):
                self.add_error("cpf_cnpj", "CNPJ inválido.")

            representante_cpf = (cleaned.get("representante_cpf") or "").strip()
            if representante_cpf and not cpf_valido(representante_cpf):
                self.add_error("representante_cpf", "CPF inválido.")
        else:
            # Representante e nome fantasia são exclusivos de Pessoa
            # Jurídica — trava/limpa pelo mesmo motivo acima.
            cleaned["nome_fantasia"] = ""
            cleaned["representante_nome"] = ""
            cleaned["representante_cpf"] = ""
            cleaned["representante_cargo"] = ""
            cleaned["representante_telefone"] = ""
            cleaned["representante_email"] = ""

            if cleaned.get("estrangeiro"):
                # RG é exclusivo de brasileiro — trava/limpa mesmo que
                # alguém manipule a requisição manualmente (o campo vem
                # desabilitado na tela).
                cleaned["rg"] = ""
            else:
                cleaned["nacionalidade"] = "Brasileira"
                if documento and not cpf_valido(documento):
                    self.add_error("cpf_cnpj", "CPF inválido.")

        for campo in ("telefone", "representante_telefone"):
            valor = (cleaned.get(campo) or "").strip()
            if valor and not telefone_valido(valor):
                self.add_error(campo, "Telefone inválido — informe DDD + número.")

        return cleaned


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["arquivo", "tipo", "descricao"]
        widgets = {
            "arquivo": forms.ClearableFileInput(attrs={"class": "input"}),
            "tipo": forms.Select(attrs={"class": "select"}),
            "descricao": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Descrição (opcional)",
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
