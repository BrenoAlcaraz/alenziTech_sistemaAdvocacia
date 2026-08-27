import hashlib

from django.core.exceptions import ValidationError
from django.db import models, transaction
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

    def save(self, *args, **kwargs):
        """Persiste o Processo e reconcilia seu Cliente como participante."""
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.cliente_id and self.responsavel_id:
                # Import local evita ciclo durante o carregamento dos models.
                from .services import garantir_participante_cliente

                garantir_participante_cliente(self)


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
    VINCULO_CHOICES = [
        ("cliente", "Cliente representado"),
        ("parte_contraria", "Parte contrária"),
        ("outro", "Outro vínculo"),
        ("legado", "Registro legado"),
    ]

    POSICAO_CHOICES = [
        ("polo_ativo", "Polo Ativo"),
        ("polo_passivo", "Polo Passivo"),
        ("terceiro", "Outros"),
        ("ministerio_publico", "Outros"),
        ("legado", "Outros — registro legado"),
    ]

    QUALIFICACAO_CHOICES = [
        ("autor", "Autor"),
        ("embargante", "Embargante"),
        ("recorrente", "Recorrente"),
        ("reu", "Réu"),
        ("embargado", "Embargado"),
        ("recorrido", "Recorrido"),
        ("terceiro_interessado", "Terceiro Interessado"),
        ("ministerio_publico", "Ministério Público"),
        ("amicus_curiae", "Amicus Curiae"),
        ("advogado_contrario_legado", "Advogado Contrário — legado"),
    ]

    ATUACAO_MP_CHOICES = [
        ("parte", "Parte do processo"),
        ("fiscal_ordem_juridica", "Fiscal da ordem jurídica"),
    ]

    POSICAO_POR_QUALIFICACAO = {
        "autor": "polo_ativo",
        "embargante": "polo_ativo",
        "recorrente": "polo_ativo",
        "reu": "polo_passivo",
        "embargado": "polo_passivo",
        "recorrido": "polo_passivo",
        "terceiro_interessado": "terceiro",
        "ministerio_publico": "ministerio_publico",
        "amicus_curiae": "terceiro",
    }

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="partes")
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participacoes_processuais",
    )
    nome = models.CharField(max_length=255, blank=True)
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    vinculo_escritorio = models.CharField(max_length=30, choices=VINCULO_CHOICES)
    posicao = models.CharField(
        max_length=30,
        choices=POSICAO_CHOICES,
        null=True,
        blank=True,
    )
    qualificacao = models.CharField(
        max_length=40,
        choices=QUALIFICACAO_CHOICES,
        null=True,
        blank=True,
    )
    atuacao_ministerio_publico = models.CharField(
        max_length=30,
        choices=ATUACAO_MP_CHOICES,
        blank=True,
    )
    tipo_legado = models.CharField(max_length=30, blank=True, editable=False)
    registro_legado = models.BooleanField(default=False, editable=False)
    classificacao_pendente = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = "Parte do Processo"
        verbose_name_plural = "Partes do Processo"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(vinculo_escritorio="cliente", cliente__isnull=False)
                    | (
                        ~models.Q(vinculo_escritorio="cliente")
                        & models.Q(cliente__isnull=True)
                    )
                ),
                name="processos_parte_vinculo_cliente_valido",
            ),
            models.UniqueConstraint(
                fields=["processo", "cliente"],
                condition=models.Q(cliente__isnull=False),
                name="processos_parte_cliente_unico",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        classificacao_pendente=True,
                        cliente__isnull=False,
                        vinculo_escritorio="cliente",
                        posicao__isnull=True,
                        qualificacao__isnull=True,
                        atuacao_ministerio_publico="",
                        registro_legado=False,
                        tipo_legado="",
                    )
                    | models.Q(classificacao_pendente=False)
                ),
                name="processos_parte_pendente_valida",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        classificacao_pendente=True,
                        posicao__isnull=True,
                        qualificacao__isnull=True,
                    )
                    | models.Q(posicao="polo_ativo", qualificacao="autor")
                    | models.Q(posicao="polo_ativo", qualificacao="embargante")
                    | models.Q(posicao="polo_ativo", qualificacao="recorrente")
                    | models.Q(posicao="polo_passivo", qualificacao="reu")
                    | models.Q(posicao="polo_passivo", qualificacao="embargado")
                    | models.Q(posicao="polo_passivo", qualificacao="recorrido")
                    | models.Q(posicao="terceiro", qualificacao="terceiro_interessado")
                    | models.Q(posicao="terceiro", qualificacao="amicus_curiae")
                    | models.Q(
                        posicao="ministerio_publico",
                        qualificacao="ministerio_publico",
                    )
                    | models.Q(
                        posicao="legado",
                        qualificacao="advogado_contrario_legado",
                    )
                ),
                name="processos_parte_taxonomia_valida",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        qualificacao="ministerio_publico",
                        atuacao_ministerio_publico__in=[
                            "parte",
                            "fiscal_ordem_juridica",
                        ],
                    )
                    | models.Q(
                        qualificacao__isnull=True,
                        atuacao_ministerio_publico="",
                    )
                    | models.Q(
                        qualificacao__in=[
                            "autor",
                            "embargante",
                            "recorrente",
                            "reu",
                            "embargado",
                            "recorrido",
                            "terceiro_interessado",
                            "amicus_curiae",
                            "advogado_contrario_legado",
                        ],
                        atuacao_ministerio_publico="",
                    )
                ),
                name="processos_parte_atuacao_mp_valida",
            ),
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            registro_legado=True,
                            classificacao_pendente=False,
                            cliente__isnull=True,
                            vinculo_escritorio="legado",
                            posicao="legado",
                            qualificacao="advogado_contrario_legado",
                        )
                        & ~models.Q(tipo_legado="")
                    )
                    | models.Q(
                        registro_legado=False,
                        vinculo_escritorio__in=[
                            "cliente",
                            "parte_contraria",
                            "outro",
                        ],
                    )
                    & ~models.Q(posicao="legado")
                    & ~models.Q(
                        qualificacao="advogado_contrario_legado"
                    )
                ),
                name="processos_parte_legado_valido",
            ),
        ]

    def __str__(self):
        qualificacao = self.get_qualificacao_display() if self.qualificacao else "pendente"
        return f"{self.nome_exibicao} ({qualificacao})"

    @property
    def nome_exibicao(self):
        if self.cliente_id:
            return self.cliente.nome_razao_social
        return self.nome

    @property
    def cpf_cnpj_exibicao(self):
        if self.cliente_id:
            return self.cliente.cpf_cnpj
        return self.cpf_cnpj

    def get_tipo_display(self):
        """Compatibilidade de apresentação com o antigo campo ``tipo``."""
        if self.classificacao_pendente:
            return "Classificação pendente"
        return self.get_qualificacao_display()

    @property
    def grupo_visual(self):
        if self.posicao == "polo_ativo":
            return "polo_ativo"
        if self.posicao == "polo_passivo":
            return "polo_passivo"
        return "outros"

    def clean(self):
        super().clean()
        erros = {}

        if (self.cliente_id is not None) != (self.vinculo_escritorio == "cliente"):
            erros["vinculo_escritorio"] = "O vínculo Cliente exige a FK de Cliente e vice-versa."

        if self.classificacao_pendente:
            if not self.cliente_id or self.vinculo_escritorio != "cliente":
                erros["classificacao_pendente"] = "Somente Cliente automático pode aguardar classificação."
            if self.posicao is not None or self.qualificacao is not None:
                erros["classificacao_pendente"] = "Participante pendente não possui posição ou qualificação."
            if self.atuacao_ministerio_publico:
                erros["atuacao_ministerio_publico"] = "Participante pendente não possui atuação do MP."
            if self.registro_legado:
                erros["registro_legado"] = "Registro legado não pode estar pendente."
            if self.tipo_legado:
                erros["tipo_legado"] = "Participante automático pendente não possui tipo legado."
        elif self.registro_legado:
            if (
                self.cliente_id is not None
                or self.vinculo_escritorio != "legado"
                or self.posicao != "legado"
                or self.qualificacao != "advogado_contrario_legado"
                or not self.tipo_legado
            ):
                erros["registro_legado"] = "O estado legado deve permanecer integralmente coerente."
        else:
            posicao_esperada = self.POSICAO_POR_QUALIFICACAO.get(self.qualificacao)
            if posicao_esperada is None or self.posicao != posicao_esperada:
                erros["qualificacao"] = "Posição e qualificação não correspondem à taxonomia aprovada."
            if self.vinculo_escritorio == "legado":
                erros["vinculo_escritorio"] = "Estado legado não pode ser criado como participante normal."
            if not self.cliente_id and not self.nome.strip():
                erros["nome"] = "Participante externo exige nome."

        if self.qualificacao == "ministerio_publico":
            if self.atuacao_ministerio_publico not in dict(self.ATUACAO_MP_CHOICES):
                erros["atuacao_ministerio_publico"] = "Informe a forma de atuação do Ministério Público."
        elif self.atuacao_ministerio_publico:
            erros["atuacao_ministerio_publico"] = "Somente o Ministério Público possui forma de atuação."

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        anterior = None
        update_fields = kwargs.get("update_fields")
        campos_classificacao = {
            "posicao",
            "qualificacao",
            "atuacao_ministerio_publico",
            "classificacao_pendente",
        }
        classificacao_persistida = (
            update_fields is None
            or bool(campos_classificacao.intersection(update_fields))
        )
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).values(
                "posicao",
                "qualificacao",
                "atuacao_ministerio_publico",
            ).first()

        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if anterior is not None and classificacao_persistida:
                estado_anterior = (
                    anterior["posicao"],
                    anterior["qualificacao"],
                    anterior["atuacao_ministerio_publico"],
                )
                estado_novo = (
                    self.posicao,
                    self.qualificacao,
                    self.atuacao_ministerio_publico,
                )
                if estado_anterior != estado_novo:
                    HistoricoClassificacaoParte.objects.create(
                        parte=self,
                        posicao_anterior=anterior["posicao"],
                        qualificacao_anterior=anterior["qualificacao"],
                        atuacao_mp_anterior=anterior["atuacao_ministerio_publico"],
                        posicao_nova=self.posicao,
                        qualificacao_nova=self.qualificacao,
                        atuacao_mp_nova=self.atuacao_ministerio_publico,
                        usuario=getattr(self, "_usuario_alteracao", None),
                    )


