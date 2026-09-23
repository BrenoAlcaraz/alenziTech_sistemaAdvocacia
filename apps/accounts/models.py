from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone

from apps.saas_tenants.storage import (
    CaminhoArquivoTenant,
    PROTEGIDO,
    StorageProtegido,
)

from .permissoes_constants import (
    CODIGO_PRESET_LIMITADO,
    MODULO_CHOICES,
    MODULO_HABILITACAO_CHOICES,
    NIVEL_CHOICES,
    ITEM_CHOICES,
    NIVEIS_POR_MODULO,
    ITENS_POR_MODULO,
)


class SequenciaCodigoInterno(models.Model):
    """
    Último número emitido do código interno (P/C/U) de cada entidade.
    Uma linha por entidade no schema do tenant — a sequência é por
    escritório. Guardado à parte (e não derivado do maior código
    existente) para que um número excluído nunca volte a ser emitido.
    """

    PROCESSO = "processo"
    CLIENTE = "cliente"
    USUARIO = "usuario"
    ENTIDADE_CHOICES = [
        (PROCESSO, "Processo"),
        (CLIENTE, "Cliente"),
        (USUARIO, "Usuário"),
    ]

    entidade = models.CharField(max_length=20, choices=ENTIDADE_CHOICES, unique=True)
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Sequência de código interno"
        verbose_name_plural = "Sequências de código interno"

    def __str__(self):
        return f"{self.get_entidade_display()}: {self.ultimo_numero}"

    @classmethod
    def proximo(cls, entidade):
        # select_for_update serializa criações concorrentes da mesma
        # entidade até o fim da transação, evitando número repetido.
        with transaction.atomic():
            sequencia, _ = cls.objects.select_for_update().get_or_create(entidade=entidade)
            sequencia.ultimo_numero += 1
            sequencia.save(update_fields=["ultimo_numero"])
            return sequencia.ultimo_numero

    @classmethod
    def devolver(cls, entidade, numero):
        """Desfaz a emissão de `numero` só se ele for o último emitido.
        Caso do Administrador: o perfil nasce comum (signal de User) e só
        depois é marcado como Administrador, que não consome número."""
        with transaction.atomic():
            cls.objects.select_for_update().filter(
                entidade=entidade, ultimo_numero=numero,
            ).update(ultimo_numero=numero - 1)


