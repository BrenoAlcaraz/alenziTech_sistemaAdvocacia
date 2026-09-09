"""Nomes de grupo do channel layer para o Chat em tempo real.

Sempre prefixados pelo schema do tenant — mesma regra validada na
issue #14 (`TenantWebsocketMiddleware`): nunca confiar num identificador
de conversa/usuário sem qualificar por tenant, já que o mesmo pk existe
em schemas diferentes.
"""


def grupo_conversa(tenant, conversa_pk):
    return f"{tenant.schema_name}.chat.conversa.{conversa_pk}"


def grupo_global(tenant):
    return f"{tenant.schema_name}.chat.global"


def grupo_usuario(tenant, usuario_pk):
    return f"{tenant.schema_name}.chat.usuario.{usuario_pk}"


def grupo_lista(tenant):
    return f"{tenant.schema_name}.chat.lista"
