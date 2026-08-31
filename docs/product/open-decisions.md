---
title: Decisões de produto em aberto
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-31
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

OPEN-002 (etapas de aprovação das solicitações financeiras) foi resolvida
e formalizada em
[PDR-0015 — Fluxo de aprovação das solicitações financeiras](decisions/PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md);
não aparece mais neste documento, conforme a regra do cabeçalho.
