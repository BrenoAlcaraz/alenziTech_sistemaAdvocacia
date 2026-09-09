"""
Testes de entrega em tempo real (WebSocket) no Chat — issue #15, spec em
specs/chat-tempo-real-websocket.md. Depende da resolução de
tenant/usuário da issue #14 (apps/saas_tenants/channels_middleware.py).

Segue o mesmo padrão de fixtures de apps/chat/tests/test_conversas.py.
Notificação (`Notificacao`) e leitura (`LeituraConversa`) não são
retestadas aqui — continuam cobertas por
apps/chat/tests/test_notificacoes_e_indicador.py e
apps/chat/tests/test_leitura.py, que seguem passando sem alteração.
"""

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.test import TransactionTestCase, override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.chat.models import Conversa
from config.asgi import application


def _criar_sessao_para(usuario):
    """Sessão autenticada equivalente à que o login por HTTP deixaria no
    cookie — mesma chave (`_auth_user_id`) que `AuthenticationMiddleware`
    lê no caminho HTTP."""
    sessao = SessionStore()
    sessao["_auth_user_id"] = str(usuario.pk)
    sessao["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
    sessao.create()
    return sessao.session_key


def _headers(dominio, session_key):
    return [(b"host", dominio.encode()), (b"cookie", f"sessionid={session_key}".encode())]


class ChatTempoRealBase(TenantTestCase):
    """`channels.db.database_sync_to_async` (usado pelos consumers e
    nas chamadas de teste que cruzam pra fora do WebSocket) fecha
    conexões consideradas "antigas" ao final de cada chamada — o que
    rompe a conexão única que `TestCase` mantém aberta sob uma
    transação atômica por teste. Mesmo ajuste de
    `apps/saas_tenants/tests/test_storage.py::TestIdentidadeVisualIsolamentoMultiTenant`."""

    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        self.http_host = Dominio.objects.filter(tenant=self.tenant).first().domain

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_acesso_chat(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel Chat {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_CHAT, ativo=True, nivel=""
        )

    def _enviar_por_http(self, usuario, url, conteudo):
        self.client.force_login(usuario)
        return self.client.post(url, {"conteudo": conteudo}, HTTP_HOST=self.http_host)


class TestConversaIndividualTempoReal(ChatTempoRealBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_ws_individual"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        self.carla = self._user("carla")
        for user in (self.ana, self.bruno, self.carla):
            self._dar_acesso_chat(user)
        self.conversa = Conversa.objects.create(tipo=Conversa.TIPO_INDIVIDUAL)
        self.conversa.participantes.set([self.ana, self.bruno])

    def test_mensagem_chega_em_tempo_real_para_quem_esta_com_a_conversa_aberta(self):
        session_key_bruno = _criar_sessao_para(self.bruno)

        async def cenario():
            comunicador = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversa.pk}/",
                headers=_headers(self.http_host, session_key_bruno),
            )
            conectado, _ = await comunicador.connect()
            self.assertTrue(conectado)

            await database_sync_to_async(self._enviar_por_http)(
                self.ana, f"/chat/{self.conversa.pk}/", "oi bruno"
            )

            resposta = await comunicador.receive_from()
            self.assertIn("oi bruno", resposta)

            await comunicador.disconnect()

        async_to_sync(cenario)()

    def test_usuario_sem_participacao_nao_consegue_conectar_mesmo_tendo_o_modulo(self):
        session_key_carla = _criar_sessao_para(self.carla)

        async def cenario():
            comunicador = WebsocketCommunicator(
                application,
                f"/ws/chat/{self.conversa.pk}/",
                headers=_headers(self.http_host, session_key_carla),
            )
            conectado, codigo = await comunicador.connect()
            self.assertFalse(conectado)
            self.assertEqual(codigo, 4403)

        async_to_sync(cenario)()

    def test_indicador_de_nao_lida_atualiza_na_lista_sem_reload(self):
        session_key_bruno = _criar_sessao_para(self.bruno)

        async def cenario():
            comunicador = WebsocketCommunicator(
                application, "/ws/chat/lista/", headers=_headers(self.http_host, session_key_bruno)
            )
            conectado, _ = await comunicador.connect()
            self.assertTrue(conectado)

            await database_sync_to_async(self._enviar_por_http)(
                self.ana, f"/chat/{self.conversa.pk}/", "oi bruno"
            )

            resposta = await comunicador.receive_from()
            conversa_id, _, html = resposta.partition("\n")
            self.assertEqual(conversa_id, str(self.conversa.pk))
            self.assertIn("bg-juridico-vermelho", html)

            await comunicador.disconnect()

        async_to_sync(cenario)()

    def test_indicador_de_nao_lida_nao_chega_pra_quem_nao_participa(self):
        session_key_carla = _criar_sessao_para(self.carla)

        async def cenario():
            comunicador = WebsocketCommunicator(
                application, "/ws/chat/lista/", headers=_headers(self.http_host, session_key_carla)
            )
            conectado, _ = await comunicador.connect()
            self.assertTrue(conectado)

            await database_sync_to_async(self._enviar_por_http)(
                self.ana, f"/chat/{self.conversa.pk}/", "oi bruno"
            )

            self.assertTrue(await comunicador.receive_nothing(timeout=0.3))
            await comunicador.disconnect()

        async_to_sync(cenario)()

    @override_settings(CHANNEL_LAYERS={})
    def test_envio_de_mensagem_por_http_funciona_sem_channel_layer_configurado(self):
        r = self._enviar_por_http(self.ana, f"/chat/{self.conversa.pk}/", "oi bruno")
        self.assertEqual(r.status_code, 302)


class TestSalaGlobalTempoReal(ChatTempoRealBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_ws_global"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        for user in (self.ana, self.bruno):
            self._dar_acesso_chat(user)

    def test_mensagem_da_sala_global_chega_em_tempo_real(self):
        session_key_bruno = _criar_sessao_para(self.bruno)

        async def cenario():
            comunicador = WebsocketCommunicator(
                application, "/ws/chat/global/", headers=_headers(self.http_host, session_key_bruno)
            )
            conectado, _ = await comunicador.connect()
            self.assertTrue(conectado)

            await database_sync_to_async(self._enviar_por_http)(self.ana, "/chat/global/", "oi geral")

            resposta = await comunicador.receive_from()
            self.assertIn("oi geral", resposta)

            await comunicador.disconnect()

        async_to_sync(cenario)()

    def test_indicador_de_nao_lida_da_sala_global_chega_pra_qualquer_usuario_do_modulo(self):
        session_key_bruno = _criar_sessao_para(self.bruno)

        async def cenario():
            comunicador = WebsocketCommunicator(
                application, "/ws/chat/lista/", headers=_headers(self.http_host, session_key_bruno)
            )
            conectado, _ = await comunicador.connect()
            self.assertTrue(conectado)

            await database_sync_to_async(self._enviar_por_http)(self.ana, "/chat/global/", "oi geral")

            resposta = await comunicador.receive_from()
            conversa_id, _, html = resposta.partition("\n")
            self.assertEqual(conversa_id, "global")
            self.assertIn("bg-juridico-vermelho", html)

            await comunicador.disconnect()

        async_to_sync(cenario)()
