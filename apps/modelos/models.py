from django.db import models
from django.contrib.auth.models import User

from apps.saas_tenants.storage import CaminhoArquivoTenant, PROTEGIDO, StorageProtegido, nome_do_arquivo


def config_documento_padrao():
    """Configuração inicial do editor visual de 'Meu Estilo' — cada chave
    corresponde a uma seção configurável na folha do editor
    (docs/prototipos/modelos-prototipo.html, aba Meu Estilo)."""
    return {
        "geral": {
            "cor_folha": "#ffffff",
            "fonte": "Times New Roman",
            "tamanho_fonte": 11,
            "espacamento": "1.15",
            "recuo_texto": "1.25",
            "recuo_paragrafo": "1.25",
        },
        # `largura` (10-100, percentual da largura da folha) e
        # `alinhamento` (left/center/right) valem só em modo "imagem"
        # (specs/modelos-estilo-simplificacao-imagens.md). `replicacao`
        # (todas/primeira/ultima) só existe em cabeçalho/rodapé — marca
        # d'água continua sempre em toda página; assinatura tem modelo
        # próprio (`AssinaturaEstilo`, permite mais de uma).
        "slots": {
            "cabecalho": {
                "ativo": True, "modo": "texto", "texto": "",
                "largura": 30, "alinhamento": "center", "replicacao": "todas",
            },
            "rodape": {
                "ativo": True, "modo": "texto", "texto": "",
                "largura": 30, "alinhamento": "center", "replicacao": "todas",
            },
            "marca_dagua": {
                "ativo": True, "modo": "texto", "texto": "MINUTA",
                "largura": 30, "alinhamento": "center",
            },
        },
        "secoes": {
            "enderecamento": {
                "fonte": "Times New Roman", "tamanho": 12, "caixa": "maiusculas",
                "alinhamento": "center", "negrito": True, "italico": False,
            },
            "numero_processo": {
                "tamanho": 10, "caixa": "capitalizado",
                "alinhamento": "right", "negrito": False, "italico": False,
                "distancia_linhas": 2,
            },
            "numero_guia": {
                "tamanho": 10, "caixa": "capitalizado",
                "alinhamento": "right", "negrito": False, "italico": False,
                "distancia_linhas": 3,
            },
            "partes": {"caixa": "maiusculas", "negrito": True, "italico": False},
            "jurisprudencia": {
                "fonte": "Times New Roman", "tamanho": 10, "recuo": "40",
                "alinhamento": "justify", "cor": "#222222", "marca_texto": "transparent",
                "negrito": False, "italico": False, "sublinhado": True, "tachado": False,
            },
            "artigo": {
                "fonte": "Times New Roman", "tamanho": 10, "recuo": "40",
                "alinhamento": "justify", "cor": "#222222", "marca_texto": "transparent",
                "negrito": False, "italico": True, "sublinhado": False, "tachado": False,
            },
            "citacao": {
                "fonte": "Times New Roman", "tamanho": 10, "recuo": "20",
                "alinhamento": "justify", "cor": "#5b6785", "marca_texto": "transparent",
                "negrito": False, "italico": True, "sublinhado": False, "tachado": False,
            },
        },
    }


class CategoriaModeloPeca(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Categoria de Modelo de Peça"
        verbose_name_plural = "Categorias de Modelo de Peça"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


REPLICACAO_CHOICES = [
    ("todas", "Todas as páginas"),
    ("primeira", "Apenas na primeira"),
    ("ultima", "Apenas na última"),
]


class ModeloPeca(models.Model):
    titulo = models.CharField(max_length=255)
    categoria = models.ForeignKey(
        CategoriaModeloPeca, on_delete=models.PROTECT, related_name="modelos"
    )
    area_direito = models.CharField(max_length=50)
    conteudo = models.TextField(help_text="Conteúdo em texto ou HTML da peça modelo")
    # Réplica de cabeçalho/rodapé por página — por modelo, não só pelo
    # padrão único do escritório (specs/modelos-estilo-simplificacao-
    # imagens.md). Valor inicial vem do padrão de Meu Estilo no momento
    # da criação (moldura de contexto), mas fica independente dele daí
    # em diante — mudar o padrão do escritório não altera modelo já criado.
    cabecalho_replicacao = models.CharField(max_length=10, choices=REPLICACAO_CHOICES, default="todas")
    rodape_replicacao = models.CharField(max_length=10, choices=REPLICACAO_CHOICES, default="todas")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # Futuramente: IA usará esses modelos como exemplos para geração de peças.
    # Por ora apenas estrutura de armazenamento.

    class Meta:
        verbose_name = "Modelo de Peça"
        verbose_name_plural = "Modelos de Peças"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo

    def preview(self):
        return self.conteudo[:120] + "..." if len(self.conteudo) > 120 else self.conteudo


class VersaoModeloPeca(models.Model):
    """Snapshot do estado de um ModeloPeca imediatamente antes de uma edição/reversão."""

    modelo = models.ForeignKey(ModeloPeca, on_delete=models.CASCADE, related_name="versoes")
    titulo = models.CharField(max_length=255)
    # PROTECT (não só no ModeloPeca atual): reverter para esta versão exige
    # uma categoria ainda existente — categoria referenciada só pelo
    # histórico continua bloqueando exclusão do catálogo, deliberadamente.
    categoria = models.ForeignKey(CategoriaModeloPeca, on_delete=models.PROTECT)
    area_direito = models.CharField(max_length=50)
    conteudo = models.TextField()
    editado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Versão de Modelo de Peça"
        verbose_name_plural = "Versões de Modelo de Peça"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.titulo} ({self.criado_em:%d/%m/%Y %H:%M})"


