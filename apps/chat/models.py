from django.db import models
from django.contrib.auth.models import User


class Conversa(models.Model):
    TIPO_INDIVIDUAL = "individual"
    TIPO_GRUPO = "grupo"
    TIPO_GLOBAL = "global"

    TIPO_CHOICES = [
        (TIPO_INDIVIDUAL, "Individual"),
        (TIPO_GRUPO, "Grupo"),
        (TIPO_GLOBAL, "Global"),
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
        constraints = [
            models.UniqueConstraint(
                fields=["tipo"],
                condition=models.Q(tipo="global"),
                name="uniq_conversa_global",
            ),
        ]

    def __str__(self):
        return self.titulo or f"Conversa #{self.pk}"

    def outro_participante(self, user):
        """Na conversa individual, o participante que não é `user` —
        None fora desse tipo ou se o outro já foi removido."""
        if self.tipo != self.TIPO_INDIVIDUAL:
            return None
        return self.participantes.exclude(pk=user.pk).first()

    def nome_para(self, user):
        """Rótulo de exibição desta conversa do ponto de vista de `user`
        — nome do outro participante na individual, título no grupo."""
        if self.tipo == self.TIPO_GRUPO:
            return self.titulo or f"Grupo #{self.pk}"
        if self.tipo == self.TIPO_INDIVIDUAL:
            outro = self.outro_participante(user)
            if outro is None:
                return "Conversa"
            return outro.get_full_name() or f"@{outro.username}"
        return self.titulo or "Sala Geral"


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
