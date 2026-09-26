from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from apps.accounts.models import ConviteDelegacao
from apps.processos.models import MovimentacaoProcessual, Processo
from apps.processos.services import processo_pertence_ao_cliente
from apps.clientes.models import Cliente


NATUREZA_AFAZER = "afazer"
NATUREZA_EVENTO = "evento"

TIPO_TAREFA = "tarefa"
TIPO_PRAZO = "prazo"
TIPO_PROTOCOLO = "protocolo"
TIPO_RETORNO = "retorno"
TIPO_AUDIENCIA = "audiencia"
TIPO_REUNIAO = "reuniao"
TIPO_PERICIA = "pericia"
TIPO_JULGAMENTO = "julgamento"

TIPOS_AFAZER = [TIPO_TAREFA, TIPO_PRAZO, TIPO_PROTOCOLO, TIPO_RETORNO]
TIPOS_EVENTO = [TIPO_AUDIENCIA, TIPO_REUNIAO, TIPO_PERICIA, TIPO_JULGAMENTO]

STATUS_A_FAZER = "a_fazer"
STATUS_EM_ANDAMENTO = "em_andamento"
STATUS_CONCLUIDO = "concluido"
STATUS_CANCELADO = "cancelado"
STATUS_ENCERRADOS = [STATUS_CONCLUIDO, STATUS_CANCELADO]

# Data para fazer padrão de um Prazo gerado pelo andamento: dias corridos
# antes da data fatal (PDR-0034).
DIAS_ANTECEDENCIA_PRAZO = 2


class ItemAgenda(models.Model):
    TIPO_CHOICES = [
        (TIPO_TAREFA, "Tarefa"),
        (TIPO_PRAZO, "Prazo"),
        (TIPO_PROTOCOLO, "Protocolo"),
        (TIPO_RETORNO, "Retorno"),
        (TIPO_AUDIENCIA, "Audiência"),
        (TIPO_REUNIAO, "Reunião"),
        (TIPO_PERICIA, "Perícia"),
        (TIPO_JULGAMENTO, "Julgamento"),
    ]

    STATUS_CHOICES = [
        (STATUS_A_FAZER, "A fazer"),
        (STATUS_EM_ANDAMENTO, "Em andamento"),
        (STATUS_CONCLUIDO, "Concluído"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
    ]

    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_TAREFA)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_A_FAZER)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default="media")
    # Afazer
    data_para_fazer = models.DateField(null=True, blank=True)
    hora_para_fazer = models.TimeField(null=True, blank=True)
    data_fatal = models.DateField(null=True, blank=True)
    # Evento
    dia_inteiro = models.BooleanField(default=False)
    data_hora_inicio = models.DateTimeField(null=True, blank=True)
    data_hora_fim = models.DateTimeField(null=True, blank=True)
    local = models.CharField(max_length=255, blank=True)

    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="itens_agenda")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="itens_agenda_criados")
    atribuidor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="itens_agenda_atribuidos")
    atribuido_em = models.DateTimeField(null=True, blank=True)
    participantes = models.ManyToManyField(
        User,
        through="ParticipanteItemAgenda",
        blank=True,
        related_name="itens_agenda_participando",
    )
    processo = models.ForeignKey(Processo, on_delete=models.SET_NULL, null=True, blank=True, related_name="itens_agenda")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="itens_agenda")
    # Prazo gerado pelo andamento: some junto com o andamento de origem.
    movimentacao_origem = models.OneToOneField(
        MovimentacaoProcessual, on_delete=models.CASCADE, null=True, blank=True, related_name="item_agenda",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    lembrete_enviado = models.BooleanField(default=False)
    cancelado_em = models.DateTimeField(null=True, blank=True)
    # Convite de delegação (PDR-0033): presente e pendente/recusado
    # enquanto o item não é uma atribuição ativa do responsável — ver
    # ItemAgenda.oculta_por_convite.
    convite_delegacao = models.OneToOneField(
        ConviteDelegacao, on_delete=models.SET_NULL, null=True, blank=True, related_name="item_agenda",
    )

    class Meta:
        verbose_name = "Item da agenda"
        verbose_name_plural = "Itens da agenda"
        ordering = ["data_hora_inicio", "data_para_fazer", "data_fatal"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(tipo=TIPO_PRAZO) | Q(data_fatal__isnull=False),
                name="agenda_prazo_exige_data_fatal",
            ),
            models.CheckConstraint(
                condition=~Q(tipo__in=TIPOS_EVENTO) | Q(data_hora_inicio__isnull=False),
                name="agenda_evento_exige_inicio",
            ),
            models.CheckConstraint(
                condition=~Q(tipo__in=TIPOS_EVENTO) | ~Q(status=STATUS_EM_ANDAMENTO),
                name="agenda_evento_sem_em_andamento",
            ),
        ]

    def __str__(self):
        return self.titulo

    @property
    def natureza(self):
        return NATUREZA_EVENTO if self.tipo in TIPOS_EVENTO else NATUREZA_AFAZER

    @property
    def eh_evento(self):
        return self.natureza == NATUREZA_EVENTO

    @property
    def gerado_pelo_processo(self):
        return self.movimentacao_origem_id is not None

    @property
    def sugerido(self):
        """Prazo de andamento trazido pelo acompanhamento automático e
        ainda não confirmado (PDR-0037)."""
        return self.gerado_pelo_processo and self.movimentacao_origem.sugerido

    @property
    def data_referencia(self):
        """Dia em que o item cai na agenda: início (evento), data para
        fazer ou, sem ela, a fatal (afazer); None em afazer sem data."""
        if self.eh_evento:
            return timezone.localdate(self.data_hora_inicio) if self.data_hora_inicio else None
        return self.data_para_fazer or self.data_fatal

    @property
    def atrasado(self):
        """Afazer aberto com data (fatal ou para fazer) no passado, ou
        evento ainda agendado cujo início já passou."""
        if self.status in STATUS_ENCERRADOS:
            return False
        if self.eh_evento:
            return self.data_hora_inicio is not None and self.data_hora_inicio < timezone.now()
        hoje = timezone.localdate()
        return any(data is not None and data < hoje for data in (self.data_fatal, self.data_para_fazer))

    @property
    def fatal_urgente(self):
        if not self.data_fatal:
            return False
        return (self.data_fatal - timezone.localdate()).days <= 3

    @property
    def fatal_label(self):
        if not self.data_fatal:
            return "sem prazo"
        dias = (self.data_fatal - timezone.localdate()).days
        if dias < 0:
            return "prazo vencido"
        if dias == 0:
            return "hoje"
        if dias == 1:
            return "amanhã"
        return f"em {dias} dias"

    def clean(self):
        erros = {}
        if not processo_pertence_ao_cliente(self.cliente, self.processo):
            erros["processo"] = "O processo selecionado não pertence ao cliente informado."
        if self.tipo == TIPO_PRAZO and not self.data_fatal:
            erros["data_fatal"] = "Prazo exige data fatal."
        if self.eh_evento and not self.data_hora_inicio:
            erros["data_hora_inicio"] = "Informe o início."
        if self.eh_evento and self.status == STATUS_EM_ANDAMENTO:
            # Chave `tipo` (não `status`): é a troca de tipo, no formulário,
            # que leva um item em andamento a virar evento.
            erros["tipo"] = "Evento não tem status Em andamento."
        if self.gerado_pelo_processo:
            if self.tipo != TIPO_PRAZO:
                erros["tipo"] = "Prazo gerado pelo andamento não muda de tipo."
            elif self.data_fatal != self.movimentacao_origem.data_prazo:
                erros["data_fatal"] = "A data fatal de um prazo gerado só muda no andamento."
        if erros:
            raise ValidationError(erros)

    @property
    def oculta_por_convite(self):
        """True enquanto o item não deve aparecer como atribuição ativa do
        responsável — convite de delegação pendente ou recusado."""
        return (
            self.convite_delegacao_id is not None
            and self.convite_delegacao.status != ConviteDelegacao.STATUS_ACEITO
        )

    def save(self, *args, **kwargs):
        if self.pk:
            data_anterior = ItemAgenda.objects.filter(pk=self.pk).values_list(
                "data_hora_inicio", flat=True
            ).first()
            if data_anterior is not None and data_anterior != self.data_hora_inicio:
                self.lembrete_enviado = False
        super().save(*args, **kwargs)

    @staticmethod
    def data_para_fazer_padrao(data_fatal):
        return data_fatal - timedelta(days=DIAS_ANTECEDENCIA_PRAZO)


