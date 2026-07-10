from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User

from apps.accounts.decorators import GRUPOS_CRIACAO_USUARIO, nome_legivel_grupo

from .models import PerfilUsuario


class GrupoPapelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return nome_legivel_grupo(obj.name)


class CriarUsuarioEscritorioForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "placeholder": "usuario@escritorio.com",
            }
        ),
    )
    nome_completo = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Nome completo",
            }
        ),
    )
    cargo = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "Ex.: Advogado, Financeiro, Gerente",
            }
        ),
    )
    grupo = GrupoPapelChoiceField(
        queryset=Group.objects.none(),
        required=True,
        empty_label="Selecione um papel",
        widget=forms.Select(attrs={"class": "input"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "email",
            "nome_completo",
            "cargo",
            "grupo",
            "password1",
            "password2",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "nome.sobrenome",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupo"].queryset = Group.objects.filter(
            name__in=GRUPOS_CRIACAO_USUARIO
        ).order_by("name")
        self.fields["password1"].widget.attrs.update(
            {"class": "input", "placeholder": "Senha inicial"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "input", "placeholder": "Confirme a senha"}
        )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe um usuário com este e-mail.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()

            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            perfil.nome_completo = self.cleaned_data.get("nome_completo", "")
            perfil.cargo = self.cleaned_data.get("cargo", "")
            perfil.save(update_fields=["nome_completo", "cargo"])

            grupo = self.cleaned_data["grupo"]
            user.groups.clear()
            user.groups.add(grupo)

        return user


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
