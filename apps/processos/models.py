from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.clientes.models import Cliente


class Processo(models.Model):
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("suspenso", "Suspenso"),
        ("encerrado", "Encerrado"),
        ("arquivado", "Arquivado"),
    ]

    AREAS_CHOICES = [
        ("CÍVEL", "Cível"),
        ("CONSUMIDOR", "Consumidor"),
        ("TRABALHISTA", "Trabalhista"),
        ("SUCESSÕES", "Sucessões"),
        ("CRIMINAL", "Criminal"),
        ("ADMINISTRATIVO", "Administrativo"),
        ("TRIBUTÁRIO", "Tributário"),
        ("FAMÍLIA", "Família"),
        ("OUTRO", "Outro"),
    ]

    FASE_CHOICES = [
        ("conhecimento", "Conhecimento"),
        ("recursal", "Recursal"),
        ("cumprimento_sentenca", "Cumprimento de Sentença"),
        ("execucao_extrajudicial", "Execução Extrajudicial"),
        ("monitoria", "Monitória"),
        ("outro", "Outro"),
    ]

    GRATUIDADE_CHOICES = [
        ("nao_requerida", "Não Requerida"),
        ("requerida", "Requerida"),
        ("deferida", "Deferida"),
        ("indeferida", "Indeferida"),
        ("revogada", "Revogada"),
    ]

    titulo = models.CharField(max_length=255)
    numero = models.CharField(max_length=50, blank=True)
    area_direito = models.CharField(max_length=30, choices=AREAS_CHOICES, default="CÍVEL")
    instancia = models.CharField(max_length=50, blank=True, default="1ª Instância")
    vara_juizo = models.CharField(max_length=255, blank=True)
    valor_causa = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativo")
    fase = models.CharField(max_length=30, choices=FASE_CHOICES, default="conhecimento")
    gratuidade_justica_status = models.CharField(max_length=20, choices=GRATUIDADE_CHOICES, default="nao_requerida")
    data_distribuicao = models.DateField(null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="processos")
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="processos")
    departamento = models.ForeignKey(
        "accounts.Departamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processos",
        verbose_name="Departamento",
    )
    prazo_proximo = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Processo"
        verbose_name_plural = "Processos"
        ordering = ["-criado_em"]

    @property
    def prazo_urgente(self):
        if not self.prazo_proximo:
            return False
        return (self.prazo_proximo - timezone.localdate()).days <= 3

    @property
    def prazo_label(self):
        if not self.prazo_proximo:
            return "sem prazo"
        dias = (self.prazo_proximo - timezone.localdate()).days
        if dias < 0:
            return "prazo vencido"
        if dias == 0:
            return "hoje"
        if dias == 1:
            return "amanhã"
        return f"em {dias} dias"

    def __str__(self):
        return self.titulo


class MovimentacaoProcessual(models.Model):
    TIPO_CHOICES = [
        ("andamento", "Andamento"),
        ("prazo", "Prazo"),
        ("decisao", "Decisão"),
        ("audiencia", "Audiência"),
        ("outro", "Outro"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="movimentacoes")
    descricao = models.TextField()
    data = models.DateTimeField(default=timezone.now)
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="andamento")

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.processo.titulo} — {self.tipo}"


class ParteProcesso(models.Model):
    TIPO_CHOICES = [
        ("autor", "Autor"),
        ("reu", "Réu"),
        ("terceiro", "Terceiro"),
        ("advogado_contrario", "Advogado Contrário"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="partes")
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="autor")
    cpf_cnpj = models.CharField(max_length=18, blank=True)

    class Meta:
        verbose_name = "Parte do Processo"
        verbose_name_plural = "Partes do Processo"

    def __str__(self):
        return f"{self.nome} ({self.tipo})"
