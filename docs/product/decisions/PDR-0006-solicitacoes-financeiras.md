---
id: PDR-0006
title: Solicitações financeiras
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-06
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/phase-1-functional-feedback.docx
---

# PDR-0006 — Solicitações financeiras

## Contexto

Usuários que não têm acesso ao caixa geral do escritório — por exemplo,
advogados que precisam pagar uma custa judicial ou pedir reembolso de um
gasto profissional — ainda assim precisam de uma forma de acionar o
Financeiro para que um pagamento ou reembolso seja processado.

## Problema

Sem um fluxo próprio de solicitação, esses usuários ou não têm meio
algum de pedir pagamentos e reembolsos ao Financeiro, ou precisariam de
acesso amplo ao caixa geral, o que exporia dados financeiros completos
do escritório a quem não deveria vê-los.

## Decisão

Usuários sem acesso ao caixa geral possuem uma visão financeira limitada:
podem solicitar pagamento e reembolso, mas não visualizam receitas,
despesas ou resultados completos do escritório.

**Solicitação de pagamento** — campos: descrição, valor, cliente,
processo, vencimento, boleto obrigatório, observação.

**Solicitação de reembolso** — campos: descrição, valor, cliente e
processo (quando aplicáveis), comprovante obrigatório, data do gasto,
observação.

O fluxo de referência das solicitações é:

```
solicitada → em análise → aprovada ou rejeitada → paga
```

O detalhamento final desse fluxo — se haverá uma etapa de análise
separada da aprovação, e se a rejeição pode ocorrer em qualquer etapa —
permanece dependente da decisão registrada em
[OPEN-002](../open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras).
Este PDR formaliza a existência do fluxo de solicitações e seus campos,
não o detalhamento final de seus estados intermediários.

## Regras obrigatórias

- O solicitante pode acompanhar o status da própria solicitação.
- Após o pagamento, o solicitante pode visualizar o comprovante anexado
  pelo Financeiro.
- Administrador do escritório e usuário com habilitação financeira podem
  processar (analisar, aprovar, rejeitar e pagar) solicitações.
- A criação de uma solicitação não gera automaticamente uma despesa
  realizada.
- A despesa passa a existir como realizada somente quando o pagamento
  for efetivamente processado.

## Consequências

- O produto passa a ter dois níveis de acesso ao Financeiro: acesso
  completo ao caixa geral, e acesso limitado restrito a solicitações.
- As solicitações de pagamento e reembolso precisam de anexos
  obrigatórios (boleto para pagamento, comprovante para reembolso), o
  que impacta a validação de formulário e o armazenamento de arquivos.
- Uma solicitação criada não gera automaticamente uma despesa realizada,
  e o saldo realizado só se altera quando o pagamento é efetivamente
  processado, em linha com as regras de previsto e realizado do
  [PDR-0004](PDR-0004-previsto-e-realizado.md). O momento exato em que
  uma solicitação passa a integrar o indicador "a pagar" não é decidido
  por este PDR e pode depender do detalhamento final do fluxo em
  OPEN-002.
- O detalhamento final dos estados do fluxo permanece bloqueado por
  OPEN-002, o que significa que a modelagem final de status das
  solicitações não pode ser fechada até essa decisão ser tomada.

## Alternativas ou regras substituídas

O feedback funcional pós-Fase 1 (`phase-1-functional-feedback.docx`) já
descrevia a possibilidade de advogados solicitarem pagamento de custas e
reembolso de gastos profissionais, com anexo de boleto ou comprovante
obrigatório. A decisão consolidada posterior formaliza esse
comportamento e propõe o fluxo de referência com etapa de análise, que
ainda depende de confirmação explícita registrada em OPEN-002. Não há
contradição entre as fontes; a fonte posterior detalha o que a anterior
já indicava, sem resolver integralmente o fluxo de aprovação.

## Fora do escopo desta decisão

- O detalhamento final das etapas de aprovação (análise separada da
  execução do pagamento, ou conclusão direta): pertence a
  [OPEN-002](../open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras).
- A definição das quatro áreas funcionais do financeiro: tratada em
  [PDR-0003](PDR-0003-areas-funcionais-financeiro.md).
- Regras de previsto e realizado aplicadas ao financeiro geral: tratadas
  em [PDR-0004](PDR-0004-previsto-e-realizado.md).
- Modelagem técnica de tabelas, models ou migrations para solicitações:
  pertence à arquitetura e à implementação.

## Critérios de aceite funcionais

- Um usuário sem acesso ao caixa geral consegue criar uma solicitação de
  pagamento ou de reembolso, sem visualizar receitas, despesas ou
  resultados completos do escritório.
- Uma solicitação de pagamento exige descrição, valor, cliente,
  processo, vencimento e boleto.
- Uma solicitação de reembolso exige descrição, valor, comprovante e
  data do gasto; cliente e processo são informados quando aplicáveis,
  sem serem obrigatórios.
- O solicitante consegue acompanhar o status de sua solicitação e, após
  o pagamento, visualizar o comprovante anexado pelo Financeiro.
- Administrador do escritório e usuário com habilitação financeira
  conseguem processar solicitações; demais usuários não conseguem.
- Criar uma solicitação não altera indicadores de despesa realizada; a
  despesa só se torna realizada quando o pagamento é efetivamente
  processado.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [phase-1-functional-feedback.docx](../../history/source-material/phase-1-functional-feedback.docx)
