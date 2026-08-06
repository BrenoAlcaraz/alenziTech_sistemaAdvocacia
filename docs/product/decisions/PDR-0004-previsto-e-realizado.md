---
id: PDR-0004
title: Previsto e realizado
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-06
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/phase-1-functional-feedback.docx
---

# PDR-0004 — Previsto e realizado

## Contexto

O financeiro precisa distinguir entre um lançamento que está apenas
previsto (ainda não pago ou recebido) e um lançamento que já foi
efetivamente liquidado. Sem essa distinção, o caixa exibido ao usuário
pode ficar incorreto, misturando valores pendentes com valores já
confirmados.

## Problema

Se uma despesa ou receita pendente altera imediatamente o saldo exibido
como realizado, o painel financeiro deixa de refletir o caixa real do
escritório, o que compromete a confiabilidade do módulo financeiro como
fonte de verdade sobre a situação financeira do escritório.

## Decisão

Todo lançamento financeiro possui duas dimensões distintas: prevista e
realizada.

- Uma pendência entra em contas a pagar ou a receber, conforme o tipo do
  lançamento.
- Uma pendência não altera o caixa realizado.
- Somente a confirmação efetiva de pagamento ou recebimento altera o
  saldo realizado.

## Regras obrigatórias

O painel financeiro deve apresentar, no mínimo, os seguintes
indicadores:

- a receber;
- a pagar;
- recebido no período;
- pago no período;
- saldo realizado;
- saldo previsto.

Regras de datas obrigatórias:

- todo lançamento possui uma data de competência;
- um lançamento pendente possui vencimento;
- uma parcela possui vencimento;
- uma ocorrência recorrente possui vencimento;
- um item pago possui data de pagamento;
- um item recebido possui data de recebimento;
- o vencimento pode não se aplicar a um lançamento já realizado, desde
  que existam competência e data de realização (pagamento ou
  recebimento) adequadas para posicioná-lo corretamente nos períodos.

## Consequências

- O saldo realizado passa a depender exclusivamente de confirmações de
  pagamento ou recebimento, e não da simples existência do lançamento.
- O modelo de dados do financeiro precisa suportar, para cada
  lançamento, a distinção entre estado previsto e estado realizado, com
  datas específicas para cada momento.
- A ausência de vencimento passa a ser uma exceção válida apenas para
  lançamentos já realizados, e não uma regra geral — todo lançamento
  pendente, parcela ou ocorrência recorrente exige vencimento.
- Os indicadores do painel financeiro passam a ter uma definição
  funcional obrigatória, o que impacta qualquer implementação de
  dashboard financeiro.

## Alternativas ou regras substituídas

Não há conflito relevante com as fontes anteriores. O feedback funcional
pós-Fase 1 (`phase-1-functional-feedback.docx`) já descrevia a mesma
lógica: todo lançamento nasce pendente e só é contabilizado como entrada
ou saída efetiva após confirmação de pagamento. A decisão consolidada
posterior formaliza essa lógica e detalha as regras de data associadas,
sem contradizer a fonte anterior.

## Fora do escopo desta decisão

- A definição das quatro áreas funcionais do financeiro (financeiro
  geral, custas, solicitações e honorários): tratada em
  [PDR-0003](PDR-0003-areas-funcionais-financeiro.md).
- Regras específicas de custas por cliente: tratadas em
  [PDR-0005](PDR-0005-custas-por-cliente.md).
- Modelagem técnica dos campos de data e dos indicadores no banco de
  dados: pertence à arquitetura e à implementação.
- Gráficos, relatórios ou exportações baseados nesses indicadores: não
  são definidos por este PDR.

## Critérios de aceite funcionais

- Um lançamento pendente aparece em "a pagar" ou "a receber", conforme
  seu tipo, sem alterar o saldo realizado.
- O saldo realizado só se altera quando um pagamento ou recebimento é
  efetivamente confirmado.
- O painel financeiro exibe, no mínimo: a receber, a pagar, recebido no
  período, pago no período, saldo realizado e saldo previsto.
- Todo lançamento possui data de competência.
- Lançamentos pendentes, parcelas e ocorrências recorrentes possuem
  vencimento.
- Lançamentos pagos possuem data de pagamento; lançamentos recebidos
  possuem data de recebimento.
- Um lançamento já realizado pode não possuir vencimento, desde que
  possua competência e data de realização registradas.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [phase-1-functional-feedback.docx](../../history/source-material/phase-1-functional-feedback.docx)
