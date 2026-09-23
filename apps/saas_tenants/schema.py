from django.db import connection
from django_tenants.utils import get_public_schema_name


def no_schema_publico():
    """Conexão está no schema da plataforma, onde tabelas de escritório
    (TENANT_APPS) não existem."""
    return connection.schema_name == get_public_schema_name()
