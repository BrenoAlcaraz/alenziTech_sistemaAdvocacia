from django.db import models
from django.contrib.auth.models import User


class Notificacao(models.Model):
    destinatario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="notificacoes")
    mensagem = models.CharField(max_length=255)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.destinatario} — {self.mensagem[:50]}"
