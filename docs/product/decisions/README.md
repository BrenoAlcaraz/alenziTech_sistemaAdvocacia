---
title: Registros de decisões de produto
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-31
---

# Registros de decisões de produto

## O que é um PDR

Um PDR (product decision record) registra uma decisão funcional de
produto já aprovada, seu contexto, as regras que decorrem dela e suas
consequências. Um PDR não descreve o estado atual do código — o que
existe implementado é responsabilidade do current-state e das
especificações de módulo, não deste registro.

Mudanças incompatíveis com um PDR existente exigem um novo PDR ou uma
substituição explícita, registrada no campo `supersedes` do documento
sucessor. Um PDR não é alterado silenciosamente para refletir uma
mudança de decisão.

Decisões que ainda não foram aprovadas não são PDRs. Elas permanecem
registradas em [open-decisions.md](../open-decisions.md) até que sejam
efetivamente decididas.

## PDRs deste lote

| ID | Decisão | Estado | Documento |
| --- | --- | --- | --- |
| PDR-0001 | Participantes processuais | accepted; partially superseded by PDR-0013 | [PDR-0001-participantes-processuais.md](PDR-0001-participantes-processuais.md) |
| PDR-0002 | Delegação direta de tarefas | accepted | [PDR-0002-delegacao-direta-de-tarefas.md](PDR-0002-delegacao-direta-de-tarefas.md) |
| PDR-0003 | Áreas funcionais do Financeiro | accepted | [PDR-0003-areas-funcionais-financeiro.md](PDR-0003-areas-funcionais-financeiro.md) |
| PDR-0004 | Previsto e realizado | accepted | [PDR-0004-previsto-e-realizado.md](PDR-0004-previsto-e-realizado.md) |
| PDR-0005 | Custas por cliente | accepted | [PDR-0005-custas-por-cliente.md](PDR-0005-custas-por-cliente.md) |
| PDR-0006 | Solicitações financeiras | accepted | [PDR-0006-solicitacoes-financeiras.md](PDR-0006-solicitacoes-financeiras.md) |
| PDR-0007 | Honorários manuais antes da IA | accepted | [PDR-0007-honorarios-manuais-antes-ia.md](PDR-0007-honorarios-manuais-antes-ia.md) |
| PDR-0008 | IA após o núcleo funcional | accepted | [PDR-0008-ia-apos-nucleo-funcional.md](PDR-0008-ia-apos-nucleo-funcional.md) |
| PDR-0009 | Sequência revisada da Fase 2 | accepted | [PDR-0009-sequencia-fase-2.md](PDR-0009-sequencia-fase-2.md) |
| PDR-0010 | Autorização, escopo e responsabilidade de Processos | accepted | [PDR-0010-autorizacao-escopo-responsabilidade-processos.md](PDR-0010-autorizacao-escopo-responsabilidade-processos.md) |
| PDR-0011 | Taxonomia e representação de participantes de Processos | superseded by PDR-0013 | [PDR-0011-taxonomia-representacao-participantes-processos.md](PDR-0011-taxonomia-representacao-participantes-processos.md) |
| PDR-0012 | Relação simétrica de processos apensos | accepted | [PDR-0012-relacao-simetrica-processos-apensos.md](PDR-0012-relacao-simetrica-processos-apensos.md) |
| PDR-0013 | Partes de processo: modelo simplificado | accepted | [PDR-0013-partes-processo-modelo-simplificado.md](PDR-0013-partes-processo-modelo-simplificado.md) |
| PDR-0014 | Responsável principal e integrantes habilitados de Processos | accepted | [PDR-0014-responsavel-integrantes-processos.md](PDR-0014-responsavel-integrantes-processos.md) |
| PDR-0015 | Fluxo de aprovação das solicitações financeiras | accepted | [PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md](PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md) |
| PDR-0016 | Notificações de Tarefas e Agenda | accepted | [PDR-0016-notificacoes-tarefas-agenda.md](PDR-0016-notificacoes-tarefas-agenda.md) |
