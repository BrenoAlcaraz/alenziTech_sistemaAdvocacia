from django.conf import settings
from django.db import models


class LogAtividade(models.Model):
    """
    Log de atividade genérico — base do Painel do gestor
    (specs/dashboard-painel-do-gestor.md). Fase 1 cobre só login e
    ações de escrita do módulo Processos; outros módulos entram depois,
    reaproveitando este mesmo modelo.

    Só leitura pela interface — nunca editável/removível.
    """

    TIPO_CHOICES = [
        ("login", "Login no sistema"),
        ("processo_criado", "Criou processo"),
        ("processo_editado", "Editou processo"),
        ("processo_arquivado", "Arquivou processo"),
        ("processo_reaberto", "Reabriu processo"),
        ("processo_andamento_adicionado", "Adicionou andamento"),
        ("processo_parte_adicionada", "Adicionou parte"),
        ("processo_parte_editada", "Editou parte"),
        ("processo_apenso_adicionado", "Adicionou apenso"),
        ("processo_apenso_removido", "Removeu apenso"),
        ("processo_integrante_adicionado", "Adicionou integrante habilitado"),
        ("processo_integrante_removido", "Removeu integrante habilitado"),
        ("processo_documento_adicionado", "Adicionou documento"),
        ("processo_documento_excluido", "Excluiu documento"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="logs_atividade"
    )
    tipo = models.CharField(max_length=40, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=255)
    processo = models.ForeignKey(
        "processos.Processo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_atividade",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de atividade"
        verbose_name_plural = "Logs de atividade"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.usuario} — {self.descricao}"
