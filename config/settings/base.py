from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "chave-insegura-somente-dev")

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,.localhost").split(",")

# ─── Multi-Tenancy ─────────────────────────────────────────────────────────────
SHARED_APPS = [
    "daphne",  # antes de staticfiles: assume o runserver em modo ASGI
    "channels",
    "django_tenants",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps públicas do SaaS
    "apps.saas_tenants",
    "apps.saas_billing",
]

TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    # Apps de cada escritório
    "apps.accounts",
    "apps.atividade",
    "apps.dashboard",
    "apps.clientes",
    "apps.processos",
    "apps.notificacoes",
    "apps.financeiro",
    "apps.agenda",
    "apps.chat",
    "apps.modelos",
    "apps.laboratorio",
    "apps.configuracoes",
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

TENANT_MODEL = "saas_tenants.Escritorio"
TENANT_DOMAIN_MODEL = "saas_tenants.Dominio"
# Base do subdomínio de cada escritório (<slug>.<DOMINIO_BASE>):
# "localhost" em dev, domínio da plataforma em produção.
DOMINIO_BASE = os.getenv("DOMINIO_BASE", "")

# ─── Banco de Dados ────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": os.getenv("DB_NAME", "juridico_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

# Limpa schemas de tenant orfaos (de execucoes de teste interrompidas)
# antes de cada TenantTestCase.setUpClass — ver apps/saas_tenants/testing.py.
TEST_RUNNER = "apps.saas_tenants.testing.TenantAwareTestRunner"

# ─── Aplicação ─────────────────────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"
# Domínio da plataforma (schema public) serve só o Django Admin; telas
# de escritório e /admin/ nunca coexistem no mesmo domínio.
PUBLIC_SCHEMA_URLCONF = "config.urls_public"

# SESSION_COOKIE_DOMAIN fica propositalmente indefinido: django_session é
# única (public) e guarda só o id do usuário, que é outra pessoa em cada
# escritório — cookie compartilhado entre subdomínios abriria sessão em
# outro escritório como outro usuário.

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Injeta dados do tenant e configuração visual em todos os templates
                "apps.saas_tenants.context_processors.tenant_config",
                # Injeta notificações não lidas do usuário logado (header)
                "apps.notificacoes.context_processors.notificacoes",
                # Página raiz de módulo (header não mostra "Voltar")
                "config.context_processors.navegacao",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Channel layer em memória — só serve um único processo (suficiente para
# validar a issue #14). Produção com mais de um worker exige um backend
# compartilhado (ex.: Redis); decisão registrada como escopo da issue #15,
# não desta.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# ─── Auth ──────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# ─── Internacionalização ───────────────────────────────────────────────────────
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ─── Static e Media ────────────────────────────────────────────────────────────
STATIC_URL = os.getenv("STATIC_URL", "/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Acompanhamento de processos (DataJud + DJEN) ──────────────────────────────
DJEN_URL = os.getenv("DJEN_URL", "https://comunicaapi.pje.jus.br/api/v1/comunicacao")
# Dias não úteis do cálculo de prazo (padrão provisório — spec J9): feriados
# nacionais fixos ("DD/MM"), datas avulsas ("AAAA-MM-DD") e recesso forense.
# A Sexta-feira Santa é móvel e entra sempre, calculada pela Páscoa.
FERIADOS_NACIONAIS = os.getenv(
    "FERIADOS_NACIONAIS", "01/01,21/04,01/05,07/09,12/10,02/11,15/11,20/11,25/12"
).split(",")
FERIADOS_AVULSOS = [d for d in os.getenv("FERIADOS_AVULSOS", "").split(",") if d]
RECESSO_FORENSE = os.getenv("RECESSO_FORENSE", "20/12-20/01")
