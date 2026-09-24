from decimal import Decimal

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from .models import CustaJudicial, GrupoCustas, Honorario, LancamentoFinanceiro, SolicitacaoFinanceira
from .services import calcular_honorario_sucumbencial, contratos_de_exito_pelo_ganho
from apps.clientes.models import Cliente
from apps.processos.forms import PROCESSO_SELECT_ATTRS, ProcessoChoiceField
from apps.processos.models import Processo
from apps.processos.services import processos_do_cliente


def _cliente_id_atual(form):
    """Cliente já conhecido no form (reenvio, edição ou pré-seleção) para
    filtrar o queryset de Processo antes de qualquer interação via JS."""
    return form.data.get("cliente") or form.initial.get("cliente") or getattr(form.instance, "cliente_id", None)


def _filtrar_processo_por_cliente(form, url_name):
    """Restringe o campo Processo ao cliente já conhecido e prepara os
    atributos consumidos pelo filtro dinâmico em static/js/main.js."""
    cliente_id = _cliente_id_atual(form)
    qs = Processo.objects.prefetch_related("clientes").exclude(status="arquivado")
    if cliente_id:
        qs = qs.filter(clientes__id=cliente_id)
    form.fields["processo"].queryset = qs
    form.fields["cliente"].widget.attrs["data-cliente-filtro"] = "1"
    form.fields["processo"].widget.attrs["data-processos-url"] = reverse(url_name)


