from django import forms
from django.contrib.auth.models import User
from django.urls import reverse

from .models import LancamentoFinanceiro, CustaJudicial, Honorario, SolicitacaoFinanceira
from apps.clientes.models import Cliente
from apps.processos.models import Processo


def _cliente_id_atual(form):
    """Cliente já conhecido no form (reenvio, edição ou pré-seleção) para
    filtrar o queryset de Processo antes de qualquer interação via JS."""
    return form.data.get("cliente") or form.initial.get("cliente") or getattr(form.instance, "cliente_id", None)


def _filtrar_processo_por_cliente(form, url_name):
    """Restringe o campo Processo ao cliente já conhecido e prepara os
    atributos consumidos pelo filtro dinâmico em static/js/main.js."""
    cliente_id = _cliente_id_atual(form)
    qs = Processo.objects.select_related("cliente").exclude(status="arquivado")
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    form.fields["processo"].queryset = qs
    form.fields["cliente"].widget.attrs["data-cliente-filtro"] = "1"
    form.fields["processo"].widget.attrs["data-processos-url"] = reverse(url_name)


class LancamentoFinanceiroForm(forms.ModelForm):
    class Meta:
        model = LancamentoFinanceiro
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
        ]
        widgets = {
            "tipo":            forms.Select(attrs={"class": "select"}),
            "descricao":       forms.TextInput(attrs={"class": "input"}),
            "valor":           forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "data_vencimento": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "data_pagamento":  forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "categoria":       forms.Select(attrs={"class": "select"}),
            "status":          forms.Select(attrs={"class": "select"}),
            "forma_pagamento": forms.Select(attrs={"class": "select"}),
            "cliente":         forms.Select(attrs={"class": "select"}),
            "processo":        forms.Select(attrs={"class": "select"}),
            "responsavel":     forms.Select(attrs={"class": "select"}),
            "observacoes":     forms.Textarea(attrs={"class": "input h-20 resize-none", "rows": 3}),
            "classificacao":   forms.Select(attrs={"class": "select", "data-toggle-select": "classificacao"}),
            "periodicidade":   forms.Select(attrs={"class": "select"}),
            "numero_parcelas": forms.NumberInput(attrs={"class": "input", "min": "2"}),
            "duracao_tipo":    forms.Select(attrs={"class": "select", "data-toggle-select": "duracao_tipo"}),
            "duracao_quantidade": forms.NumberInput(attrs={"class": "input", "min": "1"}),
            "duracao_data_final": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
        }
        labels = {
            "classificacao": "Classificação",
            "numero_parcelas": "Quantidade de parcelas",
            "duracao_tipo": "Duração da recorrência",
            "duracao_quantidade": "Quantidade de ocorrências",
            "duracao_data_final": "Data final",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["cliente"].required = False
        self.fields["cliente"].empty_label = "Nenhum"

        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
        _filtrar_processo_por_cliente(self, "financeiro:processos_por_cliente")

        self.fields["responsavel"].queryset = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.fields["responsavel"].required = False
        self.fields["responsavel"].empty_label = "Nenhum"

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

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        data_pagamento = cleaned_data.get("data_pagamento")

        if status == "pago" and not data_pagamento:
            self.add_error("data_pagamento", "Informe a data de pagamento para lançamentos pagos.")

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


class CustaJudicialForm(forms.ModelForm):
    class Meta:
        model = CustaJudicial
        fields = ["tipo", "descricao", "valor", "data", "cliente", "processo"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "select"}),
            "descricao": forms.TextInput(attrs={"class": "input", "placeholder": "Ex: Custas de citação – Processo 001/2026"}),
            "valor": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
            "data": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "cliente": forms.Select(attrs={"class": "select"}),
            "processo": forms.Select(attrs={"class": "select"}),
        }
        labels = {
            "tipo": "Tipo de custa",
            "descricao": "Descrição",
            "valor": "Valor (R$)",
            "data": "Data",
            "cliente": "Cliente",
            "processo": "Processo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["cliente"].required = False
        self.fields["cliente"].empty_label = "Nenhum"
        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
        _filtrar_processo_por_cliente(self, "financeiro:processos_por_cliente")
        self.fields["data"].input_formats = ["%Y-%m-%d"]

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor


class HonorarioForm(forms.ModelForm):
    class Meta:
        model = Honorario
        fields = ["tipo", "valor_estimado", "processo", "cliente", "data_prevista", "observacoes"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "select"}),
            "valor_estimado": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
            "processo": forms.Select(attrs={"class": "select"}),
            "cliente": forms.Select(attrs={"class": "select"}),
            "data_prevista": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "observacoes": forms.Textarea(attrs={"class": "input h-20 resize-none", "rows": 3}),
        }
        labels = {
            "valor_estimado": "Valor estimado (R$)",
            "data_prevista": "Data prevista",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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


class ConfirmarRecebimentoHonorarioForm(forms.ModelForm):
    class Meta:
        model = Honorario
        fields = ["valor_efetivo", "data_recebida"]
        widgets = {
            "valor_efetivo": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0.01"}),
            "data_recebida": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
        }
        labels = {
            "valor_efetivo": "Valor efetivo recebido (R$)",
            "data_recebida": "Data recebida",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["valor_efetivo"].required = True
        self.fields["data_recebida"].required = True
        self.fields["data_recebida"].input_formats = ["%Y-%m-%d"]

    def clean_valor_efetivo(self):
        valor = self.cleaned_data.get("valor_efetivo")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor

    def save(self, commit=True):
        honorario = super().save(commit=False)
        honorario.status = "recebido"
        if commit:
            honorario.save()
        return honorario


class SolicitacaoFinanceiraForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoFinanceira
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
            "tipo":        forms.Select(attrs={"class": "select"}),
            "descricao":   forms.TextInput(attrs={"class": "input"}),
            "valor":       forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "cliente":     forms.Select(attrs={"class": "select"}),
            "processo":    forms.Select(attrs={"class": "select"}),
            "vencimento":  forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "data_gasto":  forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "anexo":       forms.ClearableFileInput(attrs={"class": "input"}),
            "observacao":  forms.Textarea(attrs={"class": "input h-20 resize-none", "rows": 3}),
        }
        labels = {
            "anexo": "Anexo (boleto para pagamento, comprovante para reembolso)",
        }

    def __init__(self, *args, **kwargs):
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

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")

        if tipo == "pagamento":
            if not cleaned_data.get("cliente"):
                self.add_error("cliente", "Informe o cliente para solicitação de pagamento.")
            if not cleaned_data.get("processo"):
                self.add_error("processo", "Informe o processo para solicitação de pagamento.")
            if not cleaned_data.get("vencimento"):
                self.add_error("vencimento", "Informe o vencimento para solicitação de pagamento.")
        elif tipo == "reembolso":
            if not cleaned_data.get("data_gasto"):
                self.add_error("data_gasto", "Informe a data do gasto para solicitação de reembolso.")

        return cleaned_data
