from channels.generic.websocket import AsyncWebsocketConsumer
from django.template.loader import render_to_string

from apps.accounts.permissoes import tem_permissao_modulo
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.saas_tenants.channels_middleware import tenant_database_sync_to_async

from .models import Conversa, Mensagem
from .realtime import grupo_conversa, grupo_global, grupo_lista, grupo_usuario


def _renderizar_mensagem(mensagem_id, usuario_atual):
    try:
        mensagem = Mensagem.objects.select_related("autor").get(pk=mensagem_id)
    except Mensagem.DoesNotExist:
        return None
    return render_to_string(
        "chat/_mensagem.html", {"mensagem": mensagem, "usuario_atual": usuario_atual}
    )


def _indicador_nao_lida_html():
    # Sem consulta ao banco — parcial estático, não precisa do wrapper
    # de troca de schema.
    return render_to_string("chat/_indicador_nao_lida.html")


class _BaseConversaConsumer(AsyncWebsocketConsumer):
    """Base comum entre conversa individual/grupo e sala global: entrega
    de mensagem nova pelo grupo do channel layer, renderizando o mesmo
    parcial usado no envio por HTTP (`apps/chat/views.py`). Cada
    subclasse só define autorização e nome do grupo no `connect`."""

    async def disconnect(self, code):
        if hasattr(self, "grupo"):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def chat_mensagem(self, evento):
        tenant, usuario = self.scope["tenant"], self.scope["user"]
        fragmento = await tenant_database_sync_to_async(tenant, _renderizar_mensagem)(
            evento["mensagem_id"], usuario
        )
        if fragmento is not None:
            await self.send(text_data=fragmento)


class ConversaConsumer(_BaseConversaConsumer):
    """Conversa individual/grupo aberta — autorização replica
    `apps.chat.views.detalhe`: módulo habilitado + participação na
    conversa."""

    async def connect(self):
        tenant, usuario = self.scope["tenant"], self.scope["user"]
        conversa_pk = self.scope["url_route"]["kwargs"]["pk"]

        autorizado = await tenant_database_sync_to_async(tenant, self._autorizado)(
            usuario, conversa_pk
        )
        if not autorizado:
            await self.close(code=4403)
            return

        self.grupo = grupo_conversa(tenant, conversa_pk)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()

    @staticmethod
    def _autorizado(usuario, conversa_pk):
        if not tem_permissao_modulo(usuario, MODULO_CHAT):
            return False
        return (
            Conversa.objects.exclude(tipo=Conversa.TIPO_GLOBAL)
            .filter(pk=conversa_pk, participantes=usuario)
            .exists()
        )


class SalaGlobalConsumer(_BaseConversaConsumer):
    """Sala global — autorização replica `apps.chat.views.global_sala`:
    só o módulo habilitado, sem lista de participantes."""

    async def connect(self):
        tenant, usuario = self.scope["tenant"], self.scope["user"]

        autorizado = await tenant_database_sync_to_async(tenant, tem_permissao_modulo)(
            usuario, MODULO_CHAT
        )
        if not autorizado:
            await self.close(code=4403)
            return

        self.grupo = grupo_global(tenant)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()


class ListaConsumer(AsyncWebsocketConsumer):
    """Página `chat:lista` — recebe aviso de não lida em tempo real:
    grupo pessoal para conversa individual/grupo, grupo do tenant para a
    sala global (que não tem lista de participantes)."""

    async def connect(self):
        tenant, usuario = self.scope["tenant"], self.scope["user"]

        autorizado = await tenant_database_sync_to_async(tenant, tem_permissao_modulo)(
            usuario, MODULO_CHAT
        )
        if not autorizado:
            await self.close(code=4403)
            return

        self.grupo_pessoal = grupo_usuario(tenant, usuario.pk)
        self.grupo_tenant = grupo_lista(tenant)
        await self.channel_layer.group_add(self.grupo_pessoal, self.channel_name)
        await self.channel_layer.group_add(self.grupo_tenant, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "grupo_pessoal"):
            await self.channel_layer.group_discard(self.grupo_pessoal, self.channel_name)
            await self.channel_layer.group_discard(self.grupo_tenant, self.channel_name)

    async def chat_nao_lida(self, evento):
        await self.send(text_data=f"{evento['conversa_id']}\n{_indicador_nao_lida_html()}")
