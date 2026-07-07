from django.db import models


class ConfiguracaoEscritorio(models.Model):
    nome_escritorio = models.CharField(max_length=255, blank=True)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    cnpj = models.CharField(max_length=18, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    endereco = models.TextField(blank=True)
    site = models.URLField(blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração do Escritório"
        verbose_name_plural = "Configurações do Escritório"

    def __str__(self):
        return (
            self.nome_escritorio
            or self.nome_fantasia
            or "Configuração do Escritório"
        )
