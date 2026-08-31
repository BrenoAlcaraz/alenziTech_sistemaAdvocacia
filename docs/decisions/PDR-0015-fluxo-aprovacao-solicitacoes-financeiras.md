---
id: PDR-0015
title: Fluxo de aprovação das solicitações financeiras
status: accepted
owner: product-and-engineering
decision_date: 2026-08-31
last_reviewed: 2026-08-31
supersedes: []
source_files: []
---

# PDR-0015 — Fluxo de aprovação das solicitações financeiras

## Contexto

OPEN-002, anteriormente registrado em `docs/product/open-decisions.md`,
mantinha pendente a definição do fluxo de status de uma solicitação
de pagamento ou reembolso: manter uma etapa de análise/aprovação separada
da execução do pagamento, ou permitir que o Financeiro conclua diretamente
entre solicitada e paga/rejeitada.

## Decisão

O fluxo de status de uma solicitação financeira (pagamento ou reembolso) é:

```text
solicitada → em análise → aprovada → paga
```

com rejeição como desfecho alternativo da etapa "em análise":

```text
solicitada → em análise → rejeitada
```

Uma solicitação rejeitada não avança para "aprovada" nem para "paga". Uma
solicitação só chega a "paga" depois de passar por "aprovada".

Esta decisão confirma a recomendação registrada no antigo OPEN-002 e no
fluxo de referência de
[PDR-0006](PDR-0006-solicitacoes-financeiras.md). O protótipo funcional
`docs/prototipos/financeiro-prototipo.html` demonstra um fluxo mais curto
(`a_pagar`/`paga`); no conflito, esta decisão posterior é a fonte vigente.

## Consequências

- o modelo de status de solicitação financeira implementa cinco estados
  possíveis: `solicitada`, `em_analise`, `aprovada`, `rejeitada` e `paga`;
- `docs/product/modules/financeiro.md` deixa de referenciar OPEN-002 como
  pendente nesse ponto específico;
- OPEN-002 é removido de `docs/product/open-decisions.md`, conforme a própria regra
  desse documento: decisões aprovadas não permanecem listadas como em
  aberto.

## Fora do escopo desta decisão

- quem pode mover uma solicitação entre estados (papel/habilitação) —
  permanece regido por
  [ARCHITECTURE.md](../ARCHITECTURE.md)
  e pelo alcance de habilitação financeira já descrito em
  [financeiro.md](../modules/financeiro.md);
- o momento exato em que uma solicitação passa a compor o indicador "a
  pagar" — permanece ponto em aberto de `financeiro.md`;
- notificação ao solicitante em cada mudança de estado, além do já descrito
  em `financeiro.md` (visualização do comprovante após pagamento).

## Critérios de aceite funcionais

- uma solicitação nasce no estado `solicitada`;
- uma solicitação em `em_analise` só avança para `aprovada` ou
  `rejeitada`, nunca diretamente para `paga`;
- uma solicitação só atinge `paga` depois de passar por `aprovada`;
- uma solicitação `rejeitada` não pode ser reaberta para `aprovada` ou
  `paga` sem nova solicitação.

## Fontes

- decisão direta do Product Owner registrada em 2026-08-31, durante a
  revisão estrutural de documentação a partir dos protótipos funcionais;
- [PDR-0006 — Solicitações financeiras](PDR-0006-solicitacoes-financeiras.md);
- antigo OPEN-002, removido de `docs/product/open-decisions.md` após esta
  decisão;
- [docs/prototipos/financeiro-prototipo.html](../prototipos/financeiro-prototipo.html)
  (protótipo funcional navegável de alta fidelidade; somente o fluxo curto
  de status foi substituído neste ponto).
