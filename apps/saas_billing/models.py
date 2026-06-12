from django.db import models
from apps.saas_tenants.models import Escritorio


class Plano(models.Model):
    """Planos de assinatura disponíveis na plataforma."""

    nome = models.CharField(max_length=100)
    preco_mensal = models.DecimalField(max_digits=8, decimal_places=2)
    limite_processos = models.IntegerField(
        help_text="Número máximo de processos permitidos. 0 = ilimitado."
    )
    limite_usuarios = models.IntegerField(
        help_text="Número máximo de usuários permitidos. 0 = ilimitado."
    )
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    # Futuramente: validar limites e bloquear criação quando excedidos.
    # Por ora apenas estrutura — sem bloqueio real.

    class Meta:
        verbose_name = "Plano"
        verbose_name_plural = "Planos"
        ordering = ["preco_mensal"]

    def __str__(self):
        return self.nome


class Assinatura(models.Model):
    """Assinatura ativa de um escritório em um plano."""

    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("suspenso", "Suspenso"),
        ("cancelado", "Cancelado"),
    ]

    escritorio = models.OneToOneField(
        Escritorio,
        on_delete=models.CASCADE,
        related_name="assinatura",
    )
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativo")
    inicio = models.DateField()
    proximo_vencimento = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"

    def __str__(self):
        return f"{self.escritorio.nome} — {self.plano.nome}"
