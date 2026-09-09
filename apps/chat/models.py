from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.saas_tenants.storage import (
    CaminhoArquivoTenant,
    PROTEGIDO,
    StorageProtegido,
)


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

    def marcar_lida_para(self, usuario):
        """Atualiza o marco de leitura desta conversa para `usuario` —
        não afeta o marco dos demais participantes."""
        LeituraConversa.objects.update_or_create(
            conversa=self, usuario=usuario, defaults={"lida_em": timezone.now()}
        )

    def tem_mensagem_nao_lida_para(self, usuario):
        """Há mensagem de outro participante após o marco de leitura de
        `usuario` nesta conversa — ou nunca lida, se o marco não existe."""
        mensagens_de_outros = self.mensagens.exclude(autor=usuario)
        leitura = self.leituras.filter(usuario=usuario).first()
        if leitura is not None:
            mensagens_de_outros = mensagens_de_outros.filter(enviada_em__gt=leitura.lida_em)
        return mensagens_de_outros.exists()


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    conteudo = models.TextField(blank=True)
    anexo = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "chat/mensagens"),
        storage=StorageProtegido(),
        blank=True,
    )
    enviada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        ordering = ["enviada_em"]

    def __str__(self):
        return f"{self.autor} — {self.conteudo[:50]}"

    def nome_do_anexo(self):
        return self.anexo.name.rsplit("/", 1)[-1] if self.anexo else ""


class LeituraConversa(models.Model):
    """Marco de leitura de uma Conversa por usuário — cada participante
    tem o próprio marco, independente dos demais (necessário para
    conversa em grupo com mais de 2 participantes)."""

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="leituras")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="leituras_conversas")
    lida_em = models.DateTimeField()

    class Meta:
        verbose_name = "Leitura da conversa"
        verbose_name_plural = "Leituras da conversa"
        constraints = [
            models.UniqueConstraint(
                fields=["conversa", "usuario"],
                name="chat_leitura_unica_por_usuario",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} leu {self.conversa} em {self.lida_em}"
