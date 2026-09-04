from django import forms
from django.contrib.auth.models import User

from .models import LancamentoFinanceiro, CustaJudicial, Honorario, SolicitacaoFinanceira
from apps.clientes.models import Cliente
from apps.processos.models import Processo


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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["cliente"].required = False
        self.fields["cliente"].empty_label = "Nenhum"

        self.fields["processo"].queryset = Processo.objects.select_related("cliente").exclude(status="arquivado")
        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"

        self.fields["responsavel"].queryset = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.fields["responsavel"].required = False
        self.fields["responsavel"].empty_label = "Nenhum"

        self.fields["data_vencimento"].input_formats = ["%Y-%m-%d"]
        self.fields["data_pagamento"].required = False
        self.fields["data_pagamento"].input_formats = ["%Y-%m-%d"]

        self.fields["forma_pagamento"].required = False
        self.fields["observacoes"].required = False

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        data_pagamento = cleaned_data.get("data_pagamento")

        if status == "pago" and not data_pagamento:
            self.add_error("data_pagamento", "Informe a data de pagamento para lançamentos pagos.")

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
        self.fields["processo"].queryset = Processo.objects.select_related("cliente").exclude(status="arquivado")
        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
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
        self.fields["processo"].queryset = Processo.objects.select_related("cliente").exclude(status="arquivado")
        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"
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

        self.fields["processo"].queryset = Processo.objects.select_related("cliente").exclude(status="arquivado")
        self.fields["processo"].required = False
        self.fields["processo"].empty_label = "Nenhum"

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
