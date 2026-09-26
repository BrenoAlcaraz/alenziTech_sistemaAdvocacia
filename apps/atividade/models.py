from django.conf import settings
from django.db import models


class LogAtividade(models.Model):
    """
    Log de atividade genérico — base do Painel do gestor
    (specs/dashboard-painel-do-gestor.md). Cobre login/logout e ações
    de escrita de Processos, Tarefas, Agenda, Financeiro, Clientes e
    Configurações (specs/atividade-ampliar-catalogo.md).

    Só leitura pela interface — nunca editável/removível.
    """

    TIPO_CHOICES = [
        ("login", "Login no sistema"),
        ("logout", "Logout do sistema"),
        ("processo_criado", "Criou processo"),
        ("processo_editado", "Editou processo"),
        ("processo_arquivado", "Arquivou processo"),
        ("processo_reaberto", "Reabriu processo"),
        ("processo_excluido", "Excluiu processo"),
        ("processo_andamento_adicionado", "Adicionou andamento"),
        ("processo_parte_adicionada", "Adicionou parte"),
        ("processo_parte_editada", "Editou parte"),
        ("processo_representante_adicionado", "Adicionou representante de parte"),
        ("processo_representante_removido", "Removeu representante de parte"),
        ("processo_responsavel_atribuido", "Atribuiu responsável"),
        ("processo_responsavel_removido", "Removeu responsável"),
        ("processo_apenso_adicionado", "Adicionou apenso"),
        ("processo_apenso_removido", "Removeu apenso"),
        ("processo_integrante_adicionado", "Adicionou integrante habilitado"),
        ("processo_integrante_removido", "Removeu integrante habilitado"),
        ("processo_documento_adicionado", "Adicionou documento"),
        ("processo_documento_excluido", "Excluiu documento"),
        ("processo_sugestao_confirmada", "Confirmou andamento sugerido"),
        ("processo_sugestao_rejeitada", "Rejeitou andamento sugerido"),
        ("processo_sugestao_editada", "Editou andamento sugerido"),
        ("tarefa_criada", "Criou tarefa"),
        ("tarefa_editada", "Editou tarefa"),
        ("tarefa_reatribuida", "Reatribuiu tarefa"),
        ("tarefa_iniciada", "Iniciou tarefa"),
        ("tarefa_concluida", "Concluiu tarefa"),
        ("tarefa_reaberta", "Reabriu tarefa"),
        ("tarefa_cancelada", "Cancelou tarefa"),
        ("tarefa_excluida", "Excluiu tarefa"),
        ("tarefa_participante_adicionado", "Adicionou participante da tarefa"),
        ("tarefa_participante_removido", "Removeu participante da tarefa"),
        ("compromisso_criado", "Criou compromisso"),
        ("compromisso_editado", "Editou compromisso"),
        ("compromisso_concluido", "Concluiu compromisso"),
        ("compromisso_cancelado", "Cancelou compromisso"),
        ("compromisso_reaberto", "Reabriu compromisso"),
        ("compromisso_excluido", "Excluiu compromisso"),
        ("compromisso_participante_adicionado", "Adicionou participante do compromisso"),
        ("compromisso_participante_removido", "Removeu participante do compromisso"),
        ("lancamento_criado", "Criou lançamento financeiro"),
        ("lancamento_editado", "Editou lançamento financeiro"),
        ("lancamento_pago", "Marcou lançamento como pago"),
        ("lancamento_cancelado", "Cancelou lançamento financeiro"),
        ("lancamento_recorrencia_cancelada", "Cancelou recorrência de lançamento"),
        ("lancamento_reaberto", "Reabriu lançamento financeiro"),
        ("lancamento_excluido", "Excluiu lançamento financeiro"),
        ("custa_criada", "Criou custa judicial"),
        ("custa_creditada", "Creditou custa a cliente"),
        ("custa_reembolsada", "Reembolsou custa"),
        ("honorario_criado", "Criou honorário"),
        ("honorario_editado", "Editou honorário"),
        ("honorario_recebido", "Confirmou recebimento de honorário"),
        ("honorario_cancelado", "Cancelou honorário"),
        ("solicitacao_criada", "Criou solicitação financeira"),
        ("solicitacao_editada", "Editou solicitação financeira"),
        ("solicitacao_processada", "Alterou status de solicitação financeira"),
        ("cliente_criado", "Criou cliente"),
        ("cliente_editado", "Editou cliente"),
        ("cliente_desativado", "Desativou cliente"),
        ("cliente_reativado", "Reativou cliente"),
        ("cliente_excluido", "Excluiu cliente"),
        ("cliente_documento_adicionado", "Adicionou documento do cliente"),
        ("cliente_documento_excluido", "Excluiu documento do cliente"),
        ("cliente_procuracao_gerada", "Gerou procuração"),
        ("usuario_criado", "Criou usuário"),
        ("usuario_excluido", "Excluiu usuário"),
        ("equipe_criada", "Criou equipe"),
        ("equipe_editada", "Editou equipe"),
        ("equipe_membro_adicionado", "Adicionou membro da equipe"),
        ("equipe_membro_removido", "Removeu membro da equipe"),
        ("equipe_gerente_alterado", "Alterou gerente da equipe"),
        ("papel_criado", "Criou papel de acesso"),
        ("papel_editado", "Editou papel de acesso"),
        ("papel_usuario_atribuido", "Atribuiu usuário a papel de acesso"),
        ("papel_usuario_removido", "Removeu usuário de papel de acesso"),
        ("permissao_papel_editada", "Editou permissões do papel de acesso"),
        ("permissao_usuario_editada", "Editou permissões individuais do usuário"),
        ("escritorio_editado", "Editou dados do escritório"),
        ("escritorio_identidade_visual_editada", "Editou identidade visual do escritório"),
    ]

    # login/logout ficam registrados, mas não contam como ação produtiva
    # nos contadores do Painel do gestor (specs/atividade-ampliar-catalogo.md).
    TIPOS_NAO_PRODUTIVOS = {"login", "logout"}

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
