from django.db import models
from django.contrib.auth.models import User
from apps.clientes.models import Cliente
from apps.processos.models import Processo


class LancamentoFinanceiro(models.Model):
    TIPO_CHOICES = [
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    ]

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("pago", "Pago"),
        ("cancelado", "Cancelado"),
    ]

    CATEGORIA_CHOICES = [
        ("honorario", "Honorário"),
        ("exito", "Honorário de Êxito"),
        ("reembolso", "Reembolso"),
        ("custa_judicial", "Custa Judicial"),
        ("diligencia", "Diligência"),
        ("pericia", "Perícia"),
        ("taxa", "Taxa/Emolumento"),
        ("salario", "Salário/Pró-labore"),
        ("aluguel", "Aluguel"),
        ("software", "Software/Assinatura"),
        ("imposto", "Imposto"),
        ("despesa_escritorio", "Despesa do Escritório"),
        ("outro", "Outro"),
    ]

    FORMA_PAGAMENTO_CHOICES = [
        ("pix", "Pix"),
        ("boleto", "Boleto"),
        ("transferencia", "Transferência"),
        ("dinheiro", "Dinheiro"),
        ("cartao", "Cartão"),
        ("outro", "Outro"),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, default="honorario")
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES, blank=True)
    data_pagamento = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"
        ordering = ["data_vencimento", "-criado_em"]

    def __str__(self):
        return f"{self.tipo} — {self.descricao} ({self.valor})"

    @property
    def atrasado(self):
        from django.utils import timezone
        return (
            self.status == "pendente"
            and self.data_vencimento is not None
            and self.data_vencimento < timezone.localdate()
        )


class CustaJudicial(models.Model):
    TIPO_CHOICES = [
        ("adiantamento", "Adiantado pelo escritório"),
        ("deposito_cliente", "Depósito do cliente"),
    ]

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Custa Judicial"
        verbose_name_plural = "Custas Judiciais"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.descricao} — {self.valor}"
