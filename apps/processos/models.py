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
        ("EMPRESARIAL", "Empresarial"),
        ("ELEITORAL", "Eleitoral"),
        ("MÉDICO", "Médico"),
        ("PREVIDENCIÁRIO", "Previdenciário"),
        ("DIGITAL", "Digital"),
        ("PROPRIEDADE_INTELECTUAL", "Propriedade Intelectual"),
        ("IMOBILIÁRIO", "Imobiliário"),
        ("DESPORTIVO", "Desportivo"),
        ("DIREITO_INTERNACIONAL", "Direito Internacional"),
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
    # Valores legados (`tipo` genérico, anterior ao catálogo por área).
    # "prazo" não está aqui — foi removido do enum e migrado para
    # `data_prazo` (migration 0019); os outros 4 continuam válidos só
    # para exibir o texto antigo de andamentos já existentes — não
    # aparecem no catálogo novo oferecido no formulário
    # (`catalogo_por_area`).
    TIPO_LEGADO = [
        ("andamento", "Andamento"),
        ("decisao", "Decisão"),
        ("audiencia", "Audiência"),
        ("outro", "Outro"),
    ]

    # Sempre visível em qualquer área, além do catálogo específico.
    TIPO_GENERICOS = [
        ("despacho", "Despacho"),
        ("decisao_interlocutoria", "Decisão interlocutória"),
        ("pericia", "Perícia"),
    ]

    TIPO_CIVEL = [
        ("peticao_inicial", "Petição inicial"),
        ("expedicao_de_mandado", "Expedição de mandado (citação, penhora, avaliação, levantamento de valores, carta precatória)"),
        ("retorno_de_citacao", "Retorno de citação"),
        ("intimacao", "Intimação"),
        ("contestacao", "Contestação"),
        ("reconvencao", "Reconvenção"),
        ("excecao_de_pre_executividade", "Exceção de pré-executividade"),
        ("replica", "Réplica"),
        ("quesitos_tecnicos", "Quesitos técnicos"),
        ("ata_de_audiencia", "Ata de audiência"),
        ("alegacoes_finais", "Alegações finais"),
        ("sentenca", "Sentença"),
        ("embargos_de_declaracao", "Embargos de declaração"),
        ("apelacao", "Apelação"),
        ("contrarrazoes", "Contrarrazões"),
        ("agravo_de_instrumento", "Agravo de instrumento"),
        ("agravo_interno", "Agravo interno"),
        ("recurso_adesivo", "Recurso adesivo"),
        ("acordao", "Acórdão"),
        ("recurso_especial", "Recurso especial (STJ)"),
        ("recurso_extraordinario", "Recurso extraordinário (STF)"),
        ("agravo_em_recurso_especial_extraordinario", "Agravo em recurso especial/extraordinário"),
        ("embargos_de_divergencia", "Embargos de divergência"),
        ("peticao", "Petição (mero expediente)"),
        ("juntada_de_documento", "Juntada de documento"),
        ("certidao", "Certidão"),
        ("homologacao", "Homologação (acordo, transação, cálculos)"),
        ("transito_em_julgado", "Trânsito em julgado"),
        ("cumprimento_de_sentenca_execucao", "Cumprimento de sentença/execução"),
        ("impugnacao", "Impugnação"),
        ("penhora_constricao_de_bens", "Penhora/constrição de bens"),
        ("arquivamento", "Arquivamento"),
        ("desarquivamento", "Desarquivamento"),
    ]

    TIPO_TRABALHISTA = [
        ("reclamacao_trabalhista", "Reclamação trabalhista (petição inicial)"),
        ("expedicao_de_mandado", "Expedição de mandado (citação, penhora, avaliação, levantamento de valores, carta precatória)"),
        ("retorno_de_citacao_notificacao_inicial", "Retorno de citação (notificação inicial)"),
        ("intimacao", "Intimação"),
        ("contestacao", "Contestação"),
        ("reconvencao", "Reconvenção"),
        ("replica", "Réplica"),
        ("quesitos_tecnicos", "Quesitos técnicos"),
        ("ata_de_audiencia", "Ata de audiência"),
        ("razoes_finais", "Razões finais"),
        ("sentenca", "Sentença"),
        ("embargos_de_declaracao", "Embargos de declaração"),
        ("recurso_ordinario", "Recurso ordinário (RO)"),
        ("contrarrazoes", "Contrarrazões"),
        ("agravo_de_instrumento", "Agravo de instrumento"),
        ("acordao", "Acórdão"),
        ("recurso_de_revista", "Recurso de revista (RR)"),
        ("embargos_ao_tst", "Embargos ao TST"),
        ("recurso_extraordinario", "Recurso extraordinário (STF)"),
        ("peticao", "Petição (mero expediente)"),
        ("juntada_de_documento", "Juntada de documento"),
        ("certidao", "Certidão"),
        ("homologacao", "Homologação (acordo, transação, cálculos)"),
        ("transito_em_julgado", "Trânsito em julgado"),
        ("liquidacao_de_sentenca", "Liquidação de sentença"),
        ("execucao", "Execução"),
        ("impugnacao", "Impugnação"),
        ("penhora_constricao_de_bens", "Penhora/constrição de bens"),
        ("agravo_de_peticao", "Agravo de petição"),
        ("habilitacao_de_credito", "Habilitação de crédito (falência/recuperação judicial do executado)"),
        ("arquivamento", "Arquivamento"),
        ("desarquivamento", "Desarquivamento"),
    ]

    TIPO_PENAL = [
        ("inquerito_policial_termo_circunstanciado", "Inquérito policial/termo circunstanciado"),
        ("denuncia_queixa_crime", "Denúncia/queixa-crime"),
        ("decisao_recebimento_rejeicao_denuncia", "Decisão (recebimento ou rejeição da denúncia/queixa)"),
        ("expedicao_de_mandado_penal", "Expedição de mandado (citação, busca e apreensão, prisão)"),
        ("retorno_de_citacao", "Retorno de citação"),
        ("intimacao", "Intimação"),
        ("resposta_a_acusacao", "Resposta à acusação"),
        ("replica_rito_juri", "Réplica (rito do Júri — art. 409 CPP)"),
        ("decisao_absolvicao_sumaria", "Decisão (absolvição sumária)"),
        ("quesitos_tecnicos", "Quesitos técnicos"),
        ("pronuncia_impronuncia", "Pronúncia/impronúncia (rito do Júri)"),
        ("ata_de_audiencia_instrucao_julgamento", "Ata de audiência (instrução e julgamento)"),
        ("interrogatorio", "Interrogatório"),
        ("alegacoes_finais", "Alegações finais"),
        ("sentenca", "Sentença"),
        ("embargos_de_declaracao", "Embargos de declaração"),
        ("apelacao", "Apelação"),
        ("recurso_em_sentido_estrito", "Recurso em sentido estrito (RESE)"),
        ("contrarrazoes", "Contrarrazões"),
        ("acordao", "Acórdão"),
        ("carta_testemunhavel", "Carta testemunhável"),
        ("habeas_corpus", "Habeas corpus"),
        ("recurso_especial", "Recurso especial (STJ)"),
        ("recurso_extraordinario", "Recurso extraordinário (STF)"),
        ("embargos_infringentes_ou_de_nulidade", "Embargos infringentes ou de nulidade"),
        ("revisao_criminal", "Revisão criminal (ação autônoma, não recurso técnico — incluída na fase recursal por praticidade)"),
        ("sessao_de_julgamento", "Sessão de julgamento (Plenário do Júri)"),
        ("peticao", "Petição (mero expediente)"),
        ("juntada_de_documento", "Juntada de documento"),
        ("certidao", "Certidão"),
        ("homologacao_penal", "Homologação (transação penal, suspensão condicional do processo)"),
        ("transito_em_julgado", "Trânsito em julgado"),
        ("guia_de_execucao_penal", "Guia de execução penal"),
        ("progressao_regressao_de_regime", "Progressão/regressão de regime"),
        ("livramento_condicional", "Livramento condicional"),
        ("remicao_de_pena", "Remição de pena"),
        ("agravo_em_execucao", "Agravo em execução"),
        ("extincao_da_punibilidade", "Extinção da punibilidade"),
        ("arquivamento_inquerito", "Arquivamento (do inquérito ou definitivo dos autos)"),
        ("desarquivamento", "Desarquivamento"),
    ]

    # Valor único por rótulo — mesmo texto em mais de uma lista (ex.:
    # "Intimação" em Cível/Trabalhista/Penal) reaproveita o mesmo choice;
    # dict preserva a ordem da primeira ocorrência.
    TIPO_CHOICES = list(
        dict(
            TIPO_LEGADO + TIPO_GENERICOS + TIPO_CIVEL + TIPO_TRABALHISTA + TIPO_PENAL
        ).items()
    )

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="movimentacoes")
    descricao = models.TextField()
    data = models.DateTimeField(default=timezone.now)
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=60, choices=TIPO_CHOICES, default="andamento")
    data_prazo = models.DateField(null=True, blank=True, verbose_name="Prazo")
    origem_prazo = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prazos_originados",
        verbose_name="Andamento de origem do prazo",
    )

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ["-data"]

    def __str__(self):
        return f"{self.processo.titulo} — {self.tipo}"

    @property
    def prazo_vencido(self):
        if not self.data_prazo:
            return False
        return self.data_prazo < timezone.localdate()

    @classmethod
    def catalogo_por_area(cls, processo):
        """(grupo, [(valor, rótulo), ...]) para o <select> de tipo do
        formulário de andamento — área do processo + Genéricos sempre
        visível. Consumidor/Sucessões/Administrativo/Tributário/Família/
        Outro caem no fallback Cível (sem catálogo próprio)."""
        if processo.area_direito == "TRABALHISTA":
            especifico = cls.TIPO_TRABALHISTA
        elif processo.area_direito == "CRIMINAL":
            especifico = cls.TIPO_PENAL
        else:
            especifico = cls.TIPO_CIVEL
        return [
            (processo.get_area_direito_display(), especifico),
            ("Genéricos", cls.TIPO_GENERICOS),
        ]


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
        ("perito", "Perito"),
        ("testemunha", "Testemunha"),
        ("assistente_acusacao", "Assistente de Acusação"),
    ]

    # Pares Polo Ativo/Polo Passivo com contraparte processual direta —
    # usado só para sugerir o cadastro da parte oposta (ver PAPEL_CONTRAPARTE
    # abaixo); papéis de "Outros" não têm contraparte.
    PARES_CONTRAPARTE = [
        ("autor", "reu"),
        ("embargante", "embargado"),
        ("recorrente", "recorrido"),
        ("exequente", "executado"),
        ("requerente", "requerido"),
        ("reclamante", "reclamado"),
        ("agravante", "agravado"),
        ("impugnante", "impugnado"),
        ("reconvinte", "reconvindo"),
        ("excipiente", "excepto"),
        ("impetrante", "impetrado"),
        ("inventariante", "inventariado"),
    ]

    PAPEL_CONTRAPARTE = dict(PARES_CONTRAPARTE) | {
        passivo: ativo for ativo, passivo in PARES_CONTRAPARTE
    }

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
        "perito": "outros",
        "testemunha": "outros",
        "assistente_acusacao": "outros",
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
