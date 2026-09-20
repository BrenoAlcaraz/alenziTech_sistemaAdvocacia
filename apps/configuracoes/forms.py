from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator

from apps.saas_tenants.cores import hex_valido

from .models import ConfiguracaoEscritorio

TAMANHO_MAXIMO_LOGO_BYTES = 2 * 1024 * 1024


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


class IdentidadeVisualForm(forms.Form):
    """Logo do escritório e cores do sistema. Ao enviar um logo novo, as
    cores predominantes dele viram as cores do sistema (a não ser que se
    peça para manter as atuais); as cores também podem ser ajustadas."""

    logo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "input", "accept": "image/*"}),
    )
    remover_logo = forms.BooleanField(required=False)
    manter_cores = forms.BooleanField(required=False)
    cor_primaria = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"type": "color", "class": "h-10 w-16"}),
    )
    cor_secundaria = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"type": "color", "class": "h-10 w-16"}),
    )

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and logo.size > TAMANHO_MAXIMO_LOGO_BYTES:
            raise forms.ValidationError("O logo deve ter no máximo 2 MB.")
        return logo

    def _clean_cor(self, nome):
        cor = (self.cleaned_data.get(nome) or "").strip()
        if cor and not hex_valido(cor):
            raise forms.ValidationError("Informe uma cor válida (ex.: #1a1a1a).")
        return cor

    def clean_cor_primaria(self):
        return self._clean_cor("cor_primaria")

    def clean_cor_secundaria(self):
        return self._clean_cor("cor_secundaria")
