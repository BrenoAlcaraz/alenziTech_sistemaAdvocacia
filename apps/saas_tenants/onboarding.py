"""Criação de um escritório pronto para uso: tenant (schema), domínio
principal, identidade visual padrão e usuário dono (Administrador)."""

import re
import secrets
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection, transaction
from django_tenants.utils import schema_context, schema_exists

from apps.accounts.models import PerfilUsuario

from .cores import COR_PRIMARIA_PADRAO, COR_SECUNDARIA_PADRAO
from .models import ConfiguracaoVisual, Dominio, Escritorio

SLUGS_RESERVADOS = frozenset(
    {"admin", "www", "api", "app", "public", "static", "media", "mail"}
)
# Slug vira ao mesmo tempo nome de schema PostgreSQL e subdomínio.
_SLUG = re.compile(r"^[a-z][a-z0-9]{0,29}$")


class ErroOnboarding(Exception):
    pass


@dataclass(frozen=True)
class EscritorioCriado:
    escritorio: Escritorio
    dominio: str
    usuario: str
    senha: str


def dominio_base():
    base = (getattr(settings, "DOMINIO_BASE", "") or "").strip().strip(".")
    if not base:
        raise ErroOnboarding("DOMINIO_BASE não definido no .env.")
    return base


def validar(*, nome, slug, admin_usuario, admin_email, admin_nome):
    """Recusa qualquer entrada inválida ou já existente antes de criar algo.
    Devolve o domínio principal do escritório."""
    dominio = f"{slug}.{dominio_base()}"
    if not nome.strip():
        raise ErroOnboarding("Nome do escritório é obrigatório.")
    if not _SLUG.match(slug):
        raise ErroOnboarding(
            "Slug inválido: use só letras minúsculas e números, começando "
            "por letra, até 30 caracteres."
        )
    if slug in SLUGS_RESERVADOS:
        raise ErroOnboarding(f"Slug '{slug}' é reservado.")
    if (
        Escritorio.objects.filter(slug=slug).exists()
        or Escritorio.objects.filter(schema_name=slug).exists()
        or schema_exists(slug)
    ):
        raise ErroOnboarding(f"Já existe escritório com o slug '{slug}'.")
    if Dominio.objects.filter(domain=dominio).exists():
        raise ErroOnboarding(f"Domínio '{dominio}' já está em uso.")
    try:
        User.username_validator(admin_usuario)
    except ValidationError:
        raise ErroOnboarding(f"Usuário '{admin_usuario}' inválido.")
    if not admin_usuario or len(admin_usuario) > 150:
        raise ErroOnboarding("Usuário deve ter de 1 a 150 caracteres.")
    try:
        validate_email(admin_email)
    except ValidationError:
        raise ErroOnboarding(f"E-mail '{admin_email}' inválido.")
    if not admin_nome.strip():
        raise ErroOnboarding("Nome do administrador é obrigatório.")
    return dominio


def criar_escritorio(*, nome, slug, admin_usuario, admin_email, admin_nome):
    """Tudo ou nada: qualquer falha após criar o schema remove o
    escritório inteiro (schema, domínio, identidade visual, usuário)."""
    dominio = validar(
        nome=nome, slug=slug, admin_usuario=admin_usuario,
        admin_email=admin_email, admin_nome=admin_nome,
    )
    senha = secrets.token_urlsafe(12)

    # O schema é criado (e migrado) dentro de save(); se isso falhar, o
    # próprio django-tenants remove o registro e o schema.
    escritorio = Escritorio(schema_name=slug, slug=slug, nome=nome.strip())
    escritorio.save(verbosity=0)
    try:
        with transaction.atomic():
            Dominio.objects.create(tenant=escritorio, domain=dominio, is_primary=True)
            ConfiguracaoVisual.objects.create(
                escritorio=escritorio,
                nome_exibicao=escritorio.nome,
                cor_primaria=COR_PRIMARIA_PADRAO,
                cor_secundaria=COR_SECUNDARIA_PADRAO,
            )
        with schema_context(slug), transaction.atomic():
            _criar_dono(admin_usuario, admin_email, admin_nome.strip(), senha)
    except Exception:
        _desfazer(escritorio)
        raise

    return EscritorioCriado(escritorio, dominio, admin_usuario, senha)


def _desfazer(escritorio):
    """DROP SCHEMA + cascata em Dominio/ConfiguracaoVisual (public)."""
    if connection.in_atomic_block:
        # Chamado dentro de uma transação externa, as FKs deferidas das
        # migrations recém-aplicadas impedem o DROP ("pending trigger
        # events"); forçar a checagem agora libera o schema.
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    escritorio.delete(force_drop=True)


def _criar_dono(usuario, email, nome, senha):
    user = User.objects.create_user(
        username=usuario, email=email, password=senha,
        is_staff=False, is_superuser=False,
    )
    perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
    perfil.nome_completo = nome
    perfil.is_admin_escritorio = True
    perfil.save()
    return user
