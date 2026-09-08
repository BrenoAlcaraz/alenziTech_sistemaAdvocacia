from django import forms
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Compromisso
from apps.processos.models import Processo
from apps.clientes.models import Cliente


class _LabelNomeUsernameMixin:
    def label_from_instance(self, obj):
        nome = obj.get_full_name()
        return f"{nome} (@{obj.username})" if nome else f"@{obj.username}"


class ParticipanteChoiceField(_LabelNomeUsernameMixin, forms.ModelChoiceField):
    pass


class ParticipanteMultipleChoiceField(_LabelNomeUsernameMixin, forms.ModelMultipleChoiceField):
    pass


class CompromissoForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    processo = forms.ModelChoiceField(
        queryset=Processo.objects.select_related("cliente").exclude(status="arquivado"),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    responsavel = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("first_name", "username"),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    participantes = ParticipanteMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("first_name", "username"),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "rounded border-gray-300"}),
    )
    data_hora_inicio = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "input", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    data_hora_fim = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "input", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = Compromisso
        fields = [
            "titulo", "descricao", "tipo", "dia_inteiro",
            "data_hora_inicio", "data_hora_fim", "local",
            "responsavel", "cliente", "processo",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Audiência de instrução – Construtora Horizonte",
            }),
            "descricao": forms.Textarea(attrs={
                "class": "input h-20 resize-none",
                "placeholder": "Detalhes adicionais...",
            }),
            "tipo": forms.Select(attrs={"class": "select"}),
            "dia_inteiro": forms.CheckboxInput(),
            "local": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Fórum Central, Sala 3",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cliente_id = self.data.get("cliente") or self.initial.get("cliente") or getattr(self.instance, "cliente_id", None)
        qs = Processo.objects.select_related("cliente").exclude(status="arquivado")
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        self.fields["processo"].queryset = qs
        self.fields["cliente"].widget.attrs["data-cliente-filtro"] = "1"
        self.fields["processo"].widget.attrs["data-processos-url"] = reverse("agenda:processos_por_cliente")


class AdicionarParticipanteForm(forms.Form):
    usuario = ParticipanteChoiceField(
        queryset=User.objects.none(),
        label="Usuário",
        widget=forms.Select(attrs={"class": "select"}),
    )

    def __init__(self, *args, usuarios_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = usuarios_queryset
