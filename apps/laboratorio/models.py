from django.db import models
from django.contrib.auth.models import User


class CasoLaboratorio(models.Model):
    TIPO_PECA_CHOICES = [
        ("peticao_inicial", "Petição inicial"),
        ("contestacao", "Contestação"),
        ("recurso", "Recurso"),
        ("contrato", "Contrato"),
        ("notificacao", "Notificação extrajudicial"),
        ("outro", "Outro"),
    ]

    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("processando", "Processando"),  # reservado para IA futura
        ("concluido", "Concluído"),
    ]

    tipo_peca = models.CharField(max_length=30, choices=TIPO_PECA_CHOICES)
    area_direito = models.CharField(max_length=50)
    tipo_cliente = models.CharField(max_length=2, choices=[("PF", "Pessoa Física"), ("PJ", "Pessoa Jurídica")])
    nome_cliente = models.CharField(max_length=255)
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="rascunho")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Futuramente: campo "resultado" receberá o texto gerado pela IA.
    # Por ora apenas estrutura de dados e placeholder visual.

    class Meta:
        verbose_name = "Caso – Laboratório"
        verbose_name_plural = "Casos – Laboratório"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.tipo_peca} — {self.nome_cliente}"
