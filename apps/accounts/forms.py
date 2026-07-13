from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User

from apps.accounts.decorators import GRUPOS_CRIACAO_USUARIO, nome_legivel_grupo

from .models import Departamento, MembroDepartamento, PerfilUsuario


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


class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = [
            "nome",
            "descricao",
            "departamento_pai",
            "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Nome do departamento",
                }
            ),
            "descricao": forms.Textarea(
                attrs={
                    "class": "input h-24 resize-none",
                    "placeholder": "Descrição opcional do departamento",
                }
            ),
            "departamento_pai": forms.Select(
                attrs={
                    "class": "input",
                }
            ),
            "ativo": forms.CheckboxInput(
                attrs={
                    "class": "rounded border-gray-300",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Departamento.objects.filter(ativo=True).order_by("nome")
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        self.fields["departamento_pai"].queryset = qs
        self.fields["departamento_pai"].empty_label = "Sem departamento pai"

    def clean_departamento_pai(self):
        departamento_pai = self.cleaned_data.get("departamento_pai")

        if not departamento_pai or not self.instance or not self.instance.pk:
            return departamento_pai

        if departamento_pai.pk == self.instance.pk:
            raise forms.ValidationError("Um departamento não pode ser pai dele mesmo.")

        atual = departamento_pai
        while atual:
            if atual.pk == self.instance.pk:
                raise forms.ValidationError(
                    "Um departamento não pode ser vinculado a um de seus próprios subdepartamentos."
                )
            atual = atual.departamento_pai

        return departamento_pai


class MembroDepartamentoForm(forms.ModelForm):
    class Meta:
        model = MembroDepartamento
        fields = [
            "usuario",
            "eh_gerente",
        ]
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

    def __init__(self, *args, departamento=None, **kwargs):
        super().__init__(*args, **kwargs)

        usuarios_ja_vinculados = MembroDepartamento.objects.none()
        if departamento and departamento.pk:
            usuarios_ja_vinculados = MembroDepartamento.objects.filter(
                departamento=departamento
            ).values_list("usuario_id", flat=True)

        self.fields["usuario"].queryset = (
            User.objects.filter(is_active=True)
            .exclude(id__in=usuarios_ja_vinculados)
            .order_by("username")
        )
        self.fields["usuario"].empty_label = "Selecione um usuário"


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
