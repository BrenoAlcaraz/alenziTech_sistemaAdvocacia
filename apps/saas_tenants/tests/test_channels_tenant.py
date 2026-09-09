from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.db import connection
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context, tenant_context

from apps.saas_tenants.channels_middleware import TenantWebsocketMiddleware
from apps.saas_tenants.models import Dominio, Escritorio

CAMINHO_QUALQUER = "/qualquer/"


class _ConsumerDeTeste(AsyncWebsocketConsumer):
    """Stub só para este teste — devolve o que `TenantWebsocketMiddleware`
    resolveu em `scope`, sem tocar em nada de negócio."""

    async def connect(self):
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        usuario = self.scope["user"]
        await self.send(text_data=f"{self.scope['tenant'].schema_name}:{usuario.username}")


def _aplicacao_de_teste():
    return TenantWebsocketMiddleware(_ConsumerDeTeste.as_asgi())


def _criar_sessao_para(usuario):
    """Sessão autenticada equivalente à que o login por HTTP deixaria no
    cookie — mesma chave (`_auth_user_id`) que `AuthenticationMiddleware`
    lê no caminho HTTP."""
    sessao = SessionStore()
    sessao["_auth_user_id"] = str(usuario.pk)
    sessao["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
    sessao.create()
    return sessao.session_key


def _headers(dominio, session_key=None, origin=None):
    """`origin=None` usa a origem confiável padrão (mesmo domínio da
    conexão); `origin=""` omite o header; qualquer outro valor é usado
    como está — para simular handshake de outro domínio."""
    origem = f"http://{dominio}" if origin is None else origin
    headers = [(b"host", dominio.encode())]
    if session_key:
        headers.append((b"cookie", f"sessionid={session_key}".encode()))
    if origem:
        headers.append((b"origin", origem.encode()))
    return headers


class TestTenantWebsocketMiddleware(TenantTestCase):
    """Valida a issue #14: resolução de tenant/usuário dentro de uma
    conexão WebSocket, via `TenantWebsocketMiddleware`. O isolamento de
    grupo do channel layer entre tenants é responsabilidade de cada
    consumer (ex.: `apps/chat/consumers.py`, `apps/chat/realtime.py`) e é
    coberto lá, com semântica real."""

    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "ws_tenant_a"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WS A"
        tenant.slug = "ws-a"

    def setUp(self):
        # Cada teste, ao abrir uma conexão WebSocket, faz o próprio
        # middleware trocar o schema ativo da conexão compartilhada da
        # thread principal (mesma thread usada pelos testes, já que
        # `database_sync_to_async` roda na "thread atual" quando chamado
        # via `async_to_sync` a partir de código síncrono) — restaurar
        # aqui não é workaround de teste, é a mesma regra validada por
        # esta issue: nunca depender do schema deixado por uma operação
        # anterior, sempre resolver de novo antes de usar.
        connection.set_tenant(self.tenant)

        self.usuario_a = User.objects.create_user("usuaria.a", password="senha-teste-123")

        self.tenant_b = Escritorio(schema_name="ws_tenant_b", nome="WS B", slug="ws-b")
        with schema_context("public"):
            self.tenant_b.save()
            self.dominio_b = Dominio.objects.create(
                tenant=self.tenant_b, domain="ws-b.test.com", is_primary=True
            )
        with tenant_context(self.tenant_b):
            self.usuario_b = User.objects.create_user("usuaria.b", password="senha-teste-123")

        self.addCleanup(self._remover_tenant_b)

    def _remover_tenant_b(self):
        with schema_context("public"):
            self.tenant_b.delete(force_drop=True)
        # Volta ao schema conhecido do tenant A explicitamente — não
        # confiar no que a conexão compartilhada ficou depois do cenário
        # WebSocket do teste (mesma regra validada nesta issue), para o
        # `flush` do `TransactionTestCase` truncar o schema certo entre
        # os testes.
        connection.set_tenant(self.tenant)

    def test_conexao_autenticada_resolve_tenant_e_usuario_do_dominio(self):
        session_key = _criar_sessao_para(self.usuario_a)

        async def cenario():
            communicator = WebsocketCommunicator(
                _aplicacao_de_teste(), CAMINHO_QUALQUER, headers=_headers(self.domain.domain, session_key)
            )
            conectado, _ = await communicator.connect()
            self.assertTrue(conectado)

            await communicator.send_to(text_data="oi")
            resposta = await communicator.receive_from()
            self.assertEqual(resposta, f"{self.tenant.schema_name}:{self.usuario_a.username}")

            await communicator.disconnect()

        async_to_sync(cenario)()

    def test_conexao_sem_sessao_e_rejeitada(self):
        async def cenario():
            communicator = WebsocketCommunicator(
                _aplicacao_de_teste(), CAMINHO_QUALQUER, headers=_headers(self.domain.domain)
            )
            conectado, codigo = await communicator.connect()
            self.assertFalse(conectado)
            self.assertEqual(codigo, 4403)

        async_to_sync(cenario)()

    def test_dominio_sem_tenant_e_rejeitado(self):
        session_key = _criar_sessao_para(self.usuario_a)

        async def cenario():
            communicator = WebsocketCommunicator(
                _aplicacao_de_teste(),
                CAMINHO_QUALQUER,
                headers=_headers("dominio-sem-tenant.test.com", session_key),
            )
            conectado, codigo = await communicator.connect()
            self.assertFalse(conectado)
            self.assertEqual(codigo, 4403)

        async_to_sync(cenario)()

    def test_conexao_sem_header_origin_e_rejeitada(self):
        """Spec em specs/websocket-validar-origin-handshake.md — correção
        de Cross-Site WebSocket Hijacking (CSWH)."""
        session_key = _criar_sessao_para(self.usuario_a)

        async def cenario():
            communicator = WebsocketCommunicator(
                _aplicacao_de_teste(),
                CAMINHO_QUALQUER,
                headers=_headers(self.domain.domain, session_key, origin=""),
            )
            conectado, codigo = await communicator.connect()
            self.assertFalse(conectado)
            self.assertEqual(codigo, 4403)

        async_to_sync(cenario)()

    def test_conexao_com_origin_de_outro_dominio_e_rejeitada(self):
        session_key = _criar_sessao_para(self.usuario_a)

        async def cenario():
            communicator = WebsocketCommunicator(
                _aplicacao_de_teste(),
                CAMINHO_QUALQUER,
                headers=_headers(
                    self.domain.domain, session_key, origin="http://evil.example.com"
                ),
            )
            conectado, codigo = await communicator.connect()
            self.assertFalse(conectado)
            self.assertEqual(codigo, 4403)

        async_to_sync(cenario)()

    def test_usuario_resolvido_e_do_schema_certo_mesmo_com_pk_repetido_entre_tenants(self):
        session_key_b = _criar_sessao_para(self.usuario_b)

        async def cenario():
            communicator_b = WebsocketCommunicator(
                _aplicacao_de_teste(), CAMINHO_QUALQUER, headers=_headers(self.dominio_b.domain, session_key_b)
            )
            self.assertTrue((await communicator_b.connect())[0])

            await communicator_b.send_to(text_data="oi")
            resposta_b = await communicator_b.receive_from()
            self.assertEqual(resposta_b, f"{self.tenant_b.schema_name}:{self.usuario_b.username}")

            await communicator_b.disconnect()

        async_to_sync(cenario)()