class PerfilUsuario(models.Model):
    """
    Dados extras do usuário dentro de um tenant específico.
    Usa o User padrão do Django via OneToOne.
    Cargo é apenas descritivo — não controla permissão.
    Permissões vêm dos papéis de acesso (PapelAcesso).
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    nome_completo = models.CharField(max_length=255, blank=True)
    cargo = models.CharField(
        max_length=100,
        blank=True,
        help_text="Apenas descritivo. Não controla permissões.",
    )
    avatar = models.ImageField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "accounts/avatares"),
        storage=StorageProtegido(),
        blank=True,
        null=True,
    )
    is_admin_escritorio = models.BooleanField(
        default=False,
        help_text="Indica se este usuário é administrador do escritório.",
    )
    numero_interno = models.PositiveIntegerField(
        null=True, blank=True, unique=True, editable=False,
        help_text="Número do código interno U. Vazio para o Administrador (ADM).",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"
        constraints = [
            models.UniqueConstraint(
                fields=["is_admin_escritorio"],
                condition=Q(is_admin_escritorio=True),
                name="uniq_perfil_tenant_admin",
            )
        ]

    def __str__(self):
        return self.nome_completo or self.user.username

    @property
    def codigo(self):
        if self.is_admin_escritorio:
            return "ADM"
        return f"U{self.numero_interno}" if self.numero_interno else ""

    def save(self, *args, **kwargs):
        numero_anterior = self.numero_interno
        if self.is_admin_escritorio:
            if self.numero_interno is not None:
                SequenciaCodigoInterno.devolver(SequenciaCodigoInterno.USUARIO, self.numero_interno)
                self.numero_interno = None
        elif self.numero_interno is None:
            self.numero_interno = SequenciaCodigoInterno.proximo(SequenciaCodigoInterno.USUARIO)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and self.numero_interno != numero_anterior:
            kwargs["update_fields"] = {*update_fields, "numero_interno"}
        super().save(*args, **kwargs)

    def iniciais(self):
        """Retorna iniciais para o avatar visual."""
        partes = self.nome_completo.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[-1][0]}".upper()
        return self.user.username[:2].upper()


class Equipe(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Equipe"
        verbose_name_plural = "Equipes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class MembroEquipe(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membros_equipe",
    )
    equipe = models.ForeignKey(
        Equipe,
        on_delete=models.CASCADE,
        related_name="membros",
    )
    eh_gerente = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membro de Equipe"
        verbose_name_plural = "Membros de Equipe"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "equipe"],
                name="uniq_usuario_equipe",
            )
        ]

    def __str__(self):
        return f"{self.usuario.username} → {self.equipe.nome}"


class ConviteDelegacao(models.Model):
    """
    Convite de delegação (PDR-0033): `item` aponta (via content type
    genérico) para o item da Agenda Jurídica delegado, para não criar
    dependência de `apps.accounts` sobre esse módulo.
    """

    STATUS_PENDENTE = "pendente"
    STATUS_ACEITO = "aceito"
    STATUS_RECUSADO = "recusado"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_ACEITO, "Aceito"),
        (STATUS_RECUSADO, "Recusado"),
    ]

    delegante = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="convites_delegacao_enviados",
    )
    destinatario = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="convites_delegacao_recebidos",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDENTE,
    )
    justificativa_recusa = models.TextField(blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    criado_em = models.DateTimeField(auto_now_add=True)
    respondido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Convite de delegação"
        verbose_name_plural = "Convites de delegação"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Convite #{self.pk}: {self.delegante} → {self.destinatario} ({self.status})"

    def aceitar(self):
        if self.status != self.STATUS_PENDENTE:
            raise ValidationError("Este convite já foi respondido.")
        self.status = self.STATUS_ACEITO
        self.respondido_em = timezone.now()
        self.save(update_fields=["status", "respondido_em"])

    def recusar(self, justificativa=""):
        if self.status != self.STATUS_PENDENTE:
            raise ValidationError("Este convite já foi respondido.")
        self.status = self.STATUS_RECUSADO
        self.justificativa_recusa = justificativa
        self.respondido_em = timezone.now()
        self.save(update_fields=["status", "justificativa_recusa", "respondido_em"])


class PapelAcesso(models.Model):
    """
    Papel de acesso — único mecanismo de autorização além do Administrador
    do escritório (flag em PerfilUsuario), totalmente configurável por ele.

    O papel "Limitado" (codigo_preset=limitado, protegido_sistema=True) nasce
    de fábrica com tudo desligado; é editável, mas não pode ser excluído nem
    desativado.
    """

    nome = models.CharField(
        max_length=100,
        verbose_name="Nome",
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
    )
    codigo_preset = models.SlugField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Código de preset",
        help_text=(
            "Identificador técnico estável dos presets de fábrica. "
            "Nulo para papéis personalizados pelo Tenant Admin."
        ),
    )
    protegido_sistema = models.BooleanField(
        default=False,
        verbose_name="Protegido pelo sistema",
        help_text=(
            "Presets de fábrica marcados aqui não podem ser excluídos "
            "nem ter o codigo_preset alterado pela interface."
        ),
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Papel de Acesso"
        verbose_name_plural = "Papéis de Acesso"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["nome"],
                name="uniq_papelacesso_nome",
            ),
            models.UniqueConstraint(
                fields=["codigo_preset"],
                condition=Q(codigo_preset__isnull=False),
                name="uniq_papelacesso_codigo_preset",
            ),
            models.CheckConstraint(
                condition=Q(codigo_preset__isnull=True) | ~Q(codigo_preset=""),
                name="chk_papelacesso_codigo_preset_nao_vazio",
            ),
        ]

    def __str__(self):
        return self.nome

    @property
    def eh_limitado(self):
        return self.codigo_preset == CODIGO_PRESET_LIMITADO

    def delete(self, *args, **kwargs):
        if self.eh_limitado:
            raise ValidationError("O papel Limitado não pode ser excluído.")
        return super().delete(*args, **kwargs)


class UsuarioPapel(models.Model):
    """
    Vínculo entre usuário e papel de acesso.

    Um usuário pode ter vários papéis simultâneos.
    As permissões são agregadas pelo maior nível entre todos os papéis ativos.
    Overrides individuais em PermissaoUsuario/HabilitacaoUsuario continuam valendo
    independentemente dos papéis.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="atribuicoes_papel",
        verbose_name="Usuário",
    )
    papel = models.ForeignKey(
        PapelAcesso,
        on_delete=models.PROTECT,
        related_name="atribuicoes_usuario",
        verbose_name="Papel",
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
    )
    atribuido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atribuicoes_papel_realizadas",
        verbose_name="Atribuído por",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Papel do Usuário"
        verbose_name_plural = "Papéis dos Usuários"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "papel"],
                name="uniq_usuariopapel_usuario_papel",
            )
        ]
        indexes = [
            models.Index(fields=["usuario", "ativo"], name="idx_usuariopapel_usuario_ativo"),
            models.Index(fields=["papel", "ativo"], name="idx_usuariopapel_papel_ativo"),
        ]

    def __str__(self):
        return f"{self.usuario.username} → {self.papel.nome}"