class LancamentoFinanceiroForm(forms.ModelForm):
    class Meta:
        model = LancamentoFinanceiro
        field_classes = {"processo": ProcessoChoiceField}
        fields = [
            "tipo",
            "descricao",
            "valor",
            "data_vencimento",
            "data_pagamento",
            "categoria",
            "status",
            "forma_pagamento",
            "cliente",
            "processo",
            "responsavel",
            "observacoes",
            "classificacao",
            "periodicidade",
            "numero_parcelas",
            "duracao_tipo",
            "duracao_quantidade",
            "duracao_data_final",
            "anexo",
            "comprovante_pagamento",
        ]
        widgets = {
            "tipo":            forms.Select(attrs={"class": "select"}),
            "descricao":       forms.TextInput(attrs={"class": "input"}),
            "valor":           forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "data_vencimento": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "data_pagamento":  forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "categoria":       forms.Select(attrs={"class": "select"}),
            "status":          forms.Select(attrs={"class": "select", "data-toggle-select": "status"}),
            "forma_pagamento": forms.Select(attrs={"class": "select"}),
            "cliente":         forms.Select(attrs={"class": "select"}),
            "processo":        forms.Select(attrs=PROCESSO_SELECT_ATTRS),
            "responsavel":     forms.Select(attrs={"class": "select"}),
            "observacoes":     forms.Textarea(attrs={"class": "input h-20 resize-none", "rows": 3}),
            "classificacao":   forms.Select(attrs={"class": "select", "data-toggle-select": "classificacao"}),
            "periodicidade":   forms.Select(attrs={"class": "select"}),
            "numero_parcelas": forms.NumberInput(attrs={"class": "input", "min": "2"}),
            "duracao_tipo":    forms.Select(attrs={"class": "select", "data-toggle-select": "duracao_tipo"}),
            "duracao_quantidade": forms.NumberInput(attrs={"class": "input", "min": "1"}),
            "duracao_data_final": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "anexo": forms.ClearableFileInput(attrs={"class": "input"}),
            "comprovante_pagamento": forms.ClearableFileInput(attrs={"class": "input"}),
        }
        labels = {
            "classificacao": "Classificação",
            "numero_parcelas": "Quantidade de parcelas",
            "duracao_tipo": "Duração da recorrência",
            "duracao_quantidade": "Quantidade de ocorrências",
            "duracao_data_final": "Data final",
            "anexo": "Boleto/documento da despesa",
            "comprovante_pagamento": "Comprovante de pagamento",
        }

    def __init__(self, *args, pode_receber_honorario=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.pode_receber_honorario = pode_receber_honorario

        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["cliente"].required = False
        self.fields["cliente"].empty_label = "Nenhum"

        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
        _filtrar_processo_por_cliente(self, "financeiro:processos_por_cliente")

        self.fields["responsavel"].queryset = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.fields["responsavel"].required = False
        self.fields["responsavel"].empty_label = "Nenhum"

        if self.instance.status == "cancelado":
            self.fields["status"].disabled = True
        else:
            self.fields["status"].choices = [
                (valor, rotulo) for valor, rotulo in LancamentoFinanceiro.STATUS_CHOICES if valor != "cancelado"
            ]

        self.fields["data_vencimento"].input_formats = ["%Y-%m-%d"]
        self.fields["data_pagamento"].required = False
        self.fields["data_pagamento"].input_formats = ["%Y-%m-%d"]

        self.fields["forma_pagamento"].required = False
        self.fields["observacoes"].required = False

        self.fields["classificacao"].required = False
        self.fields["periodicidade"].required = False
        self.fields["numero_parcelas"].required = False
        self.fields["duracao_tipo"].required = False
        self.fields["duracao_quantidade"].required = False
        self.fields["duracao_data_final"].required = False
        self.fields["duracao_data_final"].input_formats = ["%Y-%m-%d"]
        self.fields["anexo"].required = False
        self.fields["comprovante_pagamento"].required = False

        rotulos = dict(LancamentoFinanceiro.CATEGORIA_CHOICES)
        self.categorias_por_tipo = {
            tipo: [[valor, rotulos[valor]] for valor in self._categorias_aceitas(tipo)]
            for tipo in LancamentoFinanceiro.CATEGORIAS_POR_TIPO
        }

    def _categorias_aceitas(self, tipo):
        """Categorias manuais do tipo, mais a categoria atual de um
        lançamento existente (gerada pelo sistema ou anterior à revisão de
        2026-09-20) — para editá-lo sem forçar a troca de categoria."""
        categorias = LancamentoFinanceiro.CATEGORIAS_POR_TIPO.get(tipo, ())
        instancia = self.instance
        if instancia.pk and instancia.tipo == tipo and instancia.categoria not in categorias:
            return (*categorias, instancia.categoria)
        return categorias

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        data_pagamento = cleaned_data.get("data_pagamento")

        tipo = cleaned_data.get("tipo")
        categoria = cleaned_data.get("categoria")
        if tipo and categoria and categoria not in self._categorias_aceitas(tipo):
            self.add_error("categoria", "Esta categoria não pertence ao tipo escolhido.")
        elif tipo == "receita" and categoria == "reembolso" and not cleaned_data.get("cliente"):
            # Reembolso de cliente é creditado nas custas judiciais dele.
            self.add_error("cliente", "Informe o cliente que está reembolsando.")

        if status == "pago" and not data_pagamento:
            self.add_error("data_pagamento", "Informe a data de pagamento para lançamentos pagos.")
        elif status != "pago":
            # Data de pagamento e comprovante de pagamento só existem para
            # lançamento pago; o boleto/documento da despesa (`anexo`) vale
            # independentemente do status.
            cleaned_data["data_pagamento"] = None
            if self.files.get("comprovante_pagamento"):
                self.add_error(
                    "comprovante_pagamento", "O comprovante de pagamento só pode ser anexado em lançamento pago."
                )

        self._validar_recebimento_de_honorario(cleaned_data)

        classificacao = cleaned_data.get("classificacao") or "unica"
        cleaned_data["classificacao"] = classificacao
        eh_ocorrencia_gerada = bool(self.instance.lancamento_origem_id)
        if eh_ocorrencia_gerada:
            # Ocorrência já gerada por uma recorrência/parcelamento:
            # classificacao/periodicidade são só informativas aqui, não
            # exigem parcelas/duração de novo (isso vive na origem).
            return cleaned_data

        if classificacao == "parcelado":
            numero_parcelas = cleaned_data.get("numero_parcelas")
            if not numero_parcelas or numero_parcelas < 2:
                self.add_error("numero_parcelas", "Informe ao menos 2 parcelas.")
        elif classificacao == "recorrente":
            periodicidade = cleaned_data.get("periodicidade")
            if periodicidade not in dict(self.instance.PERIODICIDADE_CHOICES):
                self.add_error("periodicidade", "Selecione mensal ou anual.")
            duracao_tipo = cleaned_data.get("duracao_tipo")
            if duracao_tipo == "quantidade" and not cleaned_data.get("duracao_quantidade"):
                self.add_error("duracao_quantidade", "Informe a quantidade de ocorrências.")
            elif duracao_tipo == "data_final":
                data_final = cleaned_data.get("duracao_data_final")
                data_venc = cleaned_data.get("data_vencimento")
                if not data_final:
                    self.add_error("duracao_data_final", "Informe a data final.")
                elif data_venc and data_final <= data_venc:
                    self.add_error("duracao_data_final", "A data final deve ser depois do primeiro vencimento.")
            elif duracao_tipo not in dict(self.instance.DURACAO_TIPO_CHOICES):
                self.add_error("duracao_tipo", "Selecione a duração da recorrência.")

        return cleaned_data

    def _validar_recebimento_de_honorario(self, cleaned_data):
        """PDR-0035. `self.instance` ainda tem os valores gravados aqui:
        o ModelForm só copia o cleaned_data para ela depois do clean()."""
        instancia = self.instance
        if not instancia.pk or not instancia.honorario_id:
            return
        if instancia.eh_recebimento_de_honorario_unico:
            # Desfazer/corrigir esse recebimento deixaria o `valor_recebido`
            # do honorário errado — só pela confirmação do honorário.
            campos = ("status", "valor", "data_pagamento")
            if any(cleaned_data.get(campo) != getattr(instancia, campo) for campo in campos):
                raise ValidationError(
                    "Este lançamento é um recebimento de honorário: valor, status e data de "
                    "pagamento não se alteram por aqui."
                )
        elif not self.pode_receber_honorario and "pago" in (cleaned_data.get("status"), instancia.status)                 and cleaned_data.get("status") != instancia.status:
            self.add_error("status", "Só o Administrador do escritório registra ou desfaz recebimento de honorário.")


_TIPO_CHOICES_DEBITO = [
    (valor, rotulo) for valor, rotulo in CustaJudicial.TIPO_CHOICES if valor != "deposito_cliente"
]


class CustaJudicialForm(forms.ModelForm):
    """Formulário de lançar débito (custa adiantada pelo escritório, ou
    paga diretamente pelo cliente) — 'Depósito do cliente' não aparece
    aqui, só existe pelo fluxo dedicado de Creditar (`CreditarCustaForm`,
    reunião de 13/09)."""

    tipo = forms.ChoiceField(
        choices=_TIPO_CHOICES_DEBITO,
        widget=forms.Select(attrs={"class": "select"}),
        label="Tipo de custa",
    )

    class Meta:
        model = CustaJudicial
        field_classes = {"processo": ProcessoChoiceField}
        fields = ["tipo", "descricao", "valor", "data", "grupo", "cliente", "processo", "anexo"]
        widgets = {
            "descricao": forms.TextInput(attrs={"class": "input", "placeholder": "Ex: Custas de citação – Processo 001/2026"}),
            "grupo": forms.Select(attrs={"class": "select"}),
            "valor": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
            "data": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "cliente": forms.Select(attrs={"class": "select"}),
            "processo": forms.Select(attrs=PROCESSO_SELECT_ATTRS),
            "anexo": forms.ClearableFileInput(attrs={"class": "input"}),
        }
        labels = {
            "descricao": "Descrição",
            "valor": "Valor (R$)",
            "data": "Data",
            "grupo": "Grupo (saldo compartilhado)",
            "cliente": "Cliente",
            "processo": "Processo",
            "anexo": "Anexo (boleto e/ou comprovante)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["cliente"].required = False
        self.fields["cliente"].empty_label = "Nenhum"
        self.fields["grupo"].required = False
        self.fields["grupo"].empty_label = "Nenhum (saldo individual do cliente)"
        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
        _filtrar_processo_por_cliente(self, "financeiro:processos_por_cliente")
        self.fields["data"].input_formats = ["%Y-%m-%d"]
        self.fields["anexo"].required = False

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor


class CreditarCustaForm(forms.ModelForm):
    """Formulário dedicado de Creditar — Cliente e Tipo ('Depósito do
    cliente') nunca aparecem como campo editável: o cliente vem do
    contexto da view (`form_creditar_custa`) e o tipo é sempre fixado no
    save() — reunião de 13/09."""

    class Meta:
        model = CustaJudicial
        field_classes = {"processo": ProcessoChoiceField}
        fields = ["descricao", "valor", "data", "processo", "anexo"]
        widgets = {
            "descricao": forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ex: Depósito antecipado para custas",
            }),
            "valor": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
            "data": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "processo": forms.Select(attrs=PROCESSO_SELECT_ATTRS),
            "anexo": forms.ClearableFileInput(attrs={"class": "input"}),
        }
        labels = {
            "descricao": "Descrição",
            "valor": "Valor (R$)",
            "data": "Data",
            "processo": "Processo (opcional)",
            "anexo": "Anexo (comprovante)",
        }

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        if cliente is None:
            # Crédito de grupo: sem processo (os membros têm processos próprios).
            del self.fields["processo"]
        else:
            self.fields["processo"].required = False
            self.fields["processo"].empty_label = "Nenhum"
            self.fields["processo"].queryset = processos_do_cliente(cliente.pk)
        self.fields["data"].input_formats = ["%Y-%m-%d"]
        self.fields["anexo"].required = False

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor


