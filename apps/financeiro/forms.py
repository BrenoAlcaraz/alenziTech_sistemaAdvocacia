from django import forms
from django.contrib.auth.models import User

from .models import LancamentoFinanceiro
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