class PermissaoPapel(models.Model):
    """
    Permissão de acesso de um papel a um módulo.

    Ausência de linha para um módulo = papel sem acesso a esse módulo.
    Administradores não possuem linhas aqui; são verificados por
    usuario_admin_escritorio() antes de qualquer consulta a esta tabela.
    """

    papel = models.ForeignKey(
        PapelAcesso,
        on_delete=models.PROTECT,
        related_name="permissoes_modulo",
        verbose_name="Papel",
    )
    modulo = models.CharField(
        max_length=30,
        choices=MODULO_CHOICES,
        verbose_name="Módulo",
    )
    ativo = models.BooleanField(
        default=False,
        verbose_name="Ativo",
    )
    nivel = models.CharField(
        max_length=30,
        choices=NIVEL_CHOICES,
        blank=True,
        default="",
        verbose_name="Nível de acesso",
        help_text="Vazio para módulos sem escopo de dados (chat, gerir).",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Permissão por Papel"
        verbose_name_plural = "Permissões por Papel"
        ordering = ["papel", "modulo"]
        constraints = [
            models.UniqueConstraint(
                fields=["papel", "modulo"],
                name="uniq_permissaopapel_papel_modulo",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        modulo__in=["processos", "clientes", "modelos", "painel", "agenda"],
                        nivel__in=["somente_seus", "todos"],
                    )
                    | Q(modulo="financeiro", nivel__in=["solicitacoes", "dados_proprios", "dados_todos"])
                    | Q(modulo__in=["chat", "gerir"], nivel="")
                ),
                name="chk_permissaopapel_nivel",
            ),
        ]

    def __str__(self):
        nivel_str = f" [{self.nivel}]" if self.nivel else ""
        return f"{self.papel.nome} / {self.get_modulo_display()}{nivel_str}"

    def clean(self):
        if self.modulo and self.modulo in NIVEIS_POR_MODULO:
            niveis_validos = NIVEIS_POR_MODULO[self.modulo]
            if self.nivel not in niveis_validos:
                raise ValidationError(
                    {"nivel": f"Para '{self.modulo}', o nível deve ser um de: {niveis_validos}."}
                )
        elif self.modulo:
            raise ValidationError({"modulo": f"Módulo desconhecido: '{self.modulo}'."})


