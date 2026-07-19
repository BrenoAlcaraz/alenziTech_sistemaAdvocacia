from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User

from .permissoes_constants import (
    TIPOS_CONTA_CONFIGURAVEIS,
    TIPOS_CONTA_CHOICES,
    MODULO_CHOICES,
    MODULO_HABILITACAO_CHOICES,
    NIVEL_CHOICES,
    ITEM_CHOICES,
    NIVEIS_POR_MODULO,
    ITENS_POR_MODULO,
)


class PerfilUsuario(models.Model):
    """
    Dados extras do usuário dentro de um tenant específico.
    Usa o User padrão do Django via OneToOne.
    Cargo é apenas descritivo — não controla permissão.
    Permissões são gerenciadas via django.contrib.auth.Group.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    nome_completo = models.CharField(max_length=255, blank=True)
    cargo = models.CharField(
        max_length=100,
        blank=True,
        help_text="Apenas descritivo. Não controla permissões.",
    )
    avatar = models.ImageField(upload_to="avatares/", blank=True, null=True)
    is_admin_escritorio = models.BooleanField(
        default=False,
        help_text="Indica se este usuário é administrador do escritório.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    # Futuramente: decorators e middleware verificarão is_admin_escritorio
    # e os grupos do Django para controle granular de acesso.

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self):
        return self.nome_completo or self.user.username

    def iniciais(self):
        """Retorna iniciais para o avatar visual."""
        partes = self.nome_completo.split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[-1][0]}".upper()
        return self.user.username[:2].upper()


class Equipe(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    equipe_pai = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subequipes",
    )
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


class PermissaoPapel(models.Model):
    """
    Permissão padrão de acesso a um módulo por tipo de conta técnico.

    Ausência de linha para um módulo = tipo de conta sem acesso a esse módulo.
    Administradores não possuem linhas aqui; são verificados por
    usuario_admin_escritorio() antes de qualquer consulta a esta tabela.
    """

    tipo_conta = models.CharField(
        max_length=20,
        choices=TIPOS_CONTA_CHOICES,
        verbose_name="Tipo de conta",
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
        verbose_name = "Permissão por Tipo de Conta"
        verbose_name_plural = "Permissões por Tipo de Conta"
        ordering = ["tipo_conta", "modulo"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_conta", "modulo"],
                name="uniq_permissaopapel_tipo_modulo",
            ),
            models.CheckConstraint(
                condition=Q(tipo_conta__in=["limitado", "financeiro"]),
                name="chk_permissaopapel_tipo_conta",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        modulo__in=["processos", "clientes", "tarefas", "modelos", "painel", "agenda"],
                        nivel__in=["somente_seus", "todos"],
                    )
                    | Q(modulo="financeiro", nivel__in=["solicitacoes", "dados"])
                    | Q(modulo__in=["chat", "gerir"], nivel="")
                ),
                name="chk_permissaopapel_nivel",
            ),
        ]

    def __str__(self):
        nivel_str = f" [{self.nivel}]" if self.nivel else ""
        return f"{self.tipo_conta} / {self.modulo}{nivel_str}"

    def clean(self):
        if self.tipo_conta and self.tipo_conta not in TIPOS_CONTA_CONFIGURAVEIS:
            raise ValidationError(
                {"tipo_conta": f"Tipo de conta inválido: '{self.tipo_conta}'."}
            )
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
    Ausência da linha significa herdar o tipo de conta.
    Excluir a linha faz o usuário voltar ao padrão do tipo de conta.
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
                        modulo__in=["processos", "clientes", "tarefas", "modelos", "painel", "agenda"],
                        nivel__in=["somente_seus", "todos"],
                    )
                    | Q(modulo="financeiro", nivel__in=["solicitacoes", "dados"])
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
    Habilitação de um item de funcionalidade por tipo de conta técnico.

    Presença com ativo=True = item habilitado para o tipo de conta.
    Ausência = item não habilitado.
    """

    tipo_conta = models.CharField(
        max_length=20,
        choices=TIPOS_CONTA_CHOICES,
        verbose_name="Tipo de conta",
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
        verbose_name = "Habilitação por Tipo de Conta"
        verbose_name_plural = "Habilitações por Tipo de Conta"
        ordering = ["tipo_conta", "modulo", "item"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_conta", "modulo", "item"],
                name="uniq_habilitacaopapel_tipo_modulo_item",
            ),
            models.CheckConstraint(
                condition=Q(tipo_conta__in=["limitado", "financeiro"]),
                name="chk_habilitacaopapel_tipo_conta",
            ),
            models.CheckConstraint(
                condition=(
                    Q(modulo="processos", item__in=[
                        "processos_criar",
                        "processos_editar",
                        "processos_andamento_adicionar",
                        "processos_usar_ia",
                        "processos_usar_laboratorio",
                    ])
                    | Q(modulo="clientes", item__in=[
                        "clientes_criar",
                        "clientes_editar",
                    ])
                    | Q(modulo="tarefas", item__in=[
                        "tarefas_atribuir_outros",
                    ])
                    | Q(modulo="modelos", item__in=[
                        "modelos_criar",
                        "modelos_editar_estilo",
                    ])
                    | Q(modulo="agenda", item__in=[
                        "agenda_criar_para_outros",
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
        return f"{self.tipo_conta} / {self.modulo} / {self.item}"

    def clean(self):
        if self.tipo_conta and self.tipo_conta not in TIPOS_CONTA_CONFIGURAVEIS:
            raise ValidationError(
                {"tipo_conta": f"Tipo de conta inválido: '{self.tipo_conta}'."}
            )
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
                    ])
                    | Q(modulo="clientes", item__in=[
                        "clientes_criar",
                        "clientes_editar",
                    ])
                    | Q(modulo="tarefas", item__in=[
                        "tarefas_atribuir_outros",
                    ])
                    | Q(modulo="modelos", item__in=[
                        "modelos_criar",
                        "modelos_editar_estilo",
                    ])
                    | Q(modulo="agenda", item__in=[
                        "agenda_criar_para_outros",
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
