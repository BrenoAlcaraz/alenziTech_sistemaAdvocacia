---
id: PDR-0005
title: Custas por cliente
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-06
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/phase-1-functional-feedback.docx
---

# PDR-0005 — Custas por cliente

## Contexto

Custas judiciais são valores pagos a tribunais para movimentar um
processo. Elas podem ser adiantadas pelo escritório e depois
reembolsadas pelo cliente, adiantadas pelo próprio cliente como crédito,
ou pagas diretamente pelo cliente. Essa dinâmica é diferente da de uma
despesa comum do escritório e precisa de um controle de saldo por
cliente.

## Problema

Sem uma área específica e uma fórmula clara de saldo, não é possível
saber, para cada cliente, quanto crédito ele mantém junto ao escritório
para cobrir custas, nem distinguir corretamente entre valores que
afetam esse saldo e valores que não afetam.

## Decisão

Custas judiciais ficam em uma área separada do caixa geral do
escritório. A tela inicial dessa área lista os clientes e o saldo de
custas de cada um. Cada cliente possui histórico de lançamentos de
custas e de créditos depositados.

Um lançamento de custa pode se relacionar a cliente e a processo, e
registra: descrição, valor, data, responsável pelo pagamento, boleto e
comprovante, quando aplicável. O responsável pelo pagamento de uma custa
pode ser o escritório ou o cliente.

A fórmula do saldo de custas é:

```
saldo de custas =
  créditos depositados pelo cliente
  − custas pagas pelo escritório
```

## Regras obrigatórias

- Uma custa paga diretamente pelo próprio cliente aparece no histórico
  de lançamentos do cliente, para fins de controle.
- Uma custa paga diretamente pelo cliente não reduz o crédito mantido
  pelo escritório.
- Uma custa paga diretamente pelo cliente não altera o saldo entre
  cliente e escritório.
- O cálculo do saldo de custas deve ser implementado e testado no
  backend, não apenas apresentado ou calculado no template.

## Consequências

- O módulo de custas precisa manter, para cada cliente, um histórico
  separado de lançamentos (custas) e de créditos (valores adiantados).
- A fórmula do saldo passa a ser uma regra de produto obrigatória, e não
  uma escolha livre de implementação: apenas créditos depositados pelo
  cliente e custas pagas pelo escritório entram no cálculo.
- Custas pagas diretamente pelo cliente exigem tratamento diferenciado:
  são registradas para controle, mas não participam da fórmula de
  saldo.
- A exigência de cálculo e teste no backend implica cobertura de testes
  automatizados específica para essa regra de saldo.

## Alternativas ou regras substituídas

Não há conflito relevante com as fontes anteriores. O feedback funcional
pós-Fase 1 (`phase-1-functional-feedback.docx`) já descrevia a mesma
lógica de listar clientes com saldo (crédito) e abas de lançamento e
crédito, incluindo a distinção entre custa paga pelo escritório e custa
paga pelo próprio cliente. A decisão consolidada posterior formaliza
essa lógica e adiciona explicitamente a exigência de cálculo e teste no
backend.

## Fora do escopo desta decisão

- A definição das quatro áreas funcionais do financeiro: tratada em
  [PDR-0003](PDR-0003-areas-funcionais-financeiro.md).
- Regras de previsto e realizado aplicadas ao financeiro geral: tratadas
  em [PDR-0004](PDR-0004-previsto-e-realizado.md).
- Modelagem técnica de tabelas, models ou migrations para custas e
  créditos: pertence à arquitetura e à implementação.
- Regras de permissão sobre quem pode registrar ou visualizar custas de
  um cliente: fora do escopo deste PDR de produto.

## Critérios de aceite funcionais

- A área de custas exibe, na tela inicial, a lista de clientes com o
  saldo de custas de cada um.
- Cada cliente possui histórico de lançamentos de custas e de créditos
  depositados.
- Um lançamento de custa pode ser associado a cliente e a processo, com
  descrição, valor, data, responsável pelo pagamento, boleto e
  comprovante, quando aplicável.
- O responsável pelo pagamento de uma custa pode ser registrado como
  escritório ou como cliente.
- O saldo de custas de um cliente é igual aos créditos depositados por
  ele menos as custas pagas pelo escritório em seu nome.
- Uma custa paga diretamente pelo cliente aparece no histórico do
  cliente, mas não altera o saldo de custas calculado.
- O cálculo do saldo de custas possui cobertura de testes automatizados
  no backend.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [phase-1-functional-feedback.docx](../../history/source-material/phase-1-functional-feedback.docx)
