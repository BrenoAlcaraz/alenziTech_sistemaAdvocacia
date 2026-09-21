---
id: PDR-0031
title: Custas judiciais por grupo de clientes
status: accepted
owner: product-and-engineering
decision_date: 2026-09-21
last_reviewed: 2026-09-21
supersedes: []
complements:
  - PDR-0005
source_files: []
---

# PDR-0031 — Custas judiciais por grupo de clientes

## Contexto

Revisão do sócio de 2026-09-20: uma holding adianta valor para custas de
várias subsidiárias. O saldo por cliente (PDR-0005) não representa isso.

## Decisão

- Um **grupo** tem nome (único) e membros (clientes). O saldo do grupo usa
  a mesma fórmula do PDR-0005, sobre os lançamentos do grupo.
- Um cliente pertence a no máximo um grupo e só entra com **saldo
  individual zero**. Não há migração de saldo individual para o grupo nem
  distribuição automática do crédito entre membros.
- Cliente em grupo some da lista individual de custas e aparece só dentro
  do grupo; o grupo é listado como um cliente comum, pelo saldo próprio.
- Crédito do grupo não tem cliente. Débito no grupo exige o **membro**;
  o processo é opcional, mas só de membro. Na ficha do membro o débito
  aparece como "pago pelo saldo do Grupo X" e não afeta o saldo individual.
- Todo lançamento novo de um membro (inclusive gerado pelo sistema, como
  custa paga via solicitação) cai no saldo do grupo; custa do grupo não é
  reembolsável individualmente.
- Remover membro ou apagar grupo só sem lançamentos vinculados — o
  histórico nunca é reescrito.
- Na tela de custas: busca por nome/documento do cliente, nome do grupo e
  nome dos membros; filtro de saldo (com crédito, em débito, sem saldo
  pendente). No formulário de débito "Adiantado pelo escritório", aviso
  informativo com saldo atual e após o débito (inclusive negativo); não
  altera a regra do saldo.
- Mesma autorização das custas (nível de dados do Financeiro); sem
  habilitação nova.

## Consequências

- Totais do financeiro (`custas_a_recuperar`) contam o débito do grupo
  pelo saldo do grupo, nunca pelo do membro.
- Crédito do grupo gera a receita "Reembolso" (sem cliente) no financeiro
  geral, como o Creditar individual.
- Reembolso individual de custa adiantada antes de o cliente entrar no
  grupo segue possível pela regra atual e não é tratado aqui.
