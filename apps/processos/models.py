from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.clientes.models import Cliente
from apps.saas_tenants.storage import (
    PROTEGIDO,
    CaminhoArquivoTenant,
    StorageProtegido,
    nome_do_arquivo,
)


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
        ("CRIMINAL", "Penal"),
        ("ADMINISTRATIVO", "Administrativo"),
        ("TRIBUTÁRIO", "Tributário"),
        ("FAMÍLIA", "Família"),
        ("OUTRO", "Outro"),
    ]

    FASE_CHOICES = [
        ("conhecimento", "Conhecimento"),
        ("recursal", "Recursal"),
        ("cumprimento_sentenca", "Cumprimento de Sentença"),
        ("execucao_extrajudicial", "Execução"),
        ("outro", "Outro"),
    ]

    GRATUIDADE_CHOICES = [
        ("nao_requerida", "Não Requerida"),
        ("requerida", "Requerida"),
        ("deferida", "Deferida"),
        ("indeferida", "Indeferida"),
        ("revogada", "Revogada"),
    ]

    UF_CHOICES = [
        ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"),
        ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"),
        ("ES", "Espírito Santo"), ("GO", "Goiás"), ("MA", "Maranhão"),
        ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
        ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"), ("PE", "Pernambuco"),
        ("PI", "Piauí"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"),
        ("SC", "Santa Catarina"), ("SP", "São Paulo"), ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    ]

    RESULTADO_SENTENCA_CHOICES = [
        ("procedente", "Procedente"),
        ("parcialmente_procedente", "Parcialmente procedente"),
        ("improcedente", "Improcedente"),
    ]

    titulo = models.CharField(max_length=255)
    numero = models.CharField(max_length=50, blank=True)
    area_direito = models.CharField(max_length=30, choices=AREAS_CHOICES, default="CÍVEL")
    instancia = models.CharField(max_length=50, blank=True, default="1ª Instância")
    vara = models.CharField(max_length=255, blank=True)
    comarca = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=2, choices=UF_CHOICES, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    valor_causa = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativo")
    fase = models.CharField(max_length=30, choices=FASE_CHOICES, default="conhecimento")
    gratuidade_justica_status = models.CharField(max_length=20, choices=GRATUIDADE_CHOICES, default="nao_requerida")
    resultado_sentenca = models.CharField(
        max_length=30, choices=RESULTADO_SENTENCA_CHOICES, blank=True
    )
    data_distribuicao = models.DateField(null=True, blank=True)
    clientes = models.ManyToManyField(Cliente, blank=True, related_name="processos")
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


class Documento(models.Model):
    """Arquivo anexado a um Processo (procuração, petição, decisão,
    prova, contrato etc.) — storage protegido por tenant, mesmo padrão
    de Mensagem.anexo (Chat) e SolicitacaoFinanceira.anexo (Financeiro)."""

    TIPO_CHOICES = [
        ("peticao", "Petição"),
        ("decisao", "Decisão"),
        ("procuracao", "Procuração"),
        ("prova", "Prova"),
        ("contrato", "Contrato"),
        ("outro", "Outro"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="documentos")
    arquivo = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "processos/documentos"),
        storage=StorageProtegido(),
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="outro")
    descricao = models.CharField(max_length=255, blank=True)
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-enviado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {nome_do_arquivo(self.arquivo)}"

    def nome_do_documento(self):
        return nome_do_arquivo(self.arquivo)


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
        ("exequente", "Exequente"),
        ("requerente", "Requerente"),
        ("reclamante", "Reclamante"),
        ("agravante", "Agravante"),
        ("impugnante", "Impugnante"),
        ("reconvinte", "Reconvinte"),
        ("excipiente", "Excipiente"),
        ("impetrante", "Impetrante"),
        ("inventariante", "Inventariante"),
        ("reu", "Réu"),
        ("embargado", "Embargado"),
        ("recorrido", "Recorrido"),
        ("executado", "Executado"),
        ("requerido", "Requerido"),
        ("reclamado", "Reclamado"),
        ("agravado", "Agravado"),
        ("impugnado", "Impugnado"),
        ("reconvindo", "Reconvindo"),
        ("excepto", "Excepto"),
        ("impetrado", "Impetrado"),
        ("inventariado", "Inventariado"),
        ("terceiro_interessado", "Terceiro Interessado"),
        ("ministerio_publico", "Ministério Público"),
        ("juiz", "Juiz"),
    ]

    GRUPO_POR_PAPEL = {
        "autor": "polo_ativo",
        "embargante": "polo_ativo",
        "recorrente": "polo_ativo",
        "exequente": "polo_ativo",
        "requerente": "polo_ativo",
        "reclamante": "polo_ativo",
        "agravante": "polo_ativo",
        "impugnante": "polo_ativo",
        "reconvinte": "polo_ativo",
        "excipiente": "polo_ativo",
        "impetrante": "polo_ativo",
        "inventariante": "polo_ativo",
        "reu": "polo_passivo",
        "embargado": "polo_passivo",
        "recorrido": "polo_passivo",
        "executado": "polo_passivo",
        "requerido": "polo_passivo",
        "reclamado": "polo_passivo",
        "agravado": "polo_passivo",
        "impugnado": "polo_passivo",
        "reconvindo": "polo_passivo",
        "excepto": "polo_passivo",
        "impetrado": "polo_passivo",
        "inventariado": "polo_passivo",
        "terceiro_interessado": "outros",
        "ministerio_publico": "outros",
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


class Intimacao(models.Model):
    """
    Intimação vinculada a um Processo — painel "Intimações" do Dashboard
    (specs/dashboard-intimacoes.md). Criação/vínculo manual nesta
    versão; `origem` fica reservada para quando a leitura automática de
    e-mail existir (pendência futura, não implementada).
    """

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("manifestada", "Manifestada"),
    ]

    ORIGEM_CHOICES = [
        ("manual", "Manual"),
        ("email", "E-mail"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="intimacoes")
    motivo = models.CharField(max_length=255)
    prazo_manifestacao = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    origem = models.CharField(max_length=10, choices=ORIGEM_CHOICES, default="manual")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Intimação"
        verbose_name_plural = "Intimações"
        ordering = ["prazo_manifestacao"]

    def __str__(self):
        return f"{self.processo.titulo} — {self.motivo}"
