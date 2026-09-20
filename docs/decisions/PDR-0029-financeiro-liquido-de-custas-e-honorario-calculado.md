---
id: PDR-0029
title: Financeiro líquido de custas do cliente e honorário sucumbencial calculado
status: accepted
owner: product-and-engineering
decision_date: 2026-09-19
last_reviewed: 2026-09-19
supersedes: []
complements:
  - PDR-0005
  - PDR-0006
  - PDR-0022
source_files: []
---

# PDR-0029 — Financeiro líquido de custas e honorário calculado

## Contexto

Revisão do sócio de 2026-09-19: lançamentos e Creditar não conversavam;
reembolso de cliente e custas pagas pelo cliente distorciam receita e
despesa; a aba Honorários não seguia o protótipo.

## Decisão

1. **Reembolso de cliente é crédito, não receita.** Receita com
   categoria "Reembolso" (exige cliente) vira crédito nas custas
   judiciais do cliente quando recebida (`pago`); reaberta, cancelada,
   excluída ou recategorizada, o crédito some. Creditar cria essa mesma
   receita — o lançamento é a única origem.
2. **Custas do cliente entram só pelo saldo devedor.** Despesas de
   categoria custa/solicitação de pagamento com cliente não contam como
   despesa; conta o saldo devedor (adiantado − creditado) na janela.
   Custa paga pelo cliente nunca conta. Reembolso de custa adiantada
   (botão na custa, com comprovante) gera o crédito e baixa o saldo.
   Só para quem vê todos os dados (`dados_todos`).
3. **Saldo previsto** = a receber + recebido − a pagar − pagos.
4. **Honorário sucumbencial calculado:** valor-base (percentual sobre a
   causa ou valor fixo) corrigido conforme o devedor — comum: índice
   (INPC/IGP-M/Selic) + juros de 1% a.m., cada um desde a sua data; ente
   estatal: só a taxa unificada. Êxito contratual opcional incide sobre o
   valor ganho já corrigido. A taxa do índice é informada à mão (sem
   integração externa, como no PDR-0022). O total nunca é gravado: é
   recalculado a cada leitura. Estende o PDR-0022, que não previa a
   distinção de devedor.

## Fora do escopo

Integração com índices externos (IBGE/BCB).