class EstiloEscritorio(models.Model):
    """Padrão visual dos documentos do escritório (singleton por tenant —
    sempre `pk=1`, ver `_obter_estilo_escritorio` em views.py).
    """

    MODO_CONSTRUIR = "construir"
    MODO_ANEXAR = "anexar"
    MODO_ESTILO_CHOICES = [
        (MODO_CONSTRUIR, "Construir do zero"),
        (MODO_ANEXAR, "Anexar peça existente"),
    ]

    # Editor visual — padrão de formatação replicado em toda peça nova
    # (docs/prototipos/modelos-prototipo.html, aba "Meu Estilo").
    modo_estilo = models.CharField(
        max_length=10, choices=MODO_ESTILO_CHOICES, default=MODO_CONSTRUIR,
    )
    arquivo_referencia = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "modelos/estilo/referencia"),
        storage=StorageProtegido(),
        blank=True,
        help_text="Peça já formatada usada como referência visual (modo 'Anexar').",
    )
    imagem_cabecalho = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "modelos/estilo/cabecalho"),
        storage=StorageProtegido(), blank=True,
    )
    imagem_rodape = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "modelos/estilo/rodape"),
        storage=StorageProtegido(), blank=True,
    )
    imagem_marca_dagua = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "modelos/estilo/marca-dagua"),
        storage=StorageProtegido(), blank=True,
    )
    # Formatação geral da folha + de cada seção retrátil (endereçamento,
    # número do processo/guia, nome das partes, jurisprudência, artigo,
    # citação) — um JSON só, nunca filtrado/consultado por subcampo, em vez
    # de dezenas de colunas para configuração puramente apresentacional.
    # Ver `config_documento_padrao()` para o formato e
    # `sanitizar_config_documento()` (forms.py) para a validação de entrada.
    config_documento = models.JSONField(default=config_documento_padrao)

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estilo do Escritório"

    def __str__(self):
        return "Estilo do Escritório"

    def nome_do_arquivo_referencia(self):
        return nome_do_arquivo(self.arquivo_referencia)


class AssinaturaEstilo(models.Model):
    """Um bloco de assinatura do padrão de Meu Estilo — texto ou imagem,
    mais de um por escritório (ex.: dois sócios assinando a mesma peça,
    specs/modelos-estilo-simplificacao-imagens.md). Presença na lista já
    é o "ligado"; sem nenhuma linha, nenhuma assinatura é exibida."""

    MODO_TEXTO = "texto"
    MODO_IMAGEM = "imagem"
    MODO_CHOICES = [
        (MODO_TEXTO, "Texto"),
        (MODO_IMAGEM, "Imagem"),
    ]

    ALINHAMENTO_CHOICES = [
        ("left", "Esquerda"),
        ("center", "Centro"),
        ("right", "Direita"),
    ]

    estilo = models.ForeignKey(EstiloEscritorio, on_delete=models.CASCADE, related_name="assinaturas")
    ordem = models.PositiveIntegerField(default=0)
    modo = models.CharField(max_length=10, choices=MODO_CHOICES, default=MODO_TEXTO)
    texto = models.CharField(max_length=300, blank=True)
    imagem = models.FileField(
        upload_to=CaminhoArquivoTenant(PROTEGIDO, "modelos/estilo/assinaturas"),
        storage=StorageProtegido(), blank=True,
    )
    largura = models.PositiveSmallIntegerField(
        default=30, verbose_name="Largura (% da folha)", help_text="Só vale em modo imagem.",
    )
    alinhamento = models.CharField(max_length=10, choices=ALINHAMENTO_CHOICES, default="center")

    class Meta:
        verbose_name = "Assinatura do Estilo"
        verbose_name_plural = "Assinaturas do Estilo"
        ordering = ["ordem", "pk"]

    def __str__(self):
        return self.texto or f"Assinatura #{self.ordem}"
