from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    MovimentacaoProcessual,
    ParteProcesso,
    Processo,
)
from .services import cliente_do_processo_corresponde_documento, nome_exibicao_usuario
from apps.clientes.models import Cliente


User = get_user_model()


INSTANCIA_CHOICES = [
    ("1ª Instância", "1ª Instância"),
    ("2ª Instância", "2ª Instância"),
    ("STJ", "STJ"),
    ("STF", "STF"),
]


class ProcessoForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        required=True,
        widget=forms.Select(attrs={"class": "select"}),
        empty_label="Selecionar cliente...",
    )
    instancia = forms.ChoiceField(
        choices=INSTANCIA_CHOICES,
        initial="1ª Instância",
        widget=forms.Select(attrs={"class": "select"}),
    )

    class Meta:
        model = Processo
        fields = [
            "titulo", "numero", "cliente", "area_direito", "fase",
            "instancia", "vara_juizo", "valor_causa",
            "data_distribuicao", "gratuidade_justica_status", "prazo_proximo",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Construtora Horizonte vs. Município",
            }),
            "numero": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "0000000-00.0000.0.00.0000",
            }),
            "area_direito": forms.Select(attrs={"class": "select"}),
            "fase": forms.Select(attrs={"class": "select"}),
            "vara_juizo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: 11ª Vara Cível",
            }),
            "valor_causa": forms.NumberInput(attrs={
                "class": "input",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00",
            }),
            "data_distribuicao": forms.DateInput(attrs={
                "class": "input",
                "type": "date",
            }, format="%Y-%m-%d"),
            "gratuidade_justica_status": forms.Select(attrs={"class": "select"}),
            "prazo_proximo": forms.DateInput(attrs={
                "class": "input",
                "type": "date",
            }, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O schema do tenant delimita a consulta. A seleção de cliente de
        # Processo não depende da permissão nem do escopo do módulo Clientes.
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)


class ResponsavelProcessoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        nome = obj.get_full_name()
        return f"{nome} (@{obj.username})" if nome else f"@{obj.username}"


class ProcessoResponsavelForm(ProcessoForm):
    """Variante exclusiva do Administrador, com reatribuição explícita."""

    responsavel = ResponsavelProcessoChoiceField(
        queryset=User.objects.none(),
        required=True,
        label="Responsável",
        widget=forms.Select(attrs={"class": "select"}),
    )

    class Meta(ProcessoForm.Meta):
        fields = ProcessoForm.Meta.fields + ["responsavel"]

    def __init__(self, *args, responsaveis_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if responsaveis_queryset is not None:
            self.fields["responsavel"].queryset = responsaveis_queryset


class ProcessoApensoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.numero:
            return f"{obj.numero} — {obj.titulo}"
        return obj.titulo


class AdicionarApensoForm(forms.Form):
    processo_apenso = ProcessoApensoChoiceField(
        queryset=Processo.objects.none(),
        empty_label="Selecionar processo...",
        label="Processo",
        widget=forms.Select(attrs={"class": "select"}),
    )

    def __init__(self, *args, processo_origem, processos_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.processo_origem = processo_origem
        self.fields["processo_apenso"].queryset = processos_queryset

    def clean_processo_apenso(self):
        processo_apenso = self.cleaned_data["processo_apenso"]
        if processo_apenso.pk == self.processo_origem.pk:
            raise forms.ValidationError(
                "Um Processo não pode ser apenso a ele mesmo."
            )
        return processo_apenso


class ParteProcessoForm(forms.ModelForm):
    GRUPOS_PAPEL = [
        ("Polo Ativo", [
            ("autor", "Autor"),
            ("embargante", "Embargante"),
            ("recorrente", "Recorrente"),
        ]),
        ("Polo Passivo", [
            ("reu", "Réu"),
            ("embargado", "Embargado"),
            ("recorrido", "Recorrido"),
        ]),
        ("Outros", [
            ("terceiro_interessado", "Terceiro Interessado"),
            ("ministerio_publico", "Ministério Público"),
            ("amicus_curiae", "Amicus Curiae"),
            ("juiz", "Juiz"),
        ]),
    ]

    papel = forms.ChoiceField(
        choices=GRUPOS_PAPEL,
        widget=forms.Select(attrs={"class": "select"}),
        label="Papel processual",
    )

    class Meta:
        model = ParteProcesso
        fields = ["papel", "nome", "cpf_cnpj", "advogado_nome", "advogado_oab"]
        widgets = {
            "nome": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Nome completo ou razão social",
            }),
            "cpf_cnpj": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "CPF ou CNPJ (opcional)",
            }),
            "advogado_nome": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Nome do advogado (opcional)",
            }),
            "advogado_oab": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "OAB (opcional)",
            }),
        }

    def __init__(self, *args, processo=None, **kwargs):
        self._processo = processo
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self._processo is not None and not cleaned.get("advogado_nome"):
            cliente = cliente_do_processo_corresponde_documento(
                self._processo, cleaned.get("cpf_cnpj")
            )
            if cliente is not None:
                cleaned["advogado_nome"] = nome_exibicao_usuario(
                    self._processo.responsavel
                )
        return cleaned


class MovimentacaoProcessualForm(forms.ModelForm):
    data = forms.DateTimeField(
        initial=timezone.now,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "input", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = MovimentacaoProcessual
        fields = ["tipo", "data", "descricao"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "select"}),
            "descricao": forms.Textarea(attrs={
                "class": "input h-20 resize-none",
                "placeholder": "Descreva o andamento, decisão ou prazo...",
            }),
        }
