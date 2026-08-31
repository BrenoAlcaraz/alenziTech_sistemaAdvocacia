---
title: Estado atual — Agenda
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Agenda

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [agenda.md](../../product/modules/agenda.md) (especificação
canônica) e [authorization-matrix.md#agenda](../../security/authorization-matrix.md#agenda).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/agenda/views.py` implementa `index`, `form_compromisso`,
`editar`, `concluir`, `cancelar`, `reabrir`, `excluir`, com filtros de
listagem por data/status (`hoje`, `proximos_7`, `vencidos`, `todos`).
`Compromisso` possui `responsavel`, `participantes` (M2M),
vínculo opcional com `processo` e `cliente`.

## Diferenças para o alvo canônico

[agenda.md](../../product/modules/agenda.md) exige escopo por
responsável ou participante — não aplicado. `cliente` e `processo` são
campos independentes em `CompromissoForm`; uma combinação inconsistente
enviada por `POST` não é rejeitada pelo servidor, apenas preenchida
automaticamente quando um dos dois está vazio. A notificação automática
15 minutos antes aprovada em
[PDR-0016](../../product/decisions/PDR-0016-notificacoes-tarefas-agenda.md)
não está implementada; não existe mecanismo periódico em segundo plano
nem model/serviço de notificação no HEAD.

## Dependências ou bloqueios

Fase A e B do roadmap; integridade cliente-processo tratada na Fase C;
PDR-0016 requer infraestrutura de execução periódica ainda inexistente.
