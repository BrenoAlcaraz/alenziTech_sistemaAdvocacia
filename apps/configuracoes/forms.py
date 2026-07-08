from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator

from .models import ConfiguracaoEscritorio


class ConfiguracaoEscritorioForm(forms.ModelForm):
    site = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "google.com",
            }
        ),
    )

    class Meta:
        model = ConfiguracaoEscritorio
        fields = [
            "nome_escritorio",
            "nome_fantasia",
            "cnpj",
            "email",
            "telefone",
            "endereco",
            "site",
            "observacoes",
        ]
        widgets = {
            "nome_escritorio": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Nome do escritório",
                }
            ),
            "nome_fantasia": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Nome fantasia",
                }
            ),
            "cnpj": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "00.000.000/0000-00",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input",
                    "placeholder": "contato@escritorio.com",
                }
            ),
            "telefone": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "(00) 00000-0000",
                }
            ),
            "endereco": forms.Textarea(
                attrs={
                    "class": "input h-24 resize-none",
                    "placeholder": "Endereço completo do escritório",
                }
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "input h-24 resize-none",
                    "placeholder": "Observações internas",
                }
            ),
        }

    def clean_site(self):
        site = self.cleaned_data.get("site", "").strip()

        if not site:
            return ""

        if not site.startswith(("http://", "https://")):
            site = f"https://{site}"

        try:
            URLValidator()(site)
        except DjangoValidationError:
            raise forms.ValidationError("Insira um endereço de site válido.")

        return site
