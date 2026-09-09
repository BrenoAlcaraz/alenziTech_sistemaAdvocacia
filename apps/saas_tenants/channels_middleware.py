"""Resolução de tenant e usuário para conexões WebSocket (Channels).

Equivalente, para o protocolo websocket, ao que `TenantMainMiddleware`
(schema pelo domínio) + `AuthenticationMiddleware` (usuário pela sessão)
já fazem no caminho HTTP — ver `docs/ARCHITECTURE.md`.
"""

from urllib.parse import urlparse

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.backends.db import SessionStore
from django.db import connection
from django_tenants.utils import get_tenant_domain_model, remove_www


def _hostname_da_conexao(scope):
    for nome, valor in scope.get("headers", []):
        if nome == b"host":
            return remove_www(valor.decode().split(":")[0])
    return None


def _origem_da_conexao(scope):
    for nome, valor in scope.get("headers", []):
        if nome == b"origin":
            return valor.decode()
    return None


def _origem_confiavel(scope):
    """Origem do handshake precisa apontar pro mesmo host da própria
    conexão (`Host`, já usado para resolver o tenant) — cada escritório
    tem seu próprio domínio, então não existe lista estática de origens
    confiáveis possível aqui. Sem isso, uma página em outro domínio
    conseguiria abrir uma conexão autenticada usando o cookie de sessão
    que o navegador envia sozinho (Cross-Site WebSocket Hijacking)."""
    origem_host = urlparse(_origem_da_conexao(scope) or "").hostname
    host_conexao = _hostname_da_conexao(scope)
    if not origem_host or not host_conexao:
        return False
    return remove_www(origem_host.lower()) == host_conexao.lower()


def _session_key_da_conexao(scope):
    for nome, valor in scope.get("headers", []):
        if nome == b"cookie":
            for parte in valor.decode().split(";"):
                chave, _, val = parte.strip().partition("=")
                if chave == settings.SESSION_COOKIE_NAME:
                    return val
    return None


def _resolver_tenant_e_usuario(scope):
    """Troca o schema e resolve o usuário da sessão numa única chamada
    síncrona, sem `await` no meio.

    `channels`/`asgiref` serializam chamadas síncronas de conexões
    concorrentes numa única thread compartilhada (sem contexto
    thread-sensitive próprio por conexão) — se a troca de schema
    (`connection.set_tenant`) e a consulta que depende dela rodassem em
    chamadas `await` separadas, outra conexão poderia trocar o schema
    dessa mesma thread entre as duas. Fazer tudo numa função síncrona só
    fecha essa janela.
    """
    connection.set_schema_to_public()
    hostname = _hostname_da_conexao(scope)
    tenant = None
    if hostname:
        domain_model = get_tenant_domain_model()
        try:
            tenant = domain_model.objects.select_related("tenant").get(domain=hostname).tenant
        except domain_model.DoesNotExist:
            tenant = None

    if tenant is None:
        return None, AnonymousUser()

    connection.set_tenant(tenant)

    usuario = AnonymousUser()
    session_key = _session_key_da_conexao(scope)
    if session_key:
        sessao = SessionStore(session_key)
        user_id = sessao.get("_auth_user_id")
        if user_id:
            try:
                usuario = User.objects.get(pk=user_id, is_active=True)
            except User.DoesNotExist:
                usuario = AnonymousUser()
    return tenant, usuario


def tenant_database_sync_to_async(tenant, fn):
    """`database_sync_to_async`, mas troca o schema para `tenant` dentro
    da mesma chamada síncrona, imediatamente antes de rodar `fn`.

    Consumers não podem assumir que o schema resolvido no `connect`
    (por `TenantWebsocketMiddleware`) continua ativo mais tarde — outra
    conexão pode ter trocado o schema da mesma thread compartilhada
    nesse meio-tempo (mesmo risco documentado em `_resolver_tenant_e_usuario`).
    Toda operação de banco de um consumer deve passar por aqui, nunca
    presumir schema ambiente.
    """

    def _com_schema(*args, **kwargs):
        connection.set_tenant(tenant)
        return fn(*args, **kwargs)

    return database_sync_to_async(_com_schema)


class TenantWebsocketMiddleware:
    """Resolve `scope["tenant"]`/`scope["user"]` antes de aceitar a
    conexão. Fecha a conexão se a origem do handshake não for confiável,
    se não houver tenant para o domínio, ou se o usuário não estiver
    autenticado — mesma política de `@login_required` já aplicada em
    toda view do sistema."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if not _origem_confiavel(scope):
            await send({"type": "websocket.close", "code": 4403})
            return None
        tenant, usuario = await database_sync_to_async(_resolver_tenant_e_usuario)(scope)
        if tenant is None or usuario.is_anonymous:
            await send({"type": "websocket.close", "code": 4403})
            return None
        scope = {**scope, "tenant": tenant, "user": usuario}
        return await self.inner(scope, receive, send)