class ParticipanteItemAgenda(models.Model):
    """
    Participação de um usuário (não responsável) num item — sempre dá
    visibilidade; em Evento, também confirmação de presença própria
    (PDR-0020), sem herdar a responsabilidade do item.
    """

    STATUS_PENDENTE = "pendente"
    STATUS_CONFIRMADO = "confirmado"
    STATUS_RECUSADO = "recusado"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_CONFIRMADO, "Confirmado"),
        (STATUS_RECUSADO, "Recusado"),
    ]

    item = models.ForeignKey(ItemAgenda, on_delete=models.CASCADE, related_name="participacoes")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="participacoes_agenda")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    lembrete_enviado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Participante do item da agenda"
        verbose_name_plural = "Participantes do item da agenda"
        constraints = [
            models.UniqueConstraint(
                fields=["item", "usuario"],
                name="agenda_participante_unico_por_item",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} em {self.item} ({self.status})"


class ReatribuicaoItemAgenda(models.Model):
    item = models.ForeignKey(ItemAgenda, on_delete=models.CASCADE, related_name="reatribuicoes")
    responsavel_anterior = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    responsavel_novo = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # Nulo quando a troca foi automática (responsável do processo mudou).
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reatribuição de item da agenda"
        verbose_name_plural = "Reatribuições de item da agenda"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.item_id}: {self.responsavel_anterior} → {self.responsavel_novo}"


class AvisoItemAgenda(models.Model):
    """Registro de aviso por data já enviado — garante uma notificação por
    item/destinatário/motivo. `referencia` é a data que motivou o aviso:
    se a data do item muda, o aviso da nova data volta a valer."""

    MOTIVO_FATAL_VESPERA = "fatal_vespera"
    MOTIVO_FATAL_HOJE = "fatal_hoje"
    MOTIVO_PARA_FAZER_VENCIDA = "para_fazer_vencida"
    MOTIVO_CHOICES = [
        (MOTIVO_FATAL_VESPERA, "Véspera da data fatal"),
        (MOTIVO_FATAL_HOJE, "Dia da data fatal"),
        (MOTIVO_PARA_FAZER_VENCIDA, "Data para fazer vencida"),
    ]

    item = models.ForeignKey(ItemAgenda, on_delete=models.CASCADE, related_name="avisos")
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES)
    referencia = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aviso de item da agenda"
        verbose_name_plural = "Avisos de item da agenda"
        constraints = [
            models.UniqueConstraint(
                fields=["item", "destinatario", "motivo", "referencia"],
                name="agenda_aviso_unico_por_motivo",
            ),
        ]

    def __str__(self):
        return f"{self.item_id} → {self.destinatario_id}: {self.motivo} ({self.referencia})"
