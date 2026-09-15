from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from apps.clientes.models import Cliente
from apps.processos.models import Processo
from apps.processos.services import processo_pertence_ao_cliente
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

    # Classificação e periodicidade da recorrência (PDR-0021) — conjunto
    # fechado: parcelado é sempre mensal entre parcelas; recorrente aceita
    # só mensal ou anual.
    CLASSIFICACAO_CHOICES = [
        ("unica", "Única"),
        ("parcelado", "Parcelado"),
        ("recorrente", "Recorrente"),
    ]

    PERIODICIDADE_CHOICES = [
        ("mensal", "Mensal"),
        ("anual", "Anual"),
    ]

    DURACAO_TIPO_CHOICES = [
        ("quantidade", "Quantidade de ocorrências"),
        ("data_final", "Data final"),
        ("indeterminado", "Indeterminado"),
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
    anexo = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "financeiro/lancamentos"),
        storage=StorageProtegido(),
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    classificacao = models.CharField(max_length=12, choices=CLASSIFICACAO_CHOICES, default="unica")
    periodicidade = models.CharField(max_length=10, choices=PERIODICIDADE_CHOICES, blank=True)
    numero_parcelas = models.PositiveSmallIntegerField(null=True, blank=True)
    duracao_tipo = models.CharField(max_length=15, choices=DURACAO_TIPO_CHOICES, blank=True)
    duracao_quantidade = models.PositiveSmallIntegerField(null=True, blank=True)
    duracao_data_final = models.DateField(null=True, blank=True)
    lancamento_origem = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="ocorrencias",
    )

    class Meta:
        verbose_name = "Lançamento Financeiro"
        verbose_name_plural = "Lançamentos Financeiros"
        ordering = ["data_vencimento", "-criado_em"]

    def __str__(self):
        return f"{self.tipo} — {self.descricao} ({self.valor})"

    def clean(self):
        if not processo_pertence_ao_cliente(self.cliente, self.processo):
            raise ValidationError({"processo": "O processo selecionado não pertence ao cliente informado."})

        if self.lancamento_origem_id:
            # Ocorrência já gerada: classificacao/periodicidade são só
            # informativas (herdadas da origem), não redisparam a
            # exigência de parcelas/duração — essas vivem só na origem.
            return

        erros = {}
        if self.classificacao == "parcelado":
            if not self.numero_parcelas or self.numero_parcelas < 2:
                erros["numero_parcelas"] = "Informe ao menos 2 parcelas."
        elif self.classificacao == "recorrente":
            if self.periodicidade not in dict(self.PERIODICIDADE_CHOICES):
                erros["periodicidade"] = "Selecione mensal ou anual."
            if self.duracao_tipo == "quantidade" and not self.duracao_quantidade:
                erros["duracao_quantidade"] = "Informe a quantidade de ocorrências."
            elif self.duracao_tipo == "data_final":
                if not self.duracao_data_final:
                    erros["duracao_data_final"] = "Informe a data final."
                elif self.data_vencimento and self.duracao_data_final <= self.data_vencimento:
                    erros["duracao_data_final"] = "A data final deve ser depois do primeiro vencimento."
            elif self.duracao_tipo not in dict(self.DURACAO_TIPO_CHOICES):
                erros["duracao_tipo"] = "Selecione a duração da recorrência."
        if erros:
            raise ValidationError(erros)

    @property
    def atrasado(self):
        from django.utils import timezone
        return (
            self.status == "pendente"
            and self.data_vencimento is not None
            and self.data_vencimento < timezone.localdate()
        )


