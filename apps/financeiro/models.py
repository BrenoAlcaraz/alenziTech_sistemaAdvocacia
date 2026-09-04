from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.saas_tenants.storage import (
    CaminhoArquivoTenant,
    PROTEGIDO,
    StorageProtegido,
)


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
        ("solicitacao_pagamento", "Solicitação de Pagamento"),
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


class Honorario(models.Model):
    """Cadastro manual de honorário advocatício (PDR-0007). Área própria,
    distinta do financeiro geral e de custas judiciais (PDR-0003)."""

    TIPO_CHOICES = [
        ("contratual", "Contratual"),
        ("sucumbencial", "Sucumbencial"),
        ("exito", "Êxito"),
        ("outro", "Outro"),
    ]

    STATUS_CHOICES = [
        ("previsto", "Previsto"),
        ("recebido", "Recebido"),
        ("cancelado", "Cancelado"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor_estimado = models.DecimalField(max_digits=12, decimal_places=2)
    valor_efetivo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    data_prevista = models.DateField(null=True, blank=True)
    data_recebida = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="previsto")
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Honorário"
        verbose_name_plural = "Honorários"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.valor_estimado}"


class SolicitacaoFinanceira(models.Model):
    """Solicitação de pagamento ou reembolso feita por quem não tem acesso
    ao caixa geral (PDR-0006). Fluxo de estados definido por PDR-0015."""

    TIPO_CHOICES = [
        ("pagamento", "Pagamento"),
        ("reembolso", "Reembolso"),
    ]

    STATUS_CHOICES = [
        ("solicitada", "Solicitada"),
        ("em_analise", "Em análise"),
        ("aprovada", "Aprovada"),
        ("rejeitada", "Rejeitada"),
        ("paga", "Paga"),
    ]

    TRANSICOES_VALIDAS = {
        "solicitada": {"em_analise"},
        "em_analise": {"aprovada", "rejeitada"},
        "aprovada": {"paga"},
        "rejeitada": set(),
        "paga": set(),
    }

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="solicitada")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True)
    vencimento = models.DateField(null=True, blank=True)
    data_gasto = models.DateField(null=True, blank=True)
    anexo = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "financeiro/solicitacoes"),
        storage=StorageProtegido(),
    )
    observacao = models.TextField(blank=True)
    solicitante = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="solicitacoes_financeiras",
    )
    lancamento = models.OneToOneField(
        LancamentoFinanceiro, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="solicitacao_origem",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Solicitação Financeira"
        verbose_name_plural = "Solicitações Financeiras"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.descricao} ({self.valor})"

    def pode_transicionar_para(self, novo_status):
        return novo_status in self.TRANSICOES_VALIDAS.get(self.status, set())

    def avancar_para(self, novo_status):
        """Move a solicitação para o próximo estado do fluxo (PDR-0015).

        Ao atingir 'paga', gera o único LancamentoFinanceiro realizado
        desta solicitação — só nesse momento a despesa passa a existir
        como realizada (PDR-0006).
        """
        if not self.pode_transicionar_para(novo_status):
            raise ValueError(f"Transição inválida de '{self.status}' para '{novo_status}'.")

        if novo_status == "paga":
            with transaction.atomic():
                self.lancamento = LancamentoFinanceiro.objects.create(
                    tipo="despesa",
                    descricao=self.descricao,
                    valor=self.valor,
                    data_vencimento=self.vencimento or timezone.localdate(),
                    status="pago",
                    categoria="reembolso" if self.tipo == "reembolso" else "solicitacao_pagamento",
                    data_pagamento=timezone.localdate(),
                    observacoes=self.observacao,
                    cliente=self.cliente,
                    processo=self.processo,
                    responsavel=self.solicitante,
                )
                self.status = novo_status
                self.save(update_fields=["status", "lancamento"])
        else:
            self.status = novo_status
            self.save(update_fields=["status"])
