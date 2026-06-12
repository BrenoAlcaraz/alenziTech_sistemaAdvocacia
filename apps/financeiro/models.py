from django.db import models
from django.contrib.auth.models import User
from apps.clientes.models import Cliente
from apps.processos.models import Processo


class LancamentoFinanceiro(models.Model):
    TIPO_CHOICES = [
        ("receita", "Receita"),
        ("despesa", "Despesa"),
    ]

    CATEGORIA_CHOICES = [
        ("honorario", "Honorário"),
        ("despesa_escritorio", "Despesa do Escritório"),
        ("reembolso", "Reembolso"),
        ("exito", "Honorário de Êxito"),
        ("outro", "Outro"),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES, default="honorario")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.tipo} — {self.descricao} ({self.valor})"


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
