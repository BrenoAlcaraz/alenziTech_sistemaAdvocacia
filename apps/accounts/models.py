from django.db import models
from django.contrib.auth.models import User


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