class HistoricoClassificacaoParte(models.Model):
    parte = models.ForeignKey(
        ParteProcesso,
        on_delete=models.CASCADE,
        related_name="historico_classificacao",
    )
    posicao_anterior = models.CharField(
        max_length=30,
        choices=ParteProcesso.POSICAO_CHOICES,
        null=True,
        blank=True,
    )
    qualificacao_anterior = models.CharField(
        max_length=40,
        choices=ParteProcesso.QUALIFICACAO_CHOICES,
        null=True,
        blank=True,
    )
    atuacao_mp_anterior = models.CharField(
        max_length=30,
        choices=ParteProcesso.ATUACAO_MP_CHOICES,
        blank=True,
    )
    posicao_nova = models.CharField(
        max_length=30,
        choices=ParteProcesso.POSICAO_CHOICES,
    )
    qualificacao_nova = models.CharField(
        max_length=40,
        choices=ParteProcesso.QUALIFICACAO_CHOICES,
    )
    atuacao_mp_nova = models.CharField(
        max_length=30,
        choices=ParteProcesso.ATUACAO_MP_CHOICES,
        blank=True,
    )
    alterado_em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alteracoes_classificacao_partes",
    )

    class Meta:
        verbose_name = "Histórico de classificação da parte"
        verbose_name_plural = "Históricos de classificação das partes"
        ordering = ["-alterado_em", "-pk"]


