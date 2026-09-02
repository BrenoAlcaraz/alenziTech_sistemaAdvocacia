from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.clientes.models import Cliente


class Processo(models.Model):
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("suspenso", "Suspenso"),
        ("encerrado", "Encerrado"),
        ("arquivado", "Arquivado"),
    ]

    AREAS_CHOICES = [
        ("CÍVEL", "Cível"),
        ("CONSUMIDOR", "Consumidor"),
        ("TRABALHISTA", "Trabalhista"),
        ("SUCESSÕES", "Sucessões"),
        ("CRIMINAL", "Criminal"),
        ("ADMINISTRATIVO", "Administrativo"),
        ("TRIBUTÁRIO", "Tributário"),
        ("FAMÍLIA", "Família"),
        ("OUTRO", "Outro"),
    ]

    FASE_CHOICES = [
        ("conhecimento", "Conhecimento"),
        ("recursal", "Recursal"),
        ("cumprimento_sentenca", "Cumprimento de Sentença"),
        ("execucao_extrajudicial", "Execução Extrajudicial"),
        ("monitoria", "Monitória"),
        ("outro", "Outro"),
    ]

    GRATUIDADE_CHOICES = [
        ("nao_requerida", "Não Requerida"),
        ("requerida", "Requerida"),
        ("deferida", "Deferida"),
        ("indeferida", "Indeferida"),
        ("revogada", "Revogada"),
    ]

    titulo = models.CharField(max_length=255)
    numero = models.CharField(max_length=50, blank=True)
    area_direito = models.CharField(max_length=30, choices=AREAS_CHOICES, default="CÍVEL")
    instancia = models.CharField(max_length=50, blank=True, default="1ª Instância")
    vara_juizo = models.CharField(max_length=255, blank=True)
    valor_causa = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativo")
    fase = models.CharField(max_length=30, choices=FASE_CHOICES, default="conhecimento")
    gratuidade_justica_status = models.CharField(max_length=20, choices=GRATUIDADE_CHOICES, default="nao_requerida")
    data_distribuicao = models.DateField(null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="processos")
    responsavel = models.ForeignKey(User, on_delete=models.PROTECT, related_name="processos")
    equipe = models.ForeignKey(
        "accounts.Equipe",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processos",
        verbose_name="Equipe",
    )
    integrantes_habilitados = models.ManyToManyField(
        User,
        blank=True,
        related_name="processos_integrante_habilitado",
        verbose_name="Integrantes habilitados",
    )
    prazo_proximo = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Processo"
        verbose_name_plural = "Processos"
        ordering = ["-criado_em"]

    @property
    def prazo_urgente(self):
        if not self.prazo_proximo:
            return False
        return (self.prazo_proximo - timezone.localdate()).days <= 3

    @property
    def prazo_label(self):
        if not self.prazo_proximo:
            return "sem prazo"
        dias = (self.prazo_proximo - timezone.localdate()).days
        if dias < 0:
            return "prazo vencido"
        if dias == 0:
            return "hoje"
        if dias == 1:
            return "amanhã"
        return f"em {dias} dias"

    def __str__(self):
        return self.titulo


class VinculoProcessoApenso(models.Model):
    """Vínculo simétrico entre dois Processos, armazenado uma única vez."""

    processo_menor = models.ForeignKey(
        Processo,
        on_delete=models.CASCADE,
        related_name="vinculos_apensos_como_menor",
    )
    processo_maior = models.ForeignKey(
        Processo,
        on_delete=models.CASCADE,
        related_name="vinculos_apensos_como_maior",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vínculo de processo apenso"
        verbose_name_plural = "Vínculos de processos apensos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    processo_menor_id__lt=models.F("processo_maior_id")
                ),
                name="processos_apenso_ordem_valida",
            ),
            models.UniqueConstraint(
                fields=["processo_menor", "processo_maior"],
                name="processos_apenso_par_unico",
            ),
        ]

    def normalizar_par(self):
        if self.processo_menor_id is None or self.processo_maior_id is None:
            return
        if self.processo_menor_id == self.processo_maior_id:
            raise ValidationError(
                {"processo_maior": "Um Processo não pode ser apenso a ele mesmo."}
            )
        if self.processo_menor_id > self.processo_maior_id:
            self.processo_menor_id, self.processo_maior_id = (
                self.processo_maior_id,
                self.processo_menor_id,
            )

    def clean(self):
        super().clean()
        self.normalizar_par()

    def save(self, *args, **kwargs):
        self.normalizar_par()
        # A constraint permanece a autoridade contra concorrência e bypass.
        self.full_clean(validate_unique=False, validate_constraints=False)
        super().save(*args, **kwargs)

    def outro_processo(self, processo):
        if processo.pk == self.processo_menor_id:
            return self.processo_maior
        if processo.pk == self.processo_maior_id:
            return self.processo_menor
        raise ValueError("O Processo informado não pertence a este vínculo.")

    def __str__(self):
        return f"{self.processo_menor} ↔ {self.processo_maior}"


class MovimentacaoProcessual(models.Model):
    TIPO_CHOICES = [
        ("andamento", "Andamento"),
        ("prazo", "Prazo"),
        ("decisao", "Decisão"),
        ("audiencia", "Audiência"),
        ("outro", "Outro"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="movimentacoes")
    descricao = models.TextField()
    data = models.DateTimeField(default=timezone.now)
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="andamento")

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.processo.titulo} — {self.tipo}"


class ParteProcesso(models.Model):
    """Parte do processo — modelo simplificado (PDR-0013).

    Um único campo de papel processual substitui a separação anterior
    entre vínculo, posição estrutural e qualificação (PDR-0001/PDR-0011).
    Advogado é texto livre associado diretamente à parte, no máximo um
    por parte — sem entidade normalizada própria.
    """

    PAPEL_CHOICES = [
        ("autor", "Autor"),
        ("embargante", "Embargante"),
        ("recorrente", "Recorrente"),
        ("reu", "Réu"),
        ("embargado", "Embargado"),
        ("recorrido", "Recorrido"),
        ("terceiro_interessado", "Terceiro Interessado"),
        ("ministerio_publico", "Ministério Público"),
        ("amicus_curiae", "Amicus Curiae"),
        ("juiz", "Juiz"),
    ]

    GRUPO_POR_PAPEL = {
        "autor": "polo_ativo",
        "embargante": "polo_ativo",
        "recorrente": "polo_ativo",
        "reu": "polo_passivo",
        "embargado": "polo_passivo",
        "recorrido": "polo_passivo",
        "terceiro_interessado": "outros",
        "ministerio_publico": "outros",
        "amicus_curiae": "outros",
        "juiz": "outros",
    }

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="partes")
    papel = models.CharField(max_length=30, choices=PAPEL_CHOICES)
    nome = models.CharField(max_length=255)
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    advogado_nome = models.CharField(max_length=255, blank=True)
    advogado_oab = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "Parte do Processo"
        verbose_name_plural = "Partes do Processo"

    def __str__(self):
        return f"{self.nome} ({self.get_papel_display()})"

    @property
    def grupo_visual(self):
        return self.GRUPO_POR_PAPEL[self.papel]

    def clean(self):
        super().clean()
        if not self.nome.strip():
            raise ValidationError({"nome": "Informe o nome da parte."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
