from django import forms

from .models import PerfilUsuario


class PerfilUsuarioForm(forms.ModelForm):
    class Meta:
        model = PerfilUsuario
        fields = [
            "nome_completo",
            "cargo",
        ]
        widgets = {
            "nome_completo": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Seu nome completo",
                }
            ),
            "cargo": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Ex.: Advogado, Sócio, Administrativo",
                }
            ),
        }