class CustaJudicial(models.Model):
    # "adiantamento" e "paga_pelo_cliente" são custas de fato (o processo
    # exigiu o pagamento); "deposito_cliente" é crédito adiantado pelo
    # cliente, não uma custa. Só "adiantamento" e "deposito_cliente"
    # entram na fórmula do saldo (PDR-0005) — "paga_pelo_cliente" fica
    # só no histórico, sem afetar o saldo.
    TIPO_CHOICES = [
        ("adiantamento", "Adiantado pelo escritório"),
        ("paga_pelo_cliente", "Paga diretamente pelo cliente"),
        ("deposito_cliente", "Depósito do cliente"),
    ]

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True)
    anexo = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "financeiro/custas"),
        storage=StorageProtegido(),
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Custa Judicial"
        verbose_name_plural = "Custas Judiciais"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.descricao} — {self.valor}"

    def clean(self):
        if not processo_pertence_ao_cliente(self.cliente, self.processo):
            raise ValidationError({"processo": "O processo selecionado não pertence ao cliente informado."})


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

    # Recebimento parcial e correção monetária/juros (PDR-0022).
    # valor_recebido acumula as confirmações já feitas; valor_pendente
    # nunca é armazenado, é sempre valor_efetivo - valor_recebido.
    # taxa_mensal/data_termo ausentes = sem correção (comportamento
    # idêntico ao anterior ao PDR-0022).
    valor_recebido = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    taxa_mensal = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    data_termo = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Honorário"
        verbose_name_plural = "Honorários"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.valor_estimado}"

    def clean(self):
        if not processo_pertence_ao_cliente(self.cliente, self.processo):
            raise ValidationError({"processo": "O processo selecionado não pertence ao cliente informado."})


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

    # Quem efetivamente pagou a custa (só se aplica a `tipo="pagamento"`,
    # exigido ao confirmar o pagamento) — alimenta o CustaJudicial gerado
    # para o cliente (PDR-0005): "escritorio" vira débito que reduz o
    # saldo do cliente, "cliente" fica só no histórico, sem afetar saldo.
    PAGO_POR_CHOICES = [
        ("escritorio", "Escritório"),
        ("cliente", "Cliente"),
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
    pago_por = models.CharField(max_length=12, choices=PAGO_POR_CHOICES, blank=True)
    comprovante_pagamento = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "financeiro/solicitacoes/comprovantes"),
        storage=StorageProtegido(),
        null=True, blank=True,
    )
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

    def clean(self):
        if not processo_pertence_ao_cliente(self.cliente, self.processo):
            raise ValidationError({"processo": "O processo selecionado não pertence ao cliente informado."})

    def pode_transicionar_para(self, novo_status):
        return novo_status in self.TRANSICOES_VALIDAS.get(self.status, set())

    def avancar_para(self, novo_status, *, pago_por=None, comprovante_pagamento=None):
        """Move a solicitação para o próximo estado do fluxo (PDR-0015).

        Ao atingir 'paga', gera o único LancamentoFinanceiro realizado
        desta solicitação — só nesse momento a despesa passa a existir
        como realizada (PDR-0006). Para `tipo="pagamento"` (a custa
        judicial solicitada a partir de um processo), exige também quem
        pagou e o comprovante, e replica o pagamento como CustaJudicial
        do cliente (PDR-0005) — "escritorio" vira débito (`adiantamento`,
        entra no saldo a cobrar do cliente), "cliente" só fica no
        histórico (`paga_pelo_cliente`, mesmo comportamento do
        lançamento manual equivalente). Reembolso não passa por essa
        exigência: não representa uma custa judicial paga pelo
        escritório ou pelo cliente.
        """
        if not self.pode_transicionar_para(novo_status):
            raise ValueError(f"Transição inválida de '{self.status}' para '{novo_status}'.")

        if novo_status != "paga":
            self.status = novo_status
            self.save(update_fields=["status"])
            return

        exige_pagamento_de_custa = self.tipo == "pagamento"
        if exige_pagamento_de_custa:
            if pago_por not in dict(self.PAGO_POR_CHOICES):
                raise ValueError("Informe se a custa foi paga pelo escritório ou pelo cliente.")
            if not comprovante_pagamento:
                raise ValueError("O comprovante de pagamento é obrigatório.")

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
            update_fields = ["status", "lancamento"]
            if exige_pagamento_de_custa:
                self.pago_por = pago_por
                self.comprovante_pagamento = comprovante_pagamento
                update_fields += ["pago_por", "comprovante_pagamento"]
            self.save(update_fields=update_fields)

            if exige_pagamento_de_custa and self.cliente_id:
                CustaJudicial.objects.create(
                    tipo="adiantamento" if pago_por == "escritorio" else "paga_pelo_cliente",
                    descricao=self.descricao,
                    valor=self.valor,
                    data=timezone.localdate(),
                    cliente=self.cliente,
                    processo=self.processo,
                    anexo=comprovante_pagamento,
                )
