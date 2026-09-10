from django.db import models
from django.contrib.auth.models import User


class CategoriaModeloPeca(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Categoria de Modelo de Peça"
        verbose_name_plural = "Categorias de Modelo de Peça"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ModeloPeca(models.Model):
    titulo = models.CharField(max_length=255)
    categoria = models.ForeignKey(
        CategoriaModeloPeca, on_delete=models.PROTECT, related_name="modelos"
    )
    area_direito = models.CharField(max_length=50)
    conteudo = models.TextField(help_text="Conteúdo em texto ou HTML da peça modelo")
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
    """Tom de voz e instruções gerais do escritório para geração futura de IA."""

    tom_voz = models.TextField(
        blank=True,
        help_text="Descreva o tom de voz e estilo de escrita do escritório.",
    )
    instrucoes_gerais = models.TextField(
        blank=True,
        help_text="Instruções gerais que a IA deve seguir ao redigir peças.",
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estilo do Escritório"

    def __str__(self):
        return "Estilo do Escritório"
