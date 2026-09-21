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
        ("honorario", "Honorários"),
        ("honorario_sucumbencia", "Honorários de sucumbência"),
        ("reembolso", "Reembolso"),
        ("consultoria", "Consultoria"),
        ("comissao", "Comissão"),
        ("auditoria", "Auditoria"),
        ("acordo", "Acordo"),
        ("capacitacao", "Capacitação"),
        ("aluguel", "Aluguel"),
        ("condominio", "Condomínio"),
        ("agua", "Água"),
        ("luz", "Luz"),
        ("internet", "Internet"),
        ("salario", "Salário"),
        ("bonificacao", "Bonificação"),
        ("imposto", "Impostos/taxas"),
        ("cursos", "Cursos"),
        ("equipamentos", "Equipamentos"),
        ("material", "Material"),
        ("software", "Software/assinatura"),
        ("outro", "Outros"),
        # Só o sistema gera estas (solicitações, custas, honorários
        # confirmados) ou já existiam antes da revisão de 2026-09-20 —
        # ficam fora do dropdown manual e mantêm o rótulo na listagem.
        ("exito", "Honorário de Êxito"),
        ("solicitacao_pagamento", "Solicitação de Pagamento"),
        ("custa_judicial", "Custa Judicial"),
        ("diligencia", "Diligência"),
        ("pericia", "Perícia"),
        ("taxa", "Taxa/Emolumento"),
    ]

    # Categorias que o usuário escolhe à mão em cada tipo — o formulário só
    # oferece as do tipo escolhido e o backend recusa a combinação inválida.
    # "reembolso" como receita é o cliente devolvendo custa adiantada
    # (credita nas custas judiciais dele).
    CATEGORIAS_POR_TIPO = {
        "receita": (
            "honorario", "honorario_sucumbencia", "reembolso", "consultoria",
            "comissao", "auditoria", "acordo", "capacitacao", "outro",
        ),
        "despesa": (
            "aluguel", "condominio", "agua", "luz", "internet", "salario",
            "bonificacao", "imposto", "cursos", "equipamentos", "material",
            "software", "outro",
        ),
    }

    # Despesas com estas categorias e cliente vinculado são custas do
    # cliente: entram nos totais só pelo saldo devedor dele (ver
    # `services.custas_a_recuperar`), nunca pelo lançamento em si.
    CATEGORIAS_CUSTA_DO_CLIENTE = ("custa_judicial", "solicitacao_pagamento")

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

    # Crédito nascido de uma receita "Reembolso" do financeiro geral: o
    # lançamento é a origem e o crédito some junto com ele.
    lancamento = models.OneToOneField(
        "LancamentoFinanceiro", on_delete=models.CASCADE, null=True, blank=True,
        related_name="credito_custa",
    )
    # Só em `adiantamento`: o crédito que o cliente depositou/reembolsou
    # para cobrir esta custa.
    reembolsada_por = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reembolsa",
    )

    class Meta:
        verbose_name = "Custa Judicial"
        verbose_name_plural = "Custas Judiciais"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.descricao} — {self.valor}"

    def clean(self):
        if not processo_pertence_ao_cliente(self.cliente, self.processo):
            raise ValidationError({"processo": "O processo selecionado não pertence ao cliente informado."})

    @property
    def reembolsada(self):
        return self.reembolsada_por_id is not None

    @property
    def pode_reembolsar(self):
        return self.tipo == "adiantamento" and self.cliente_id is not None and not self.reembolsada


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

    # Honorário sucumbencial calculado (PDR-0029): valor-base por
    # percentual sobre a causa ou valor fixo, corrigido conforme o devedor
    # e o índice. O total nunca é gravado — é recalculado a cada leitura
    # (`services.calcular_honorario_sucumbencial`). `forma_condenacao`
    # vazio = honorário no modelo simples (valor estimado informado).
    FORMA_CONDENACAO_CHOICES = [
        ("percentual", "Percentual sobre o valor da causa"),
        ("fixo", "Valor fixo predeterminado"),
    ]
    DEVEDOR_CHOICES = [
        ("pessoa", "Pessoa física ou jurídica"),
        ("ente_estatal", "Ente estatal (União/Estado/Município)"),
    ]
    INDICE_CHOICES = [
        ("inpc", "INPC (padrão legal)"),
        ("igpm", "IGP-M (se previsto em contrato/sentença)"),
        ("selic", "Taxa Selic (se previsto em contrato/sentença)"),
    ]
    forma_condenacao = models.CharField(max_length=12, choices=FORMA_CONDENACAO_CHOICES, blank=True)
    percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valor_causa = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    valor_fixo = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    devedor_tipo = models.CharField(max_length=14, choices=DEVEDOR_CHOICES, blank=True)
    indice_correcao = models.CharField(max_length=6, choices=INDICE_CHOICES, blank=True)
    taxa_indice_mensal = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,
        help_text="Taxa mensal (%) do índice escolhido, informada manualmente.",
    )
    data_correcao = models.DateField(null=True, blank=True)
    data_juros = models.DateField(null=True, blank=True)
    exito_percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    exito_valor_ganho = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    exito_data_correcao = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Honorário"
        verbose_name_plural = "Honorários"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.valor_estimado}"

    @property
    def calculado(self):
        return bool(self.forma_condenacao)

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

    STATUS_ABERTOS = ("solicitada", "em_analise", "aprovada")

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
    data_pagamento = models.DateField(null=True, blank=True)
    pagamento_realizado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="solicitacoes_pagas",
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

    @property
    def vencida(self):
        return (
            self.status in self.STATUS_ABERTOS
            and self.vencimento is not None
            and self.vencimento < timezone.localdate()
        )

    def pode_transicionar_para(self, novo_status):
        return novo_status in self.TRANSICOES_VALIDAS.get(self.status, set())

    def avancar_para(self, novo_status, *, pago_por=None, comprovante_pagamento=None, usuario=None):
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
            self.data_pagamento = timezone.localdate()
            self.pagamento_realizado_por = usuario
            update_fields = ["status", "lancamento", "data_pagamento", "pagamento_realizado_por"]
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
