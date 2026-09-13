---
id: PDR-0021
title: Periodicidades da recorrência financeira
status: accepted
owner: product-and-engineering
decision_date: 2026-09-13
last_reviewed: 2026-09-13
supersedes: []
complements:
  - PDR-0003
source_files: []
---

# PDR-0021 — Periodicidades da recorrência financeira

## Contexto

`docs/modules/financeiro.md` já define que todo lançamento do financeiro
geral é único, parcelado ou recorrente, mas as periodicidades
disponíveis na primeira versão ficaram registradas como decisão em
aberto (`OPEN-001` em `docs/STATUS.md`), bloqueando o detalhamento de UI
e a migration de recorrência/parcelamento.

## Problema

Sem um conjunto fechado de periodicidades, não é possível desenhar o
formulário de lançamento (bloco de periodicidade/dia de vencimento/
duração) nem a migration que sustenta parcelamento e recorrência.

## Decisão

A primeira versão do financeiro geral oferece apenas três
periodicidades:

- **mensal**;
- **anual**;
- **parcelamento mensal** (uso específico da classificação "parcelado":
  quantidade de parcelas + primeiro vencimento, cada parcela mensal a
  partir daí).

Semanal, quinzenal, trimestral, semestral e periodicidade personalizada
ficam fora desta versão.

## Regras obrigatórias

- Lançamento **parcelado** usa sempre periodicidade mensal entre
  parcelas — não expõe escolha de periodicidade, só quantidade de
  parcelas e primeiro vencimento (conforme já descrito em
  `docs/modules/financeiro.md`).
- Lançamento **recorrente** escolhe entre mensal ou anual, mais
  duração: quantidade de ocorrências, data final, ou indeterminado.
- Nenhuma periodicidade fora desse conjunto (mensal/anual/parcelamento
  mensal) é aceita nesta versão — validação de produto, não só de UI.

## Consequências

- `docs/STATUS.md` remove `OPEN-001` das decisões em aberto.
- `docs/modules/financeiro.md` deixa de citar a periodicidade como
  decisão em aberto.
- A migration de recorrência/parcelamento do financeiro geral pode ser
  implementada com esse conjunto fechado.
- Ampliar para semanal/quinzenal/trimestral/semestral/personalizada
  exige novo PDR — não é implementação silenciosa.

## Alternativas ou regras substituídas

`OPEN-001` apresentava duas alternativas: o conjunto mínimo aqui
adotado, ou um conjunto ampliado (mensal/anual/parcelamento +
semanal/quinzenal/trimestral/semestral/personalizada). A alternativa
ampliada foi descartada nesta rodada por abrir escopo de campos e
testes de migration sem necessidade comprovada agora; pode ser retomada
em PDR futuro se surgir demanda real.

## Fora do escopo desta decisão

- Periodicidades de custas judiciais ou de solicitações financeiras —
  essas áreas não têm recorrência (PDR-0005/PDR-0006).
- Modelagem técnica de tabelas/migrations — arquitetura e
  implementação.
- Regras de permissão sobre quem pode criar lançamento recorrente —
  fora de escopo deste PDR.

## Critérios de aceite funcionais

- Cadastro de lançamento recorrente só aceita periodicidade mensal ou
  anual.
- Cadastro de lançamento parcelado não pergunta periodicidade — sempre
  mensal entre parcelas.
- Tentar registrar periodicidade fora desse conjunto (ex.: quinzenal)
  falha na validação de produto.

## Fontes

- Conversa desta sessão (spec `specs/financeiro-visao-grafica-navegacao-temporal.md`,
  apagada após a promoção deste PDR, conforme
  [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
