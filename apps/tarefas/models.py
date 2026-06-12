from django.db import models
from django.contrib.auth.models import User
from apps.processos.models import Processo


class Tarefa(models.Model):
    STATUS_CHOICES = [
        ("a_fazer", "A fazer"),
        ("em_andamento", "Em andamento"),
        ("concluida", "Concluída"),
    ]

    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
    ]

    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="a_fazer")
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default="media")
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas")
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas")
    prazo = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"
        ordering = ["prazo", "-prioridade"]

    def __str__(self):
        return self.titulo
