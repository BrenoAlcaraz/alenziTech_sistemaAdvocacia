---
id: PDR-0003
title: Áreas funcionais do Financeiro
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-06
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/phase-2-consolidated-plan-v1.docx
---

# PDR-0003 — Áreas funcionais do Financeiro

## Contexto

O módulo financeiro não pode ser representado como um único tipo
genérico de lançamento. Ele cobre situações conceitualmente diferentes:
o caixa operacional do escritório, as custas judiciais adiantadas ou
reembolsadas por clientes, as solicitações de pagamento e reembolso
feitas por usuários sem acesso ao caixa geral, e os honorários
advocatícios a receber.

## Problema

Tratar todas essas situações como um único tipo de lançamento financeiro
gera confusão de categorias (por exemplo, custas judiciais aparecendo
como categoria comum de despesa do escritório), dificulta aplicar
regras diferentes de visibilidade e responsabilidade, e impede modelar
corretamente conceitos com ciclos de vida distintos, como uma solicitação
que passa por análise antes de virar despesa efetiva.

## Decisão

O Financeiro é composto por quatro áreas funcionais distintas, que se
relacionam entre si mas não devem ser tratadas conceitualmente como um
único tipo genérico de lançamento:

1. financeiro geral do escritório;
2. custas judiciais;
3. solicitações de pagamento e reembolso;
4. honorários advocatícios.

Este PDR não obriga a existência de uma tabela física por área — a
decisão de modelagem física (uma tabela, várias tabelas, ou um modelo
compartilhado com especializações) pertence à arquitetura e à
implementação, não a este PDR de produto.

## Regras obrigatórias

**Financeiro geral do escritório**

- Representa receitas e despesas operacionais do escritório.
- Custas processuais não são uma categoria comum do financeiro geral;
  elas pertencem à área específica de custas judiciais.
- As categorias de receita e de despesa disponíveis devem ser
  condicionadas ao tipo do lançamento (receita ou despesa), evitando que
  categorias de um tipo apareçam para o outro.

**Modalidades de lançamento**

Todo lançamento do financeiro geral segue uma das três modalidades:

- único;
- parcelado;
- recorrente.

**Parcelado**

- O lançamento parcelado registra quantidade de parcelas, periodicidade
  e primeiro vencimento.
- O sistema gera ocorrências individuais vinculadas à mesma origem.

**Recorrente**

- O lançamento recorrente registra periodicidade e primeiro vencimento.
- Registra data final ou duração, quando houver, ou indicação de prazo
  indeterminado.
- Cada ocorrência recorrente nasce como um lançamento independente,
  vinculado à mesma origem recorrente.
- Cada ocorrência nasce inicialmente pendente, salvo quando for
  registrada como já realizada, conforme as regras de previsto e
  realizado do [PDR-0004](PDR-0004-previsto-e-realizado.md).
- Cancelar uma recorrência impede apenas as gerações futuras.
- Itens já realizados (pagos ou recebidos) não são apagados nem
  reescritos quando a recorrência é cancelada.

As periodicidades específicas disponíveis (mensal, anual, semanal,
quinzenal, trimestral, semestral, personalizada) não são decididas por
este PDR — essa decisão permanece em aberto em
[OPEN-001](../open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão).

## Consequências

- O módulo financeiro passa a ser tratado, em nível de produto, como
  quatro áreas relacionadas, e não como uma lista única de lançamentos.
- Custas judiciais deixam de concorrer como categoria dentro do
  financeiro geral.
- A distinção entre único, parcelado e recorrente passa a ser uma regra
  de produto obrigatória, com consequências diferentes para geração de
  ocorrências e para cancelamento.
- Fica estabelecido que cancelar uma recorrência não pode apagar ou
  reescrever histórico já realizado, o que impacta a modelagem de dados
  e a lógica de cancelamento.
- A decisão de modelagem física (quantidade de tabelas, herança,
  campos compartilhados) permanece aberta para a arquitetura, que deve
  respeitar a separação conceitual das quatro áreas.

## Alternativas ou regras substituídas

Não há conflito relevante entre esta decisão e as fontes anteriores. O
plano técnico consolidado (`phase-2-consolidated-plan-v1.docx`) já
recomendava separar custas processuais das despesas gerais do
escritório e distinguir lançamentos únicos, parcelados e recorrentes, o
que é compatível com esta decisão.

## Fora do escopo desta decisão

- Definição das periodicidades específicas disponíveis na primeira
  versão: pertence a [OPEN-001](../open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão).
- Modelagem física de tabelas, models ou migrations: pertence à
  arquitetura e à implementação.
- Regras de previsto e realizado, que são tratadas em
  [PDR-0004](PDR-0004-previsto-e-realizado.md).
- Regras específicas de custas por cliente, que são tratadas em
  [PDR-0005](PDR-0005-custas-por-cliente.md).
- Regras específicas de solicitações financeiras, que são tratadas em
  [PDR-0006](PDR-0006-solicitacoes-financeiras.md).
- Regras específicas de honorários, que são tratadas em
  [PDR-0007](PDR-0007-honorarios-manuais-antes-ia.md).

## Critérios de aceite funcionais

- O produto trata financeiro geral, custas judiciais, solicitações de
  pagamento/reembolso e honorários como áreas funcionais distintas.
- Custas processuais não aparecem como opção de categoria dentro do
  financeiro geral.
- Ao selecionar "receita", somente categorias de receita ficam
  disponíveis; ao selecionar "despesa", somente categorias de despesa
  ficam disponíveis.
- É possível registrar um lançamento como único, parcelado ou
  recorrente.
- Um lançamento parcelado gera ocorrências individuais vinculadas à
  mesma origem, a partir de quantidade de parcelas, periodicidade e
  primeiro vencimento.
- Um lançamento recorrente gera ocorrências a partir de periodicidade e
  primeiro vencimento, respeitando data final, duração ou prazo
  indeterminado.
- As ocorrências recorrentes são individualmente identificáveis.
- A confirmação ou o cancelamento de uma ocorrência não reescreve as
  demais ocorrências da mesma recorrência.
- Cada ocorrência futura é gerada inicialmente como pendente.
- Cancelar uma recorrência impede novas ocorrências futuras, mas não
  apaga nem reescreve ocorrências já pagas ou recebidas.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [phase-2-consolidated-plan-v1.docx](../../history/source-material/phase-2-consolidated-plan-v1.docx)
