from django import forms
from django.contrib.auth.models import User


class UsuarioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        nome = obj.get_full_name()
        return f"{nome} (@{obj.username})" if nome else f"@{obj.username}"


class NovaConversaIndividualForm(forms.Form):
    usuario = UsuarioChoiceField(
        queryset=User.objects.none(),
        label="Com quem você quer conversar?",
        widget=forms.Select(attrs={"class": "select"}),
    )

    def __init__(self, *args, usuarios_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = usuarios_queryset


class NovaConversaGrupoForm(forms.Form):
    titulo = forms.CharField(
        label="Título do grupo",
        max_length=255,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Ex: Equipe Trabalhista",
        }),
    )
    participantes = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label="Participantes",
        widget=forms.SelectMultiple(attrs={"class": "select", "size": "8"}),
    )

    def __init__(self, *args, usuarios_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participantes"].queryset = usuarios_queryset

    def clean_participantes(self):
        participantes = self.cleaned_data["participantes"]
        if participantes.count() < 2:
            raise forms.ValidationError(
                "Selecione ao menos 2 participantes além de você."
            )
        return participantes
