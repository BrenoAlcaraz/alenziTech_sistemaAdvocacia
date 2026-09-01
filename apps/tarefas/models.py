from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.processos.models import Processo
from apps.clientes.models import Cliente


class Tarefa(models.Model):
    STATUS_CHOICES = [
        ("a_fazer", "A fazer"),
        ("em_andamento", "Em andamento"),
        ("concluida", "Concluída"),
        ("cancelada", "Cancelada"),
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
    criador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas_criadas")
    atribuidor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas_atribuidas")
    atribuido_em = models.DateTimeField(null=True, blank=True)
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas")
    prazo = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"
        ordering = ["prazo", "-prioridade"]

    @property
    def prazo_urgente(self):
        if not self.prazo:
            return False
        return (self.prazo - timezone.localdate()).days <= 3

    @property
    def prazo_label(self):
        if not self.prazo:
            return "sem prazo"
        dias = (self.prazo - timezone.localdate()).days
        if dias < 0:
            return "prazo vencido"
        if dias == 0:
            return "hoje"
        if dias == 1:
            return "amanhã"
        return f"em {dias} dias"

    def __str__(self):
        return self.titulo


class ReatribuicaoTarefa(models.Model):
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name="reatribuicoes")
    responsavel_anterior = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    responsavel_novo = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reatribuição de tarefa"
        verbose_name_plural = "Reatribuições de tarefa"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.tarefa_id}: {self.responsavel_anterior} → {self.responsavel_novo}"
