---
title: Estado atual — Financeiro
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Financeiro

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [financeiro.md](../../product/modules/financeiro.md) (especificação
canônica) e [authorization-matrix.md#financeiro](../../security/authorization-matrix.md#financeiro).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/financeiro/views.py` implementa listagem, criação, edição,
marcação de pago, cancelamento, reabertura e exclusão de
`LancamentoFinanceiro`, além de listagem e criação de `CustaJudicial`.
O saldo de custas por cliente é calculado no backend
(`créditos depositados − custas pagas pelo escritório`), conforme
exigido por
[PDR-0005](../../product/decisions/PDR-0005-custas-por-cliente.md).

## Estado interno por área funcional

| Área funcional | Estado | Implementação identificada | Diferença principal |
| --- | --- | --- | --- |
| Financeiro geral | Parcialmente implementado | `LancamentoFinanceiro` com `CATEGORIA_CHOICES`, `status`, `data_pagamento`; indicadores de previsto/realizado calculados na view | Sem campo de modalidade (único/parcelado/recorrente); `CATEGORIA_CHOICES` inclui `"custa_judicial"` como categoria comum, apesar de PDR-0003 exigir área própria |
| Custas judiciais | Parcialmente implementado | `CustaJudicial` existe; saldo por cliente calculado corretamente no backend, conforme PDR-0005 | Sem filtro de escopo na listagem; sem rota de edição/transição de estado identificada (sem exigência canônica correspondente) |
| Solicitações | Não identificado | Nenhum model, view ou rota para solicitação de pagamento/reembolso | Fluxo já resolvido por [PDR-0015](../../product/decisions/PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md); modelagem inteira pendente de implementação |
| Honorários | Não identificado | Nenhum model `Honorario`; `LancamentoFinanceiro.CATEGORIA_CHOICES` inclui `"honorario"`/`"exito"` como categorias, sem os campos de valor estimado/efetivo exigidos por PDR-0007 | Modelagem de Honorário como entidade própria pendente |
| Recorrência | Não identificado | Nenhum campo de quantidade de parcelas, periodicidade, data final ou vínculo de origem entre ocorrências | Bloqueado por [OPEN-001](../../product/open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão) |
| Billing SaaS | Parcialmente implementado | `Plano`/`Assinatura` existem em `saas_billing`; leitura (sem escrita) do nome do plano em `apps.configuracoes` e `apps.dashboard` | Sem interface de gestão de plano além da leitura; nenhuma sincronização automática assinatura → lançamento, conforme PDR-0003 (preservado deliberadamente, não é lacuna) |

Pontos preservados sem resolução: OPEN-001 (PDR-0015 já resolveu o
antigo OPEN-002), billing mantido separado do financeiro do tenant por
decisão de
[PDR-0003](../../product/decisions/PDR-0003-areas-funcionais-financeiro.md),
e nenhuma sincronização automática entre assinatura SaaS e lançamento
financeiro do tenant.

## Diferenças para o alvo canônico

Ver a tabela "Estado interno por área funcional" acima para o
detalhamento por área funcional.

## Dependências ou bloqueios

[OPEN-001](../../product/open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão),
[PDR-0015](../../product/decisions/PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md)
(resolve o antigo OPEN-002; modelagem de Solicitações ainda não
implementada no código), Fase A e B para autorização/escopo, Fase D
para consolidação.
