from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    AutoridadeProcessual,
    MovimentacaoProcessual,
    ParteProcesso,
    Processo,
    RepresentanteParte,
)
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


class ParteProcessoForm(forms.Form):
    TIPO_CHOICES = [
        ("POLO ATIVO", [
            ("autor", "Autor"),
            ("embargante", "Embargante"),
            ("recorrente", "Recorrente"),
        ]),
        ("POLO PASSIVO", [
            ("reu", "Réu"),
            ("embargado", "Embargado"),
            ("recorrido", "Recorrido"),
        ]),
        ("OUTROS", [
            ("terceiro_interessado", "Terceiro Interessado"),
            ("ministerio_publico", "Ministério Público"),
            ("amicus_curiae", "Amicus Curiae"),
            ("juiz", "Juiz"),
        ]),
    ]
    POSICAO_POR_TIPO = ParteProcesso.POSICAO_POR_QUALIFICACAO

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={"class": "select"}),
        label="Tipo de participante",
    )
    nome = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Nome completo ou razão social",
        }),
    )
    cpf_cnpj = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "CPF ou CNPJ (opcional)",
        }),
    )
    vinculo_escritorio = forms.ChoiceField(
        choices=[("", "Vínculo com o escritório...")]
        + ParteProcesso.VINCULO_CHOICES[1:3],
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        label="Vínculo com o escritório",
    )
    atuacao_ministerio_publico = forms.ChoiceField(
        choices=[("", "Forma de atuação do MP...")] + ParteProcesso.ATUACAO_MP_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        label="Atuação do Ministério Público",
    )
    vara_orgao = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Vara ou órgão (obrigatório para Juiz)",
        }),
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "input h-20 resize-none",
            "placeholder": "Observação da autoridade (opcional)",
        }),
    )

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        if tipo == "juiz":
            if not cleaned.get("vara_orgao"):
                self.add_error("vara_orgao", "Informe a vara ou órgão do juiz.")
        else:
            if not cleaned.get("vinculo_escritorio"):
                self.add_error(
                    "vinculo_escritorio",
                    "Informe o vínculo do participante com o escritório.",
                )
        if tipo == "ministerio_publico" and not cleaned.get(
            "atuacao_ministerio_publico"
        ):
            self.add_error(
                "atuacao_ministerio_publico",
                "Informe se o Ministério Público atua como parte ou fiscal.",
            )
        elif tipo != "ministerio_publico":
            cleaned["atuacao_ministerio_publico"] = ""
        return cleaned

    def criar_para_processo(self, processo, *, cliente=None, usuario=None):
        tipo = self.cleaned_data["tipo"]
        if tipo == "juiz":
            return AutoridadeProcessual.objects.create(
                processo=processo,
                tipo="juiz",
                nome=self.cleaned_data["nome"],
                vara_orgao=self.cleaned_data["vara_orgao"],
                observacao=self.cleaned_data["observacao"],
            )

        if cliente is not None:
            participante, _ = ParteProcesso.objects.get_or_create(
                processo=processo,
                cliente=cliente,
                defaults={
                    "nome": "",
                    "cpf_cnpj": "",
                    "vinculo_escritorio": "cliente",
                    "posicao": None,
                    "qualificacao": None,
                    "classificacao_pendente": True,
                },
            )
            participante.posicao = self.POSICAO_POR_TIPO[tipo]
            participante.qualificacao = tipo
            participante.atuacao_ministerio_publico = self.cleaned_data[
                "atuacao_ministerio_publico"
            ]
            participante.classificacao_pendente = False
            participante._usuario_alteracao = usuario
            participante.save(
                update_fields=[
                    "posicao",
                    "qualificacao",
                    "atuacao_ministerio_publico",
                    "classificacao_pendente",
                ]
            )
            return participante

        return ParteProcesso.objects.create(
            processo=processo,
            cliente=None,
            nome=self.cleaned_data["nome"],
            cpf_cnpj=self.cleaned_data["cpf_cnpj"],
            vinculo_escritorio=self.cleaned_data["vinculo_escritorio"],
            posicao=self.POSICAO_POR_TIPO[tipo],
            qualificacao=tipo,
            atuacao_ministerio_publico=self.cleaned_data[
                "atuacao_ministerio_publico"
            ],
        )


class ClassificacaoParteForm(forms.Form):
    tipo = forms.ChoiceField(
        choices=ParteProcessoForm.TIPO_CHOICES[:-1]
        + [("OUTROS", ParteProcessoForm.TIPO_CHOICES[-1][1][:-1])],
        widget=forms.Select(attrs={"class": "select"}),
        label="Classificação processual",
    )
    atuacao_ministerio_publico = forms.ChoiceField(
        choices=[("", "Forma de atuação do MP...")]
        + ParteProcesso.ATUACAO_MP_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
    )

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        if tipo == "ministerio_publico":
            if not cleaned.get("atuacao_ministerio_publico"):
                self.add_error(
                    "atuacao_ministerio_publico",
                    "Informe se o Ministério Público atua como parte ou fiscal.",
                )
        else:
            cleaned["atuacao_ministerio_publico"] = ""
        return cleaned

    def salvar(self, parte, *, usuario):
        parte.posicao = ParteProcesso.POSICAO_POR_QUALIFICACAO[
            self.cleaned_data["tipo"]
        ]
        parte.qualificacao = self.cleaned_data["tipo"]
        parte.atuacao_ministerio_publico = self.cleaned_data[
            "atuacao_ministerio_publico"
        ]
        parte.classificacao_pendente = False
        parte._usuario_alteracao = usuario
        parte.save(
            update_fields=[
                "posicao",
                "qualificacao",
                "atuacao_ministerio_publico",
                "classificacao_pendente",
            ]
        )
        return parte


class RepresentanteParteForm(forms.ModelForm):
    class Meta:
        model = RepresentanteParte
        fields = [
            "tipo",
            "usuario",
            "nome_externo",
            "oab",
            "uf_oab",
            "telefone",
            "email",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "select"}),
            "usuario": forms.Select(attrs={"class": "select"}),
            "nome_externo": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Nome do advogado externo",
            }),
            "oab": forms.TextInput(attrs={"class": "input", "placeholder": "OAB"}),
            "uf_oab": forms.TextInput(attrs={
                "class": "input uppercase",
                "maxlength": "2",
                "placeholder": "UF",
            }),
            "telefone": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Telefone",
            }),
            "email": forms.EmailInput(attrs={"class": "input", "placeholder": "E-mail"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = User.objects.filter(is_active=True).order_by(
            "first_name", "last_name", "username"
        )
        self.fields["usuario"].required = False
        self.fields["usuario"].empty_label = "Selecionar usuário do escritório..."

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        if tipo == "interno":
            if not cleaned.get("usuario"):
                self.add_error("usuario", "Selecione o usuário interno.")
            if any(
                cleaned.get(campo)
                for campo in ("nome_externo", "oab", "uf_oab", "telefone", "email")
            ):
                self.add_error(
                    "tipo",
                    "Advogado interno não pode possuir dados de advogado externo.",
                )
        elif tipo == "externo":
            cleaned["usuario"] = None
            for campo, mensagem in (
                ("nome_externo", "Informe o nome do advogado externo."),
                ("oab", "Informe o número da OAB."),
                ("uf_oab", "Informe a UF da OAB."),
            ):
                if not cleaned.get(campo):
                    self.add_error(campo, mensagem)
            if cleaned.get("uf_oab"):
                cleaned["uf_oab"] = cleaned["uf_oab"].upper()
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