class GrupoCustasForm(forms.ModelForm):
    class Meta:
        model = GrupoCustas
        fields = ["nome"]
        widgets = {"nome": forms.TextInput(attrs={"class": "input", "placeholder": "Ex: Grupo Holding X"})}
        labels = {"nome": "Nome do grupo"}


class MembroGrupoCustasForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(), label="Cliente",
        widget=forms.Select(attrs={"class": "select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True, grupo_custas__isnull=True)


class ReembolsoCustaForm(forms.Form):
    """Reembolso, pelo cliente, de uma custa adiantada pelo escritório —
    exige o comprovante."""

    data = forms.DateField(
        label="Data do reembolso", input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
    )
    comprovante = forms.FileField(
        label="Comprovante de reembolso",
        widget=forms.ClearableFileInput(attrs={"class": "input"}),
    )


class HonorarioForm(forms.ModelForm):
    """Cadastro manual de honorário (PDR-0007, PDR-0032). Só Contratual e
    Sucumbência se criam; "exito"/"outro" (legado) seguem editáveis no
    modelo simples (valor estimado informado). Contratual: valor (único,
    parcelado ou recorrente) e/ou êxito. Sucumbência: valor-base + correção
    conforme devedor/índice (PDR-0029); o total é sempre recalculado."""

    CAMPOS_SUCUMBENCIA = (
        "forma_condenacao", "percentual", "valor_condenacao", "valor_fixo", "devedor_tipo",
        "indice_correcao", "taxa_indice_mensal",
        "data_correcao", "data_correcao_fim", "data_juros", "data_juros_fim",
    )
    CAMPOS_PAGAMENTO = (
        "classificacao", "periodicidade", "numero_parcelas",
        "duracao_tipo", "duracao_quantidade", "duracao_data_final",
    )
    CAMPOS_EXITO = ("exito_percentual", "exito_base")
    # Estrutura que, depois de gerados os lançamentos, só se muda neles.
    CAMPOS_ESTRUTURA_GERADA = ("tipo", "valor_estimado", "data_prevista", *CAMPOS_PAGAMENTO)

    class Meta:
        model = Honorario
        field_classes = {"processo": ProcessoChoiceField}
        fields = [
            "tipo", "modalidade", "valor_estimado", "processo", "cliente", "data_prevista", "observacoes",
            "classificacao", "periodicidade", "numero_parcelas",
            "duracao_tipo", "duracao_quantidade", "duracao_data_final",
            "exito_percentual", "exito_base",
            "forma_condenacao", "percentual", "valor_condenacao", "valor_fixo", "devedor_tipo",
            "indice_correcao", "taxa_indice_mensal",
            "data_correcao", "data_correcao_fim", "data_juros", "data_juros_fim",
            "documento",
        ]
        widgets = {
            "documento": forms.ClearableFileInput(attrs={"class": "input"}),
            "tipo": forms.Select(attrs={"class": "select", "data-toggle-select": "honorario_tipo"}),
            "modalidade": forms.Select(attrs={"class": "select", "data-toggle-select": "modalidade"}),
            "classificacao": forms.Select(attrs={"class": "select", "data-toggle-select": "pagamento"}),
            "periodicidade": forms.Select(attrs={"class": "select"}),
            "numero_parcelas": forms.NumberInput(attrs={"class": "input", "min": "2"}),
            "duracao_tipo": forms.Select(attrs={"class": "select", "data-toggle-select": "duracao_tipo"}),
            "duracao_quantidade": forms.NumberInput(attrs={"class": "input", "min": "1"}),
            "duracao_data_final": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "exito_percentual": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "exito_base": forms.Select(attrs={"class": "select"}),
            "forma_condenacao": forms.Select(attrs={"class": "select", "data-toggle-select": "forma"}),
            "devedor_tipo": forms.Select(attrs={"class": "select", "data-toggle-select": "devedor"}),
            "indice_correcao": forms.Select(attrs={"class": "select"}),
            "percentual": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "valor_condenacao": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "valor_fixo": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "taxa_indice_mensal": forms.NumberInput(attrs={"class": "input", "step": "0.0001", "min": "0"}),
            "data_correcao": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "data_correcao_fim": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "data_juros": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "data_juros_fim": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "valor_estimado": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
            "processo": forms.Select(attrs=PROCESSO_SELECT_ATTRS),
            "cliente": forms.Select(attrs={"class": "select"}),
            "data_prevista": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "observacoes": forms.Textarea(attrs={"class": "input h-20 resize-none", "rows": 3}),
        }
        labels = {
            "documento": "Documento de origem (contrato ou decisão)",
            "modalidade": "Cobrança contratual",
            "valor_estimado": "Valor (R$)",
            "data_prevista": "Vencimento (ou 1º vencimento)",
            "classificacao": "Pagamento do valor",
            "numero_parcelas": "Quantidade de parcelas",
            "duracao_tipo": "Duração da recorrência",
            "duracao_quantidade": "Quantidade de ocorrências",
            "duracao_data_final": "Data final",
            "exito_percentual": "Percentual de êxito (%)",
            "exito_base": "Base do êxito",
            "forma_condenacao": "Forma da sucumbência",
            "percentual": "Percentual (%)",
            "valor_condenacao": "Valor da condenação (R$)",
            "valor_fixo": "Valor fixo (R$)",
            "devedor_tipo": "Devedor (para cálculo da correção)",
            "indice_correcao": "Índice de correção monetária",
            "taxa_indice_mensal": "Taxa mensal do índice (%)",
            "data_correcao": "Correção monetária — data inicial",
            "data_correcao_fim": "Correção monetária — data final",
            "data_juros": "Juros (1% a.m.) — data inicial",
            "data_juros_fim": "Juros (1% a.m.) — data final",
        }

    # Recebimento já ocorrido, registrado junto com o cadastro (PDR-0035):
    # único = valor inteiro; parcelado/recorrente = só a 1ª parcela.
    ja_recebido = forms.BooleanField(
        label="Já recebido (no parcelado/recorrente: a 1ª parcela)", required=False,
        widget=forms.CheckboxInput(attrs={"class": "rounded border-gray-300"}),
    )
    data_recebimento = forms.DateField(
        label="Data do recebimento", required=False, input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
    )
    comprovante_recebimento = forms.FileField(
        label="Comprovante do recebimento", required=False,
        widget=forms.ClearableFileInput(attrs={"class": "input"}),
    )
    CAMPOS_RECEBIMENTO = ("ja_recebido", "data_recebimento", "comprovante_recebimento")

    def __init__(self, *args, pode_registrar_recebimento=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not pode_registrar_recebimento or self.instance.pk:
            for nome in self.CAMPOS_RECEBIMENTO:
                del self.fields[nome]
        self.fields["documento"].required = False
        campos_opcionais = (
            "valor_estimado", "modalidade", *self.CAMPOS_PAGAMENTO, *self.CAMPOS_EXITO, *self.CAMPOS_SUCUMBENCIA,
        )
        for nome in campos_opcionais:
            self.fields[nome].required = False
        for nome in ("data_correcao", "data_correcao_fim", "data_juros", "data_juros_fim", "duracao_data_final"):
            self.fields[nome].input_formats = ["%Y-%m-%d"]
        # Só Contratual e Sucumbência para criar; o tipo legado do próprio
        # registro continua aceito ao editá-lo.
        self.fields["tipo"].choices = [
            (valor, rotulo) for valor, rotulo in Honorario.TIPO_CHOICES
            if valor in Honorario.TIPOS_NOVOS or valor == self.instance.tipo
        ]
        self.fields["modalidade"].choices = Honorario.MODALIDADE_CHOICES
        self.fields["classificacao"].choices = LancamentoFinanceiro.CLASSIFICACAO_CHOICES
        for nome, opcoes in (
            ("periodicidade", LancamentoFinanceiro.PERIODICIDADE_CHOICES),
            ("duracao_tipo", LancamentoFinanceiro.DURACAO_TIPO_CHOICES),
            ("exito_base", Honorario.EXITO_BASE_CHOICES),
            ("forma_condenacao", Honorario.FORMA_CONDENACAO_CHOICES),
            ("devedor_tipo", Honorario.DEVEDOR_CHOICES),
            ("indice_correcao", Honorario.INDICE_CHOICES),
        ):
            self.fields[nome].choices = [("", "Selecione")] + list(opcoes)
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["cliente"].required = False
        self.fields["cliente"].empty_label = "Nenhum"
        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
        _filtrar_processo_por_cliente(self, "financeiro:processos_por_cliente")
        self.fields["data_prevista"].required = False
        self.fields["data_prevista"].input_formats = ["%Y-%m-%d"]
        self.fields["observacoes"].required = False

    def clean_valor_estimado(self):
        valor = self.cleaned_data.get("valor_estimado")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor

    def _exigir(self, cleaned, campos, mensagem):
        for campo in campos:
            if cleaned.get(campo) in (None, ""):
                self.add_error(campo, mensagem)

    @staticmethod
    def _zerar(cleaned, campos):
        for campo in campos:
            cleaned[campo] = None if Honorario._meta.get_field(campo).null else ""

    def _derivar_cliente_do_processo(self, cleaned, mensagem):
        if not cleaned.get("processo"):
            self.add_error("processo", mensagem)
        elif not cleaned.get("cliente"):
            cleaned["cliente"] = cleaned["processo"].clientes.first()

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        if tipo == "sucumbencial":
            self._clean_sucumbencia(cleaned)
        elif tipo == "contratual":
            self._clean_contratual(cleaned)
        elif tipo:
            self._clean_legado(cleaned)
        self._exigir_estrutura_gerada_intacta(cleaned)
        self._clean_recebimento(cleaned)
        return cleaned

    def _clean_recebimento(self, cleaned):
        if not cleaned.get("ja_recebido"):
            return
        if cleaned.get("tipo") != "contratual" or cleaned.get("modalidade") == "exito":
            # Sucumbência e êxito puro recebem pela confirmação do honorário.
            cleaned["ja_recebido"] = False
            return
        data = cleaned.get("data_recebimento")
        if not data:
            self.add_error("data_recebimento", "Informe a data do recebimento.")
        elif data > timezone.localdate():
            self.add_error("data_recebimento", "A data do recebimento não pode ser futura.")

    def _clean_legado(self, cleaned):
        if cleaned.get("valor_estimado") is None:
            self.add_error("valor_estimado", "Informe o valor estimado.")
        self._zerar(cleaned, (*self.CAMPOS_SUCUMBENCIA, "modalidade", *self.CAMPOS_PAGAMENTO, *self.CAMPOS_EXITO))

    def _clean_contratual(self, cleaned):
        modalidade = cleaned["modalidade"] = cleaned.get("modalidade") or "valor"
        self._zerar(cleaned, self.CAMPOS_SUCUMBENCIA)
        if modalidade in ("valor", "valor_exito"):
            self._clean_valor_contratual(cleaned)
        else:
            cleaned["valor_estimado"] = Decimal("0")
            cleaned["data_prevista"] = None
            self._zerar(cleaned, self.CAMPOS_PAGAMENTO)
        if modalidade in ("exito", "valor_exito"):
            self._clean_exito_contratual(cleaned)
        else:
            self._zerar(cleaned, self.CAMPOS_EXITO)

    def _clean_valor_contratual(self, cleaned):
        if cleaned.get("valor_estimado") is None:
            self.add_error("valor_estimado", "Informe o valor.")
        classificacao = cleaned["classificacao"] = cleaned.get("classificacao") or "unica"
        if classificacao == "unica":
            self._zerar(cleaned, self.CAMPOS_PAGAMENTO[1:])
            return
        if not cleaned.get("data_prevista"):
            self.add_error("data_prevista", "Informe a data do primeiro vencimento.")
        if self.instance.valor_recebido > 0:
            self.add_error(
                "classificacao",
                "Já há recebimento confirmado: o pagamento não pode mais ser parcelado ou recorrente.",
            )
        self._validar_recorrencia(cleaned)
        if classificacao == "parcelado":
            self._zerar(cleaned, ("periodicidade", "duracao_tipo", "duracao_quantidade", "duracao_data_final"))
        else:
            self._zerar(cleaned, ("numero_parcelas",))
            if cleaned.get("duracao_tipo") != "quantidade":
                self._zerar(cleaned, ("duracao_quantidade",))
            if cleaned.get("duracao_tipo") != "data_final":
                self._zerar(cleaned, ("duracao_data_final",))

    def _validar_recorrencia(self, cleaned):
        """Mesmas regras de parcelado/recorrente do lançamento (PDR-0021),
        reaproveitando a validação do próprio modelo."""
        provisorio = LancamentoFinanceiro(
            data_vencimento=cleaned.get("data_prevista"),
            **{campo: cleaned.get(campo) for campo in self.CAMPOS_PAGAMENTO},
        )
        try:
            provisorio.clean()
        except ValidationError as erro:
            for campo, mensagens in erro.message_dict.items():
                self.add_error(campo, mensagens)

    def _clean_exito_contratual(self, cleaned):
        self._derivar_cliente_do_processo(cleaned, "Informe o processo — obrigatório para honorário por êxito.")
        self._exigir(cleaned, self.CAMPOS_EXITO, "Obrigatório para honorário por êxito.")
        percentual = cleaned.get("exito_percentual")
        if percentual is not None and not 0 < percentual <= 100:
            self.add_error("exito_percentual", "Informe um percentual entre 0 e 100.")

    def _clean_sucumbencia(self, cleaned):
        obrigatorio = "Obrigatório para honorário de sucumbência."
        self._derivar_cliente_do_processo(cleaned, "Informe o processo — o cliente é derivado dele.")
        self._exigir(cleaned, ("forma_condenacao", "devedor_tipo", "data_correcao"), obrigatorio)
        forma = cleaned.get("forma_condenacao")
        if forma in ("percentual", "fixo_percentual"):
            self._exigir(cleaned, ("percentual", "valor_condenacao"), obrigatorio)
        else:
            cleaned["percentual"] = cleaned["valor_condenacao"] = None
        if forma in ("fixo", "fixo_percentual"):
            self._exigir(cleaned, ("valor_fixo",), obrigatorio)
        else:
            cleaned["valor_fixo"] = None
        if cleaned.get("devedor_tipo") == "pessoa":
            self._exigir(cleaned, ("indice_correcao", "data_juros"), obrigatorio)
        else:
            # Ente estatal: só a Selic, unificada, sem juros à parte.
            cleaned["indice_correcao"] = "selic"
            cleaned["data_juros"] = cleaned["data_juros_fim"] = None
        for inicio, fim in (("data_correcao", "data_correcao_fim"), ("data_juros", "data_juros_fim")):
            if cleaned.get(inicio) and cleaned.get(fim) and cleaned[fim] < cleaned[inicio]:
                self.add_error(fim, "A data final não pode ser anterior à inicial.")
        self._zerar(cleaned, ("modalidade", *self.CAMPOS_PAGAMENTO, "exito_base"))
        # O êxito passou a ser o contrato do processo (aviso na sucumbência);
        # o êxito embutido de registros anteriores é preservado, sem edição.
        embutido = self.instance.tipo == "sucumbencial" and self.instance.exito_percentual is not None
        cleaned["exito_percentual"] = self.instance.exito_percentual if embutido else None

        if not self.errors:
            # Valor estimado = total calculado hoje (o exibido é sempre recalculado).
            provisorio = Honorario(
                exito_valor_ganho=self.instance.exito_valor_ganho if embutido else None,
                exito_data_correcao=self.instance.exito_data_correcao if embutido else None,
                **{campo: cleaned.get(campo) for campo in (*self.CAMPOS_SUCUMBENCIA, "exito_percentual")},
            )
            cleaned["valor_estimado"] = calcular_honorario_sucumbencial(
                provisorio, timezone.localdate(), contratos_de_exito_pelo_ganho(cleaned.get("processo")),
            )["total"]

    def _exigir_estrutura_gerada_intacta(self, cleaned):
        # Honorário único também tem lançamentos (os recebimentos), mas a
        # estrutura dele segue editável no próprio honorário.
        instancia = self.instance
        if self.errors or not instancia.pk or not instancia.recebimento_por_lancamentos                 or not instancia.lancamentos.exists():
            return
        if any(cleaned.get(campo) != getattr(self.instance, campo) for campo in self.CAMPOS_ESTRUTURA_GERADA):
            raise forms.ValidationError(
                "Os lançamentos deste honorário já foram gerados: para mudar valor, datas ou "
                "parcelamento, ajuste-os no Financeiro."
            )


class ConfirmarRecebimentoHonorarioForm(forms.ModelForm):
    """Confirmação de recebimento (PDR-0007), parcial ou total
    (PDR-0022). `valor_recebido_agora` em branco confirma o valor
    pendente inteiro — mesmo comportamento de antes do PDR-0022, quando
    só existia confirmação total. `taxa_mensal`/`data_termo` em branco
    não aplica nenhuma correção."""

    valor_recebido_agora = forms.DecimalField(
        label="Valor recebido agora (R$)", max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
        help_text="Em branco, confirma o valor pendente inteiro.",
    )
    anexo = forms.FileField(
        label="Anexar comprovante", required=False,
        widget=forms.ClearableFileInput(attrs={"class": "input"}),
    )

    class Meta:
        model = Honorario
        fields = ["valor_efetivo", "data_recebida", "taxa_mensal", "data_termo"]
        widgets = {
            "valor_efetivo": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
            "data_recebida": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "taxa_mensal": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "data_termo": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
        }
        labels = {
            "valor_efetivo": "Valor efetivo (total a receber, R$)",
            "data_recebida": "Data desta confirmação",
            "taxa_mensal": "Taxa de correção mensal (%)",
            "data_termo": "Data-termo da correção",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["valor_efetivo"].required = True
        self.fields["data_recebida"].required = True
        self.fields["data_recebida"].input_formats = ["%Y-%m-%d"]
        self.fields["taxa_mensal"].required = False
        self.fields["data_termo"].required = False
        self.fields["data_termo"].input_formats = ["%Y-%m-%d"]

    def clean_valor_efetivo(self):
        valor = self.cleaned_data.get("valor_efetivo")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor

    def clean_valor_recebido_agora(self):
        valor = self.cleaned_data.get("valor_recebido_agora")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor


class SolicitacaoFinanceiraForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoFinanceira
        field_classes = {"processo": ProcessoChoiceField}
        fields = [
            "tipo",
            "descricao",
            "valor",
            "cliente",
            "processo",
            "vencimento",
            "data_gasto",
            "anexo",
            "observacao",
        ]
        widgets = {
            "tipo":        forms.Select(attrs={"class": "select", "data-toggle-select": "tipo"}),
            "descricao":   forms.TextInput(attrs={"class": "input"}),
            "valor":       forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "cliente":     forms.Select(attrs={"class": "select"}),
            "processo":    forms.Select(attrs=PROCESSO_SELECT_ATTRS),
            "vencimento":  forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "data_gasto":  forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "anexo":       forms.ClearableFileInput(attrs={"class": "input"}),
            "observacao":  forms.Textarea(attrs={"class": "input h-20 resize-none", "rows": 3}),
        }
        labels = {
            "anexo": "Anexo (boleto para pagamento, comprovante para reembolso)",
        }

    def __init__(self, *args, processo_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["cliente"].required = False
        self.fields["cliente"].empty_label = "Nenhum"

        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
        _filtrar_processo_por_cliente(self, "financeiro:processos_por_cliente")

        self.fields["vencimento"].required = False
        self.fields["vencimento"].input_formats = ["%Y-%m-%d"]
        self.fields["data_gasto"].required = False
        self.fields["data_gasto"].input_formats = ["%Y-%m-%d"]
        self.fields["observacao"].required = False

        self.processo_fixo = processo_fixo
        self.cliente_travado = False
        if processo_fixo is not None:
            self._travar_tipo_processo_cliente(processo_fixo)

    def _travar_tipo_processo_cliente(self, processo_fixo):
        """Solicitação nascida da aba Custas Judiciais de um processo
        (`?processo=<id>`): sempre uma custa a pagar, sem margem para virar
        reembolso, e sem poder trocar o processo/cliente que originou o
        pedido — evita a inconsistência de o usuário escolher outro
        processo/cliente no meio do caminho."""
        self.fields["tipo"].widget = forms.HiddenInput(attrs={"data-toggle-select": "tipo"})
        self.initial["tipo"] = "pagamento"

        self.fields["processo"].widget = forms.HiddenInput()
        self.fields["processo"].queryset = Processo.objects.filter(pk=processo_fixo.pk)
        self.initial["processo"] = processo_fixo.pk

        clientes_processo = list(processo_fixo.clientes.all())
        self.fields["cliente"].queryset = Cliente.objects.filter(
            pk__in=[cliente.pk for cliente in clientes_processo]
        )
        if len(clientes_processo) == 1:
            self.fields["cliente"].widget = forms.HiddenInput()
            self.initial["cliente"] = clientes_processo[0].pk
            self.cliente_travado = True
        else:
            # Mais de um cliente no processo: usuário ainda escolhe entre
            # eles, nunca de toda a base de clientes.
            self.fields["cliente"].required = True
            self.fields["cliente"].empty_label = None

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")

        # Processo é opcional nos dois tipos. Vencimento só existe em
        # pagamento e data do gasto só em reembolso — o outro é descartado.
        if tipo == "pagamento":
            if not cleaned_data.get("cliente"):
                self.add_error("cliente", "Informe o cliente para solicitação de pagamento.")
            if not cleaned_data.get("vencimento"):
                self.add_error("vencimento", "Informe o vencimento para solicitação de pagamento.")
            cleaned_data["data_gasto"] = None
        elif tipo == "reembolso":
            if not cleaned_data.get("data_gasto"):
                self.add_error("data_gasto", "Informe a data do gasto para solicitação de reembolso.")
            cleaned_data["vencimento"] = None

        return cleaned_data
