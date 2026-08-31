---
title: Estado atual — Dashboard
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Dashboard

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [dashboard.md](../../product/modules/dashboard.md) (especificação
canônica) e [authorization-matrix.md#dashboard](../../security/authorization-matrix.md#dashboard).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/dashboard/views.py::painel` agrega dados reais de
`apps.clientes.Cliente`, `apps.processos.Processo`,
`apps.tarefas.Tarefa`, `apps.agenda.Compromisso` e
`apps.financeiro.LancamentoFinanceiro`, sem mocks. Lê
`request.tenant.assinatura.plano.nome` para exibição, sem escrita. Não
possui `models.py` próprio.

## Diferenças para o alvo canônico

[dashboard.md](../../product/modules/dashboard.md) exige que cada
indicador respeite autorização e escopo do usuário que consulta;
`painel` calcula todos os contadores e totais (incluindo financeiros)
sobre o tenant inteiro, sem filtro por usuário.

## Dependências ou bloqueios

Depende de escopo aplicado primeiro em Clientes, Processos, Tarefas,
Agenda e Financeiro, conforme a ordem de dependência de
[PDR-0009](../../product/decisions/PDR-0009-sequencia-fase-2.md).
