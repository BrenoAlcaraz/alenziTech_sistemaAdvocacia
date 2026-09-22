"""Test runner com blindagem contra schemas de tenant orfaos.

Contexto: suites baseadas em ``TenantTestCase`` (django-tenants) usam
schema_name fixo por classe (``get_test_schema_name``). ``setUpClass``
cria o schema real no Postgres; ``tearDownClass`` o remove. Se uma
execucao for interrompida antes do ``tearDownClass`` (Ctrl+C, timeout,
processo encerrado), schema e tenant ficam orfaos no banco de teste —
como ``schema_name`` e unique, a proxima execucao daquela mesma classe
falha em ``cls.tenant.save()`` (IntegrityError), o que pode deixar a
conexao em estado de transacao abortada e contaminar classes de teste
seguintes na mesma execucao (sintoma: erros de conexao/schema em testes
sem relacao com a mudanca feita).

Este runner corrige o problema na raiz sem exigir alteracao das classes
de teste existentes: antes de cada ``setUpClass``, remove qualquer
schema/tenant orfao com o mesmo nome que a classe esta prestes a criar.
"""

from django.db import connections
from django.test.runner import DiscoverRunner
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import (
    get_public_schema_name,
    get_tenant_database_alias,
    get_tenant_model,
    schema_exists,
)


def _limpar_schema_orfao(schema_name):
    if schema_name == get_public_schema_name():
        return

    tenant_model = get_tenant_model()
    orfao = tenant_model.objects.filter(schema_name=schema_name).first()
    if orfao is not None:
        orfao.delete(force_drop=True)
        return

    if schema_exists(schema_name):
        connection = connections[get_tenant_database_alias()]
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')


_setup_class_original = TenantTestCase.setUpClass.__func__


def _setup_class_blindado(cls):
    _limpar_schema_orfao(cls.get_test_schema_name())
    _setup_class_original(cls)


class TenantAwareTestRunner(DiscoverRunner):
    """DiscoverRunner padrao + limpeza de schemas de tenant orfaos."""

    def setup_test_environment(self, **kwargs):
        TenantTestCase.setUpClass = classmethod(_setup_class_blindado)
        super().setup_test_environment(**kwargs)
