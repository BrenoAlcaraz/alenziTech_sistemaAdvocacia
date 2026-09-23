from django import forms
from django.contrib.auth.models import User
from django.urls import reverse
from .models import TIPOS_AFAZER, TIPOS_EVENTO, ItemAgenda
from apps.accounts.forms import UsuarioChoiceField
from apps.processos.forms import PROCESSO_SELECT_ATTRS, ProcessoChoiceField
from apps.processos.models import Processo
from apps.clientes.models import Cliente
from apps.accounts.codigo_interno import rotulo_usuario


def _usuarios_ativos():
    return User.objects.filter(is_active=True).order_by("first_name", "username")


class _LabelNomeUsernameMixin:
    def label_from_instance(self, obj):
        return rotulo_usuario(obj)


class ParticipanteChoiceField(_LabelNomeUsernameMixin, forms.ModelChoiceField):
    pass


class ParticipanteMultipleChoiceField(_LabelNomeUsernameMixin, forms.ModelMultipleChoiceField):
    pass


_CAMPOS_AFAZER = ["prioridade", "data_para_fazer", "hora_para_fazer", "data_fatal"]
_CAMPOS_EVENTO = ["dia_inteiro", "data_hora_inicio", "data_hora_fim", "local"]
# Prazo gerado pelo andamento: vínculo e data fatal vêm da origem.
_CAMPOS_TRAVADOS_NO_PRAZO_GERADO = ["tipo", "data_fatal", "processo", "cliente"]


class ItemAgendaForm(forms.ModelForm):
    # Valores do <select> de tipo que exibem cada grupo de campos.
    tipos_afazer_csv = ",".join(TIPOS_AFAZER)
    tipos_evento_csv = ",".join(TIPOS_EVENTO)

    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    processo = ProcessoChoiceField(
        queryset=Processo.objects.prefetch_related("clientes").exclude(status="arquivado"),
        required=False,
        widget=forms.Select(attrs=PROCESSO_SELECT_ATTRS),
        empty_label="Nenhum",
    )
    responsavel = forms.ModelChoiceField(
        queryset=_usuarios_ativos(),
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Nenhum",
    )
    participantes = ParticipanteMultipleChoiceField(
        queryset=_usuarios_ativos(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            "class": "rounded border-gray-300",
            "data-disponibilidade-participante": "1",
        }),
    )
    data_para_fazer = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "input", "type": "date"}, format="%Y-%m-%d"),
    )
    hora_para_fazer = forms.TimeField(
        required=False,
        input_formats=["%H:%M"],
        widget=forms.TimeInput(attrs={"class": "input", "type": "time"}, format="%H:%M"),
    )
    data_fatal = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"class": "input", "type": "date"}, format="%Y-%m-%d"),
    )
    data_hora_inicio = forms.DateTimeField(
        required=False,
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
        model = ItemAgenda
        fields = [
            "tipo", "titulo", "descricao",
            *_CAMPOS_AFAZER, *_CAMPOS_EVENTO,
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
            # Mostra só os campos da natureza do tipo (data-toggle-panel no template).
            "tipo": forms.Select(attrs={"class": "select", "data-toggle-select": "natureza"}),
            "prioridade": forms.Select(attrs={"class": "select"}),
            "dia_inteiro": forms.CheckboxInput(),
            "local": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Fórum Central, Sala 3",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cliente_id = self.data.get("cliente") or self.initial.get("cliente") or getattr(self.instance, "cliente_id", None)
        qs = Processo.objects.prefetch_related("clientes").exclude(status="arquivado")
        if cliente_id:
            qs = qs.filter(clientes__id=cliente_id)
        self.fields["processo"].queryset = qs
        self.fields["cliente"].widget.attrs["data-cliente-filtro"] = "1"
        self.fields["processo"].widget.attrs["data-processos-url"] = reverse("agenda:processos_por_cliente")
        self.fields["prioridade"].required = False
        if self.instance.gerado_pelo_processo:
            # `disabled` faz o Django ignorar o POST e manter o valor atual.
            for nome in _CAMPOS_TRAVADOS_NO_PRAZO_GERADO:
                self.fields[nome].disabled = True

    def clean(self):
        cleaned = super().clean()
        # Cada natureza guarda só os próprios campos.
        if cleaned.get("tipo") in TIPOS_EVENTO or not cleaned.get("prioridade"):
            cleaned["prioridade"] = "media"
        if cleaned.get("tipo") in TIPOS_EVENTO:
            cleaned.update(data_para_fazer=None, hora_para_fazer=None, data_fatal=None)
        else:
            cleaned.update(dia_inteiro=False, data_hora_inicio=None, data_hora_fim=None, local="")
            if cleaned.get("hora_para_fazer") and not cleaned.get("data_para_fazer"):
                self.add_error("hora_para_fazer", "Informe a data para fazer.")
        return cleaned


class AdicionarParticipanteForm(forms.Form):
    usuario = ParticipanteChoiceField(
        queryset=User.objects.none(),
        label="Usuário",
        widget=forms.Select(attrs={
            "class": "select",
            "data-disponibilidade-participante": "1",
        }),
    )

    def __init__(self, *args, usuarios_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = usuarios_queryset


class ReatribuirForm(forms.Form):
    destinatario = UsuarioChoiceField(
        queryset=_usuarios_ativos(),
        widget=forms.Select(attrs={"class": "select"}),
        label="Novo responsável",
    )
