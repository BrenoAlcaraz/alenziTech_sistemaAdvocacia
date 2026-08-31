---
title: Estado atual — Chat
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Chat

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [chat.md](../../product/modules/chat.md) (especificação
canônica) e [authorization-matrix.md#chat](../../security/authorization-matrix.md#chat).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/chat/views.py` implementa `lista`, `detalhe`, `global_sala`. A
única sala existente é `Conversa.TIPO_GLOBAL`, obtida por
`get_or_create`, compartilhada por todo o tenant. `lista`/`detalhe`
sempre redirecionam para ela — o `pk` recebido por `detalhe` não é
usado para carregar uma conversa específica. Envio de mensagem
funcional, com validação de conteúdo não vazio.

## Diferenças para o alvo canônico

[chat.md](../../product/modules/chat.md) prevê conversas individuais e em
grupo — nenhuma das duas existe no código; não há view de criação de
conversa além da sala global.

## Dependências ou bloqueios

Fase E do roadmap (funcionalidades colaborativas e de apoio).