class PermissaoUsuario(models.Model):
    """
    Sobrescrita individual de permissão de acesso a um módulo para um usuário.

    Presença da linha substitui PermissaoPapel para o usuário e módulo.
    ativo=True concede acesso individualmente.
    ativo=False bloqueia acesso individualmente.
    Ausência da linha significa herdar o(s) papel(éis) do usuário.
    Excluir a linha faz o usuário voltar ao padrão do papel.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="permissoes_individuais",
        verbose_name="Usuário",
    )
    modulo = models.CharField(
        max_length=30,
        choices=MODULO_CHOICES,
        verbose_name="Módulo",
    )
    ativo = models.BooleanField(
        default=False,
        verbose_name="Ativo",
    )
    nivel = models.CharField(
        max_length=30,
        choices=NIVEL_CHOICES,
        blank=True,
        default="",
        verbose_name="Nível de acesso",
        help_text="Vazio para módulos sem escopo de dados (chat, gerir).",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Permissão Individual"
        verbose_name_plural = "Permissões Individuais"
        ordering = ["usuario", "modulo"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "modulo"],
                name="uniq_permissaousuario_usuario_modulo",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        modulo__in=["processos", "clientes", "modelos", "painel", "agenda"],
                        nivel__in=["somente_seus", "todos"],
                    )
                    | Q(modulo="financeiro", nivel__in=["solicitacoes", "dados_proprios", "dados_todos"])
                    | Q(modulo__in=["chat", "gerir"], nivel="")
                ),
                name="chk_permissaousuario_nivel",
            ),
        ]

    def __str__(self):
        nivel_str = f" [{self.nivel}]" if self.nivel else ""
        return f"{self.usuario} / {self.modulo}{nivel_str}"

    def clean(self):
        if self.modulo and self.modulo in NIVEIS_POR_MODULO:
            niveis_validos = NIVEIS_POR_MODULO[self.modulo]
            if self.nivel not in niveis_validos:
                raise ValidationError(
                    {"nivel": f"Para '{self.modulo}', o nível deve ser um de: {niveis_validos}."}
                )
        elif self.modulo:
            raise ValidationError({"modulo": f"Módulo desconhecido: '{self.modulo}'."})


class HabilitacaoPapel(models.Model):
    """
    Habilitação de um item de funcionalidade por papel.

    Presença com ativo=True = item habilitado para o papel.
    Ausência = item não habilitado.
    """

    papel = models.ForeignKey(
        PapelAcesso,
        on_delete=models.PROTECT,
        related_name="habilitacoes",
        verbose_name="Papel",
    )
    modulo = models.CharField(
        max_length=30,
        choices=MODULO_HABILITACAO_CHOICES,
        verbose_name="Módulo",
    )
    item = models.CharField(
        max_length=60,
        choices=ITEM_CHOICES,
        verbose_name="Item",
    )
    ativo = models.BooleanField(
        default=False,
        verbose_name="Ativo",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Habilitação por Papel"
        verbose_name_plural = "Habilitações por Papel"
        ordering = ["papel", "modulo", "item"]
        constraints = [
            models.UniqueConstraint(
                fields=["papel", "modulo", "item"],
                name="uniq_habilitacaopapel_papel_modulo_item",
            ),
            models.CheckConstraint(
                condition=(
                    Q(modulo="processos", item__in=[
                        "processos_criar",
                        "processos_editar",
                        "processos_andamento_adicionar",
                        "processos_usar_ia",
                        "processos_usar_laboratorio",
                        "processos_atribuir_responsavel",
                        "processos_documento_adicionar",
                        "processos_documento_excluir",
                        "processos_excluir",
                    ])
                    | Q(modulo="clientes", item__in=[
                        "clientes_criar",
                        "clientes_editar",
                        "clientes_desativar",
                        "clientes_reativar",
                        "clientes_excluir",
                        "clientes_documento_adicionar",
                        "clientes_documento_excluir",
                    ])
                    | Q(modulo="modelos", item__in=[
                        "modelos_criar",
                        "modelos_editar_estilo",
                        "modelos_editar_alheio",
                        "modelos_excluir_alheio",
                        "modelos_gerir_categorias",
                    ])
                    | Q(modulo="agenda", item__in=[
                        "agenda_atribuir_outros",
                    ])
                    | Q(modulo="financeiro", item__in=[
                        "financeiro_reabrir_lancamento_pago",
                    ])
                    | Q(modulo="gerir", item__in=[
                        "gerir_criar_usuario",
                        "gerir_habilitar_usuario_processos",
                        "gerir_criar_equipe",
                        "gerir_habilitar_terceiros",
                    ])
                ),
                name="chk_habilitacaopapel_modulo_item",
            ),
        ]

    def __str__(self):
        return f"{self.papel.nome} / {self.get_modulo_display()} / {self.get_item_display()}"

    def clean(self):
        if self.modulo and self.modulo in ITENS_POR_MODULO:
            itens_validos = ITENS_POR_MODULO[self.modulo]
            if not itens_validos:
                raise ValidationError(
                    {"modulo": f"O módulo '{self.modulo}' não possui habilitações nesta versão."}
                )
            if self.item not in itens_validos:
                raise ValidationError(
                    {"item": f"Item '{self.item}' inválido para o módulo '{self.modulo}'."}
                )
        elif self.modulo:
            raise ValidationError({"modulo": f"Módulo desconhecido: '{self.modulo}'."})


class HabilitacaoUsuario(models.Model):
    """
    Sobrescrita individual de habilitação de item para um usuário específico.

    Presença desta linha substitui HabilitacaoPapel para o usuário, módulo e item.
    ativo=True habilita individualmente.
    ativo=False desabilita individualmente.
    Ausência da linha significa herdar HabilitacaoPapel.
    Excluir a linha restaura a herança.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habilitacoes_individuais",
        verbose_name="Usuário",
    )
    modulo = models.CharField(
        max_length=30,
        choices=MODULO_HABILITACAO_CHOICES,
        verbose_name="Módulo",
    )
    item = models.CharField(
        max_length=60,
        choices=ITEM_CHOICES,
        verbose_name="Item",
    )
    ativo = models.BooleanField(
        default=False,
        verbose_name="Ativo",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Habilitação Individual"
        verbose_name_plural = "Habilitações Individuais"
        ordering = ["usuario", "modulo", "item"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "modulo", "item"],
                name="uniq_habilitacaousuario_usuario_modulo_item",
            ),
            models.CheckConstraint(
                condition=(
                    Q(modulo="processos", item__in=[
                        "processos_criar",
                        "processos_editar",
                        "processos_andamento_adicionar",
                        "processos_usar_ia",
                        "processos_usar_laboratorio",
                        "processos_atribuir_responsavel",
                        "processos_documento_adicionar",
                        "processos_documento_excluir",
                        "processos_excluir",
                    ])
                    | Q(modulo="clientes", item__in=[
                        "clientes_criar",
                        "clientes_editar",
                        "clientes_desativar",
                        "clientes_reativar",
                        "clientes_excluir",
                        "clientes_documento_adicionar",
                        "clientes_documento_excluir",
                    ])
                    | Q(modulo="modelos", item__in=[
                        "modelos_criar",
                        "modelos_editar_estilo",
                        "modelos_editar_alheio",
                        "modelos_excluir_alheio",
                        "modelos_gerir_categorias",
                    ])
                    | Q(modulo="agenda", item__in=[
                        "agenda_atribuir_outros",
                    ])
                    | Q(modulo="financeiro", item__in=[
                        "financeiro_reabrir_lancamento_pago",
                    ])
                    | Q(modulo="gerir", item__in=[
                        "gerir_criar_usuario",
                        "gerir_habilitar_usuario_processos",
                        "gerir_criar_equipe",
                        "gerir_habilitar_terceiros",
                    ])
                ),
                name="chk_habilitacaousuario_modulo_item",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} / {self.modulo} / {self.item}"

    def clean(self):
        if self.modulo and self.modulo in ITENS_POR_MODULO:
            itens_validos = ITENS_POR_MODULO[self.modulo]
            if not itens_validos:
                raise ValidationError(
                    {"modulo": f"O módulo '{self.modulo}' não possui habilitações nesta versão."}
                )
            if self.item not in itens_validos:
                raise ValidationError(
                    {"item": f"Item '{self.item}' inválido para o módulo '{self.modulo}'."}
                )
        elif self.modulo:
            raise ValidationError({"modulo": f"Módulo desconhecido: '{self.modulo}'."})