class AutoridadeProcessual(models.Model):
    TIPO_CHOICES = [("juiz", "Juiz")]

    processo = models.ForeignKey(
        Processo,
        on_delete=models.CASCADE,
        related_name="autoridades",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="juiz")
    nome = models.CharField(max_length=255)
    vara_orgao = models.CharField(max_length=255)
    observacao = models.TextField(blank=True)

    class Meta:
        verbose_name = "Autoridade processual"
        verbose_name_plural = "Autoridades processuais"

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class RepresentanteParte(models.Model):
    TIPO_CHOICES = [
        ("interno", "Advogado do escritório"),
        ("externo", "Advogado externo"),
    ]

    parte = models.ForeignKey(
        ParteProcesso,
        on_delete=models.CASCADE,
        related_name="representantes",
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="representacoes_processuais",
    )
    nome_externo = models.CharField(max_length=255, blank=True)
    oab = models.CharField(max_length=30, blank=True)
    uf_oab = models.CharField(max_length=2, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    fingerprint_externo = models.CharField(max_length=64, blank=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Representante da parte"
        verbose_name_plural = "Representantes das partes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        tipo="interno",
                        usuario__isnull=False,
                        nome_externo="",
                        oab="",
                        uf_oab="",
                        telefone="",
                        email="",
                        fingerprint_externo="",
                    )
                    | (
                        models.Q(tipo="externo", usuario__isnull=True)
                        & ~models.Q(nome_externo="")
                        & ~models.Q(oab="")
                        & ~models.Q(uf_oab="")
                        & ~models.Q(fingerprint_externo="")
                    )
                ),
                name="processos_representante_tipo_usuario_valido",
            ),
            models.UniqueConstraint(
                fields=["parte", "usuario"],
                condition=models.Q(tipo="interno"),
                name="processos_representante_interno_unico",
            ),
            models.UniqueConstraint(
                fields=["parte", "fingerprint_externo"],
                condition=models.Q(tipo="externo"),
                name="processos_representante_externo_unico",
            ),
        ]

    def normalizar_identidade_externa(self):
        self.nome_externo = " ".join((self.nome_externo or "").split())
        self.oab = "".join(
            caractere
            for caractere in (self.oab or "").strip().upper()
            if caractere.isalnum()
        )
        self.uf_oab = (self.uf_oab or "").strip().upper()
        self.telefone = "".join(caractere for caractere in (self.telefone or "") if caractere.isdigit())
        self.email = (self.email or "").strip().lower()
        identidade = "\x1f".join(
            [self.nome_externo.casefold(), self.oab, self.uf_oab, self.telefone, self.email]
        )
        self.fingerprint_externo = hashlib.sha256(identidade.encode("utf-8")).hexdigest()

    def clean(self):
        super().clean()
        erros = {}
        campos_externos = ("nome_externo", "oab", "uf_oab", "telefone", "email")
        if self.tipo == "interno":
            if not self.usuario_id:
                erros["usuario"] = "Representante interno exige um usuário."
            if any(getattr(self, campo) for campo in campos_externos):
                erros["tipo"] = "Representante interno não pode possuir dados externos."
            self.fingerprint_externo = ""
        elif self.tipo == "externo":
            if self.usuario_id:
                erros["usuario"] = "Representante externo não pode referenciar usuário interno."
            self.normalizar_identidade_externa()
            for campo in ("nome_externo", "oab", "uf_oab"):
                if not getattr(self, campo):
                    erros[campo] = "Campo obrigatório para representante externo."
        else:
            erros["tipo"] = "Tipo de representante inválido."
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        campos_fingerprint = {
            "tipo",
            "usuario",
            "nome_externo",
            "oab",
            "uf_oab",
            "telefone",
            "email",
        }
        if update_fields is not None and campos_fingerprint.intersection(
            update_fields
        ):
            kwargs["update_fields"] = set(update_fields) | {
                "fingerprint_externo"
            }
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def nome(self):
        if self.usuario_id:
            return self.usuario.get_full_name() or self.usuario.username
        return self.nome_externo

    @property
    def oab_formatada(self):
        if not self.oab:
            return ""
        return f"OAB/{self.uf_oab} {self.oab}" if self.uf_oab else f"OAB {self.oab}"

    def __str__(self):
        return self.nome
