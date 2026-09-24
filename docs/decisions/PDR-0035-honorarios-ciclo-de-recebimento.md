---
id: PDR-0035
title: Honorários — ciclo de recebimento
status: accepted
owner: product-and-engineering
decision_date: 2026-09-23
last_reviewed: 2026-09-23
supersedes: []
complements:
  - PDR-0004
  - PDR-0007
  - PDR-0022
  - PDR-0032
source_files: []
---

# PDR-0035 — Honorários: ciclo de recebimento

## Contexto

Pedido de adicionar ao cadastro de honorário os campos status
pago/pendente, vencimento, data de pagamento, contrato e comprovante,
e, no parcelado, o status e a data da 1ª parcela. O sistema já separava
previsão (cadastro) e recebimento (confirmação exclusiva do
Administrador, com parcial — PDR-0022). O honorário parcelado/recorrente,
porém, era baixado pelos lançamentos gerados, sem essa restrição.

## Decisão

Previsão e recebimento continuam separados. O ciclo é PREVISÃO →
VENCIMENTO → RECEBIMENTO → COMPROVAÇÃO:

- **Status nunca é digitado.** A situação exibida é calculada: a vencer,
  vencido (vencimento passou e há saldo), parcialmente recebido,
  recebido, cancelado. No parcelado/recorrente, pelas parcelas.
- **"Já recebido" no cadastro** (no parcelado/recorrente, a 1ª parcela)
  é um atalho: cadastra e registra o recebimento na mesma operação, com
  data (não futura) e comprovante opcional. Só para o Administrador, só
  no contratual com valor. Recebimento parcial continua pela
  confirmação.
- **Todo recebimento de honorário é exclusivo do Administrador**,
  inclusive baixar, reabrir ou excluir parcela/ocorrência gerada no
  Financeiro. Cada recebimento notifica o advogado responsável pelo
  processo.
- **O recebimento de honorário de valor único não se desfaz pelo
  lançamento** (nem pelo Administrador): o `valor_recebido` do honorário
  ficaria errado. Recebimentos confirmados ficam vinculados ao
  honorário.
- **Documento de origem** (contrato ou decisão) é opcional e fica no
  honorário; o **comprovante** é opcional e fica em cada recebimento;
  recebimento sem comprovante é sinalizado.
- Sucumbência pode ficar sem vencimento. Registros antigos não são
  revisados.

## Alternativas descartadas

- Status pago/pendente editável no cadastro: fazia o caixa realizado
  depender de um campo que qualquer usuário edita (contraria PDR-0004)
  e não comporta recebimento parcial.
- "Usuário informa, Administrador confere": mais controle, mas cria
  uma fila de conferência; fica para quando houver demanda.

## Fora do escopo

- Recebimento parcial de uma parcela.
- Desfazer recebimento de honorário com recálculo.
- Revisão de recebimentos antigos (confirmações anteriores a este PDR
  não estão vinculadas ao honorário).
