from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .codigo_interno import rotulo_usuario
from .permissoes_constants import CODIGO_PRESET_LIMITADO
from .models import Equipe, MembroEquipe, PapelAcesso, PerfilUsuario, UsuarioPapel


class UsuarioChoiceField(forms.ModelChoiceField):
    """Seletor de usuário com o rótulo padrão "U3 · Nome (@username)"."""

    def label_from_instance(self, obj):
        return rotulo_usuario(obj)


class UsuarioMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return rotulo_usuario(obj)


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
    papel = forms.ModelChoiceField(
        queryset=PapelAcesso.objects.none(),
        required=True,
        empty_label=None,
        widget=forms.Select(attrs={"class": "input"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "email",
            "nome_completo",
            "cargo",
            "papel",
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
        self.fields["papel"].queryset = PapelAcesso.objects.filter(ativo=True).order_by("nome")
        self.fields["papel"].initial = (
            PapelAcesso.objects.filter(codigo_preset=CODIGO_PRESET_LIMITADO)
            .values_list("pk", flat=True)
            .first()
        )
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

            UsuarioPapel.objects.get_or_create(
                usuario=user, papel=self.cleaned_data["papel"], defaults={"ativo": True}
            )

        return user


class EquipeForm(forms.ModelForm):
    class Meta:
        model = Equipe
        fields = [
            "nome",
            "descricao",
            "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Nome da equipe",
                }
            ),
            "descricao": forms.Textarea(
                attrs={
                    "class": "input h-24 resize-none",
                    "placeholder": "Descrição opcional da equipe",
                }
            ),
            "ativo": forms.CheckboxInput(
                attrs={
                    "class": "rounded border-gray-300",
                }
            ),
        }


class MembroEquipeForm(forms.ModelForm):
    class Meta:
        model = MembroEquipe
        fields = [
            "usuario",
            "eh_gerente",
        ]
        field_classes = {"usuario": UsuarioChoiceField}
        widgets = {
            "usuario": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
            "eh_gerente": forms.CheckboxInput(
                attrs={
                    "class": "rounded border-gray-300",
                }
            ),
        }

    def __init__(self, *args, equipe=None, **kwargs):
        super().__init__(*args, **kwargs)

        usuarios_ja_vinculados = MembroEquipe.objects.none()
        if equipe and equipe.pk:
            usuarios_ja_vinculados = MembroEquipe.objects.filter(
                equipe=equipe
            ).values_list("usuario_id", flat=True)

        self.fields["usuario"].queryset = (
            User.objects.filter(is_active=True)
            .exclude(id__in=usuarios_ja_vinculados)
            .order_by("username")
        )
        self.fields["usuario"].empty_label = "Selecione um usuário"


class PapelAcessoForm(forms.ModelForm):
    class Meta:
        model = PapelAcesso
        fields = [
            "nome",
            "descricao",
            "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Nome do papel",
                }
            ),
            "descricao": forms.Textarea(
                attrs={
                    "class": "input h-24 resize-none",
                    "placeholder": "Descrição opcional do papel",
                }
            ),
            "ativo": forms.CheckboxInput(
                attrs={
                    "class": "rounded border-gray-300",
                }
            ),
        }

    def clean_ativo(self):
        ativo = self.cleaned_data["ativo"]
        papel = self.instance
        if ativo or not papel.pk or not papel.ativo:
            return ativo
        if papel.eh_limitado:
            raise forms.ValidationError("O papel Limitado não pode ser desativado.")
        usuarios = UsuarioPapel.objects.filter(
            papel=papel, ativo=True, usuario__is_active=True
        ).count()
        if usuarios:
            quem = "o usuário" if usuarios == 1 else f"os {usuarios} usuários"
            raise forms.ValidationError(
                f"Reatribua {quem} deste papel antes de desativá-lo."
            )
        return ativo


class AtribuirPapelForm(forms.Form):
    usuario = UsuarioChoiceField(
        queryset=User.objects.none(),
        empty_label="Selecione um usuário",
        widget=forms.Select(attrs={"class": "input"}),
    )

    def __init__(self, *args, papel=None, **kwargs):
        super().__init__(*args, **kwargs)

        usuarios_ja_vinculados = UsuarioPapel.objects.none()
        if papel and papel.pk:
            usuarios_ja_vinculados = UsuarioPapel.objects.filter(
                papel=papel, ativo=True
            ).values_list("usuario_id", flat=True)

        self.fields["usuario"].queryset = (
            User.objects.filter(is_active=True)
            .exclude(id__in=usuarios_ja_vinculados)
            .order_by("username")
        )


class AlterarSenhaForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].widget.attrs.update(
            {"class": "input", "placeholder": "Senha atual"}
        )
        self.fields["new_password1"].widget.attrs.update(
            {"class": "input", "placeholder": "Nova senha"}
        )
        self.fields["new_password2"].widget.attrs.update(
            {"class": "input", "placeholder": "Confirme a nova senha"}
        )


class PerfilUsuarioForm(forms.ModelForm):
    class Meta:
        model = PerfilUsuario
        fields = [
            "nome_completo",
            "cargo",
            "avatar",
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
            "avatar": forms.ClearableFileInput(attrs={"class": "input"}),
        }
