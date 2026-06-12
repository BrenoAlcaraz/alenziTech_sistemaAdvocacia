from django.db import models
from django.contrib.auth.models import User


class Conversa(models.Model):
    TIPO_CHOICES = [
        ("individual", "Individual"),
        ("grupo", "Grupo"),
    ]

    titulo = models.CharField(max_length=255, blank=True)
    participantes = models.ManyToManyField(User, related_name="conversas")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="individual")
    criada_em = models.DateTimeField(auto_now_add=True)

    # Futuramente: implementar WebSocket via Django Channels para mensagens em tempo real.
    # Por ora apenas estrutura de dados.

    class Meta:
        verbose_name = "Conversa"
        verbose_name_plural = "Conversas"
        ordering = ["-criada_em"]

    def __str__(self):
        return self.titulo or f"Conversa #{self.pk}"


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    conteudo = models.TextField()
    enviada_em = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        ordering = ["enviada_em"]

    def __str__(self):
        return f"{self.autor} — {self.conteudo[:50]}"
