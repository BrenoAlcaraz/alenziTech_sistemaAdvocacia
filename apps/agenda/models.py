from django.db import models
from django.contrib.auth.models import User
from apps.processos.models import Processo


class Compromisso(models.Model):
    TIPO_CHOICES = [
        ("audiencia", "Audiência"),
        ("prazo", "Prazo"),
        ("reuniao", "Reunião"),
        ("outro", "Outro"),
    ]

    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="outro")
    data_hora_inicio = models.DateTimeField()
    data_hora_fim = models.DateTimeField(null=True, blank=True)
    local = models.CharField(max_length=255, blank=True)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="compromissos")
    participantes = models.ManyToManyField(User, blank=True, related_name="compromissos_participando")
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True, related_name="compromissos")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compromisso"
        verbose_name_plural = "Compromissos"
        ordering = ["data_hora_inicio"]

    def __str__(self):
        return self.titulo
