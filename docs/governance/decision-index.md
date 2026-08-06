---
title: Índice de decisões
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Índice de decisões

## Como utilizar este índice

Este índice lista decisões de produto e arquitetura já identificadas no
projeto, junto com o registro formal (PDR ou ADR) que futuramente as
documentará. Este índice não substitui os futuros PDRs e ADRs; ele apenas
rastreia quais decisões existem e para onde apontar quando forem
formalizadas.

Os PDRs e ADRs listados abaixo representam decisões funcionais e
arquiteturais já consolidadas nas fontes anteriores do projeto (histórico,
planos e checkpoints). Elas estão pendentes apenas de formalização em
arquivos PDR ou ADR individuais — não estão em aberto. Já os itens
OPEN-001, OPEN-002 e OPEN-003, na seção "Decisões em aberto", continuam
realmente sem decisão tomada.

## Decisões de produto pendentes de formalização

| ID planejado | Assunto | Estado | Futuro documento |
| --- | --- | --- | --- |
| PDR-0001 | Participantes processuais | aprovada — pendente de formalização | `docs/product/decisions/PDR-0001-participantes-processuais.md` |
| PDR-0002 | Delegação direta de tarefas | aprovada — pendente de formalização | `docs/product/decisions/PDR-0002-delegacao-direta-de-tarefas.md` |
| PDR-0003 | Áreas funcionais do Financeiro | aprovada — pendente de formalização | `docs/product/decisions/PDR-0003-areas-funcionais-financeiro.md` |
| PDR-0004 | Previsto e realizado | aprovada — pendente de formalização | `docs/product/decisions/PDR-0004-previsto-e-realizado.md` |
| PDR-0005 | Custas por cliente | aprovada — pendente de formalização | `docs/product/decisions/PDR-0005-custas-por-cliente.md` |
| PDR-0006 | Solicitações de pagamento e reembolso | aprovada — pendente de formalização | `docs/product/decisions/PDR-0006-solicitacoes-financeiras.md` |
| PDR-0007 | Honorários manuais antes da IA | aprovada — pendente de formalização | `docs/product/decisions/PDR-0007-honorarios-manuais-antes-ia.md` |
| PDR-0008 | IA após consolidação do núcleo funcional | aprovada — pendente de formalização | `docs/product/decisions/PDR-0008-ia-apos-nucleo-funcional.md` |
| PDR-0009 | Sequência revisada da Fase 2 | aprovada — pendente de formalização | `docs/product/decisions/PDR-0009-sequencia-fase-2.md` |

## Decisões arquiteturais pendentes de formalização

| ID planejado | Assunto | Estado | Futuro documento |
| --- | --- | --- | --- |
| ADR-0001 | Monólito modular Django | pendente de formalização | `docs/architecture/decisions/ADR-0001-monolito-modular.md` |
| ADR-0002 | Schema PostgreSQL por tenant | pendente de formalização | `docs/architecture/decisions/ADR-0002-schema-por-tenant.md` |
| ADR-0003 | User padrão e PerfilUsuario | pendente de formalização | `docs/architecture/decisions/ADR-0003-user-e-perfil.md` |
| ADR-0004 | Autorização por papéis dinâmicos | pendente de formalização | `docs/architecture/decisions/ADR-0004-papeis-dinamicos.md` |
| ADR-0005 | Implementação de IA após consolidação do núcleo | pendente de formalização | `docs/architecture/decisions/ADR-0005-ia-apos-consolidacao-core.md` |

## Decisões em aberto

- **OPEN-001** — Periodicidades financeiras da primeira versão.
- **OPEN-002** — Etapas de aprovação das solicitações financeiras.
- **OPEN-003** — Espelhamento da assinatura SaaS no Financeiro.

Estas decisões ainda não foram resolvidas. Após a criação da área de
produto, elas serão mantidas em `docs/product/open-decisions.md`.

## Regra de atualização

Quando um PDR ou ADR for efetivamente criado:

- O estado correspondente neste índice deve ser atualizado.
- O caminho real do documento deve ser inserido no lugar do caminho
  planejado.
- Decisões substituídas devem apontar para sua sucessora.
- Este índice não deve conter o texto completo da decisão — apenas a
  referência a ela.
