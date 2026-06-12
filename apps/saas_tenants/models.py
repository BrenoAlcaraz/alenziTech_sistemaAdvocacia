from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Escritorio(TenantMixin):
    """Representa um escritório de advocacia — um tenant isolado no banco."""

    nome = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    # django-tenants exige esse campo herdado de TenantMixin:
    # schema_name (já vem via TenantMixin)
    auto_create_schema = True

    class Meta:
        verbose_name = "Escritório"
        verbose_name_plural = "Escritórios"

    def __str__(self):
        return self.nome


class Dominio(DomainMixin):
    """Domínio/subdomínio vinculado a um Escritório."""

    # domain e is_primary já vêm de DomainMixin
    # tenant (FK → Escritorio) já vem de DomainMixin

    class Meta:
        verbose_name = "Domínio"
        verbose_name_plural = "Domínios"

    def __str__(self):
        return self.domain


class ConfiguracaoVisual(models.Model):
    """Personalização white label de cada escritório, armazenada no schema público."""

    escritorio = models.OneToOneField(
        Escritorio,
        on_delete=models.CASCADE,
        related_name="configuracao_visual",
    )
    nome_exibicao = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    favicon = models.ImageField(upload_to="favicons/", blank=True, null=True)
    cor_primaria = models.CharField(max_length=7, default="#1a1a1a")
    cor_secundaria = models.CharField(max_length=7, default="#8B7355")
    imagem_fundo_login = models.ImageField(upload_to="backgrounds/", blank=True, null=True)

    class Meta:
        verbose_name = "Configuração Visual"
        verbose_name_plural = "Configurações Visuais"

    def __str__(self):
        return f"Visual — {self.escritorio.nome}"
