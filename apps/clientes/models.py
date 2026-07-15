from django.conf import settings
from django.db import models


class Cliente(models.Model):
    TIPO_CHOICES = [
        ("PF", "Pessoa Física"),
        ("PJ", "Pessoa Jurídica"),
    ]

    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default="PF")
    nome_razao_social = models.CharField(max_length=255)
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    endereco = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_responsaveis",
        verbose_name="Responsável",
    )
    departamento = models.ForeignKey(
        "accounts.Departamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes",
        verbose_name="Departamento",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nome_razao_social"]

    def __str__(self):
        return self.nome_razao_social

    def iniciais(self):
        partes = self.nome_razao_social.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[1][0]}".upper()
        return self.nome_razao_social[:2].upper()
