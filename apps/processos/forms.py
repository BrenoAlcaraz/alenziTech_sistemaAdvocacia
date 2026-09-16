from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Documento,
    Intimacao,
    MovimentacaoProcessual,
    ParteProcesso,
    Processo,
)
from .services import (
    cliente_do_processo_corresponde_documento,
    nome_exibicao_usuario,
    rotulo_processo,
)
from apps.clientes.models import Cliente


User = get_user_model()


# Widget padrão de qualquer campo que selecione um Processo — o
# `data-processo-busca` liga o <select> à busca/combobox genérica em
# static/js/main.js (seção "Busca em campo de Processo"). Compartilhado
# entre apps (processos, financeiro, agenda, tarefas) para manter um
# único nome de atributo.
PROCESSO_SELECT_ATTRS = {"class": "select", "data-processo-busca": "1"}


INSTANCIA_CHOICES = [
    ("1ª Instância", "1ª Instância"),
    ("2ª Instância", "2ª Instância"),
    ("STJ", "STJ"),
    ("STF", "STF"),
]


class ProcessoForm(forms.ModelForm):
    clientes = forms.ModelMultipleChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        required=True,
        widget=forms.SelectMultiple(attrs={"class": "select", "size": "5"}),
        label="Cliente(s)",
    )
    instancia = forms.ChoiceField(
        choices=INSTANCIA_CHOICES,
        initial="1ª Instância",
        widget=forms.Select(attrs={"class": "select"}),
    )

    class Meta:
        model = Processo
        fields = [
            "titulo", "numero", "clientes", "area_direito", "fase",
            "instancia", "vara", "comarca", "estado", "cidade", "valor_causa",
            "data_distribuicao", "gratuidade_justica_status",
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
            "vara": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: 11ª Vara Cível",
            }),
            "comarca": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Comarca da Capital",
            }),
            "estado": forms.Select(attrs={"class": "select"}),
            "cidade": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Belo Horizonte",
            }),
            "valor_causa": forms.NumberInput(attrs={
                "class": "input",
                "step": "0.01",
                "min": "0",
                "placeholder": "0,00",
            }),
            "data_distribuicao": forms.DateInput(attrs={
                "class": "input",
                "type": "date",
            }, format="%Y-%m-%d"),
            "gratuidade_justica_status": forms.Select(attrs={"class": "select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O schema do tenant delimita a consulta. A seleção de cliente de
        # Processo não depende da permissão nem do escopo do módulo Clientes.
        self.fields["clientes"].queryset = Cliente.objects.filter(ativo=True)


class ResponsavelProcessoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        nome = obj.get_full_name()
        return f"{nome} (@{obj.username})" if nome else f"@{obj.username}"


class ProcessoResponsavelForm(ProcessoForm):
    """Variante com reatribuição explícita de responsável — Administrador
    ou usuário com a habilitação `processos_atribuir_responsavel`."""

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


class ProcessoChoiceField(forms.ModelChoiceField):
    """Padrão de label ("Título — Número") de qualquer seletor de
    Processo do sistema — usar em todo campo desse tipo."""

    def label_from_instance(self, obj):
        return rotulo_processo(obj)


class AdicionarIntegranteForm(forms.Form):
    usuario = ResponsavelProcessoChoiceField(
        queryset=User.objects.none(),
        label="Usuário",
        widget=forms.Select(attrs={"class": "select"}),
    )

    def __init__(self, *args, usuarios_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = usuarios_queryset


class AdicionarApensoForm(forms.Form):
    processo_apenso = ProcessoChoiceField(
        queryset=Processo.objects.none(),
        empty_label="Selecionar processo...",
        label="Processo",
        widget=forms.Select(attrs=PROCESSO_SELECT_ATTRS),
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
            ("exequente", "Exequente"),
            ("requerente", "Requerente"),
            ("reclamante", "Reclamante"),
            ("agravante", "Agravante"),
            ("impugnante", "Impugnante"),
            ("reconvinte", "Reconvinte"),
            ("excipiente", "Excipiente"),
            ("impetrante", "Impetrante"),
            ("inventariante", "Inventariante"),
        ]),
        ("Polo Passivo", [
            ("reu", "Réu"),
            ("embargado", "Embargado"),
            ("recorrido", "Recorrido"),
            ("executado", "Executado"),
            ("requerido", "Requerido"),
            ("reclamado", "Reclamado"),
            ("agravado", "Agravado"),
            ("impugnado", "Impugnado"),
            ("reconvindo", "Reconvindo"),
            ("excepto", "Excepto"),
            ("impetrado", "Impetrado"),
            ("inventariado", "Inventariado"),
        ]),
        ("Outros", [
            ("terceiro_interessado", "Terceiro Interessado"),
            ("ministerio_publico", "Ministério Público"),
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


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["arquivo", "tipo", "descricao"]
        widgets = {
            "arquivo": forms.ClearableFileInput(attrs={"class": "input"}),
            "tipo": forms.Select(attrs={"class": "select"}),
            "descricao": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Descrição (opcional)",
            }),
        }


class MovimentacaoOrigemPrazoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        data_local = timezone.localtime(obj.data)
        return f"{data_local:%d/%m/%Y} — {obj.get_tipo_display()}"


class MovimentacaoProcessualForm(forms.ModelForm):
    """Além do andamento em si, permite atualizar opcionalmente o
    'Resultado da sentença' do Processo — campo que saiu do formulário de
    criação/edição do processo e passou a ser definido a partir daqui
    (reunião de 13/09). 'Próximo prazo' do Processo não é mais definido
    aqui: passou a ser calculado automaticamente a partir de `data_prazo`
    dos andamentos (ver `services.recalcular_prazo_proximo`)."""

    data = forms.DateTimeField(
        initial=timezone.now,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "input", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    atualizar_resultado_sentenca = forms.ChoiceField(
        required=False,
        label="Atualizar resultado da sentença do processo",
        choices=[("", "Não alterar")] + Processo.RESULTADO_SENTENCA_CHOICES,
        widget=forms.Select(attrs={"class": "select"}),
    )

    class Meta:
        model = MovimentacaoProcessual
        fields = ["tipo", "data", "descricao", "data_prazo", "origem_prazo"]
        field_classes = {"origem_prazo": MovimentacaoOrigemPrazoChoiceField}
        widgets = {
            "tipo": forms.Select(attrs={"class": "select"}),
            "descricao": forms.Textarea(attrs={
                "class": "input h-20 resize-none",
                "placeholder": "Descreva o andamento, decisão ou prazo...",
            }),
            "data_prazo": forms.DateInput(attrs={"class": "input", "type": "date"}, format="%Y-%m-%d"),
            "origem_prazo": forms.Select(attrs={"class": "select"}),
        }

    def __init__(self, *args, processo, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].choices = MovimentacaoProcessual.catalogo_por_area(processo)
        self.fields["origem_prazo"].queryset = processo.movimentacoes.order_by("-data")
        self.fields["origem_prazo"].empty_label = "Nenhum (opcional)"


class IntimacaoForm(forms.ModelForm):
    class Meta:
        model = Intimacao
        fields = ["processo", "motivo", "prazo_manifestacao"]
        field_classes = {"processo": ProcessoChoiceField}
        widgets = {
            "processo": forms.Select(attrs=PROCESSO_SELECT_ATTRS),
            "motivo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Réplica à contestação",
            }),
            "prazo_manifestacao": forms.DateInput(attrs={
                "class": "input",
                "type": "date",
            }, format="%Y-%m-%d"),
        }

    def __init__(self, *args, processos_queryset, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["processo"].queryset = processos_queryset
        self.fields["processo"].empty_label = "Selecionar processo..."
