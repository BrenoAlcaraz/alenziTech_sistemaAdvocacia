# Spec — Conversas individuais e em grupo no Chat

Status: em andamento.

## Objetivo

Permitir que usuários do mesmo tenant iniciem conversas individuais (1:1)
e em grupo no Chat, além da sala global já existente, trocando mensagens
com acesso restrito a quem participa da conversa.

## Comportamento esperado

- Nova ação de iniciar conversa individual: usuário escolhe outro usuário
  do tenant; se já existir uma conversa individual entre os dois, reabre
  a existente em vez de criar duplicata.
- Nova ação de criar conversa em grupo: usuário escolhe 2+ participantes
  e informa um título (obrigatório — grupo sem título fica ambíguo na
  listagem).
- `chat:lista` deixa de redirecionar sempre para `chat:global` — passa a
  listar as conversas do usuário (global + individuais + grupos de que
  participa), ordenada pela mais recente.
- `chat:detalhe` deixa de redirecionar sempre para `chat:global` — passa
  a abrir a conversa individual/grupo pelo mesmo padrão já usado em
  `global_sala` (listar mensagens, form de envio via POST).
- Envio de mensagem em conversa individual/grupo segue o fluxo já
  implementado em `global_sala` (POST cria `Mensagem`, redireciona).
- Equipe (`apps/accounts` `Equipe`) não gera grupo de chat
  automaticamente — regra já definida em `docs/PRODUCT.md`, só
  confirmada aqui.

## Regras de negócio relevantes

- Acesso a uma conversa (leitura e envio de mensagem) é sempre por
  participação: só quem está em `Conversa.participantes` acessa.
  Quem não participa recebe 404 ao tentar `/chat/<pk>/` diretamente,
  nunca 403 — mesmo padrão de posse via `QuerySet` já usado em
  Clientes/Processos (`docs/ARCHITECTURE.md#autorização--padrão-a-reutilizar`);
  conhecer o `pk` não concede acesso.
- Isolamento entre tenants já é estrutural (`apps.chat` está em
  `TENANT_APPS`, schema PostgreSQL por tenant) — não é preciso filtro
  adicional por tenant no código da view.
- Autorização de módulo continua binária
  (`tem_permissao_modulo(user, MODULO_CHAT)`,
  `NIVEIS_POR_MODULO[MODULO_CHAT] == [""]`) — não introduzir nível de
  escopo novo no kernel de `apps/accounts`; a granularidade de acesso é
  só por participação, resolvida dentro do próprio app `chat`.
- Usuários ativos do tenant aparecem como opção de participante ao
  iniciar conversa individual/grupo — mesmo universo já usado em
  `apps/agenda/views.py::_usuarios_elegiveis_para_participante`
  (não há, hoje, um jeito de filtrar usuário por acesso a módulo em
  queryset; e não filtrar aqui não abre brecha, porque o gate do módulo
  Chat é sempre reconferido em toda rota, inclusive para quem foi
  convidado).
- Reaproveita os models já existentes `Conversa`/`Mensagem`
  (`apps/chat/models.py`, tipos `individual`/`grupo`/`global` e
  `participantes` já modelados) — sem alteração de schema.

## Fora do escopo

- Notificação de nova mensagem — `docs/decisions/PDR-0016` cobre só
  Tarefas/Agenda; chat pode ganhar isso depois, não faz parte desta
  versão.
- Indicador de lida/não lida por participante — o campo `Mensagem.lida`
  existente é um booleano único, insuficiente para grupo (múltiplos
  leitores); não será usado nem estendido aqui.
- Tempo real (WebSocket/Django Channels) — já registrado como futuro no
  próprio `apps/chat/models.py`; esta versão mantém o padrão
  request/response (POST + redirect) já usado na sala global.
- Editar ou excluir mensagem enviada.
- Sair de um grupo, remover participante, renomear grupo, ou qualquer
  administração de grupo além da criação.
- Anexos em mensagem.
- Chamada de áudio/vídeo, integração com apps externos, IA no chat (já
  fora de escopo em `docs/PRODUCT.md`).

## Critérios de aceite

- Usuário autorizado ao módulo Chat inicia conversa individual com outro
  usuário do tenant e troca mensagens visíveis só para os dois.
- Usuário autorizado ao módulo Chat cria grupo com título e 2+
  participantes e troca mensagens visíveis só para quem está no grupo.
- Iniciar conversa individual duas vezes com a mesma pessoa reabre a
  conversa existente, não duplica.
- `chat:lista` mostra a sala global e todas as conversas
  individuais/grupos de que o usuário participa.
- Usuário sem acesso ao módulo Chat continua recebendo 403 em qualquer
  rota do chat (comportamento já testado — não regride).
- Usuário que não participa de uma conversa recebe 404 ao acessar
  `/chat/<pk>/` diretamente pela URL.
- Conversa/mensagem de um tenant nunca aparece em outro tenant
  (isolamento estrutural já existente, coberto por teste igual ao
  padrão dos demais módulos).
