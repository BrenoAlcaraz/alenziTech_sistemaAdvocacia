---
title: Decisões de produto em aberto
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Decisões de produto em aberto

Este documento lista somente as decisões de produto que ainda não foram
efetivamente aprovadas. Decisões já aprovadas, mesmo quando a fonte
original registrava uma recomendação antes da aprovação, são formalizadas
em [PDRs](decisions/README.md) e não aparecem aqui.

## OPEN-001 — Periodicidades financeiras da primeira versão

Status: open

### Contexto

O módulo financeiro precisa suportar lançamentos parcelados e
recorrentes, o que exige a definição de quais periodicidades estarão
disponíveis desde a primeira versão.

### Pergunta

A primeira versão oferecerá apenas mensal, anual e parcelamento mensal,
ou também semanal, quinzenal, trimestral, semestral e personalizada?

### Opções identificadas

- oferecer apenas mensal, anual e parcelamento mensal na primeira
  versão;
- oferecer também semanal, quinzenal, trimestral, semestral e
  personalizada desde o início.

### Recomendação registrada nas fontes

Mensal, anual e quantidade de parcelas na primeira versão.

### Impacto da decisão

Define o desenho dos campos de periodicidade e das regras de geração de
ocorrências recorrentes e parceladas no módulo financeiro.

### Bloqueia

Detalhamento e migrations de recorrência financeira.

### Decisão final

Pendente.

## OPEN-002 — Etapas de aprovação das solicitações financeiras

Status: open

### Contexto

Solicitações de pagamento e reembolso feitas por usuários sem acesso ao
caixa geral precisam de um fluxo de status até a efetivação do
pagamento.

### Pergunta

O fluxo será:

solicitada → em análise → aprovada → paga

ou o Financeiro poderá concluir diretamente:

solicitada → paga ou rejeitada?

### Opções identificadas

- manter uma etapa de análise/aprovação separada da execução do
  pagamento;
- permitir que o Financeiro conclua diretamente entre solicitada e
  paga ou rejeitada, sem etapa intermediária de aprovação.

### Recomendação registrada nas fontes

Manter uma etapa de aprovação separada da execução do pagamento.

### Impacto da decisão

Define a modelagem final do status das solicitações financeiras e as
regras de transição entre estados.

### Bloqueia

Modelagem final do status das solicitações e regras de transição.

### Decisão final

Pendente.

## OPEN-003 — Espelhamento da assinatura SaaS no Financeiro

Status: open

### Contexto

A cobrança da assinatura da plataforma SaaS é hoje um conceito distinto
das despesas operacionais registradas pelo escritório no módulo
financeiro do tenant.

### Pergunta

A cobrança da plataforma será automaticamente lançada no financeiro do
tenant, permanecerá somente no Billing ou poderá ser espelhada
opcionalmente?

### Opções identificadas

- lançar automaticamente a cobrança da assinatura como despesa
  recorrente no financeiro do tenant;
- manter a cobrança somente em `saas_billing`, sem qualquer lançamento
  automático no financeiro do tenant;
- manter a cobrança em `saas_billing` e oferecer futuramente uma opção
  de espelhamento, sem criação automática por padrão.

### Recomendação registrada nas fontes

Manter a cobrança em `saas_billing` e oferecer futuramente uma opção de
espelhamento, sem criação automática por padrão.

### Impacto da decisão

Define se e como haverá integração entre `saas_billing` e o financeiro
do tenant.

### Bloqueia

Integração entre `saas_billing` e o financeiro do tenant.

### Decisão final

Pendente.
