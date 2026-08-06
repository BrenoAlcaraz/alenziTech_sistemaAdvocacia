---
id: PDR-0007
title: Honorários manuais antes da IA
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-06
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/product-vision-original.docx
---

# PDR-0007 — Honorários manuais antes da IA

## Contexto

Havia a possibilidade de que o controle de honorários advocatícios só
fosse viável a partir de identificação automática por IA (por exemplo,
reconhecendo sentenças que condenam honorários sucumbenciais). Era
necessário decidir se essa dependência de IA seria um pré-requisito para
existir a funcionalidade de honorários.

## Problema

Tornar o controle de honorários dependente de IA atrasaria a entrega da
funcionalidade para depender de um pré-requisito — IA jurídica — que
ainda não está consolidado, conforme registrado em
[PDR-0008](PDR-0008-ia-apos-nucleo-funcional.md).

## Decisão

A funcionalidade de honorários advocatícios não depende de inteligência
artificial. O cadastro manual vem primeiro.

Um honorário pode se relacionar a processo e a cliente, e o cadastro
deve permitir registrar:

- tipo;
- valor estimado;
- valor efetivo;
- processo;
- cliente, quando aplicável;
- data prevista;
- data recebida;
- status;
- observações.

## Regras obrigatórias

- O cadastro de honorários funciona de forma manual, sem depender de
  nenhuma funcionalidade de IA para existir ou operar.
- A IA jurídica futura pode identificar honorários em documentos e
  sugerir um cadastro correspondente.
- A sugestão da IA não substitui a regra funcional de cadastro manual
  nem dispensa a confirmação humana do lançamento.

## Consequências

- A entrega de honorários pode ser priorizada e concluída
  independentemente do andamento da IA jurídica.
- O cadastro de honorários precisa dos campos de valor estimado e valor
  efetivo separados, o que implica acompanhar a evolução de um
  honorário previsto até seu recebimento.
- Uma futura integração com IA para sugestão automática de honorários
  deverá se conectar a este cadastro manual como uma camada adicional,
  não como substituição.

## Alternativas ou regras substituídas

O material de visão inicial (`product-vision-original.docx`) descrevia
uma visão em que o próprio sistema já "sabe reconhecer" processos com
honorários sucumbenciais transitados em julgado a favor do usuário, sem
mencionar explicitamente um cadastro manual anterior. A decisão
consolidada posterior estabelece que o cadastro manual é o ponto de
partida obrigatório, e que a identificação automática por IA é uma
evolução posterior e opcional — não um pré-requisito. Nesse ponto, a
decisão posterior prevalece sobre a visão inicial.

## Fora do escopo desta decisão

- O desenho da funcionalidade de identificação automática de honorários
  por IA: fora do escopo, tratado apenas como evolução futura mencionada
  neste PDR.
- A relação entre honorários e o restante do módulo financeiro: tratada
  em [PDR-0003](PDR-0003-areas-funcionais-financeiro.md).
- Modelagem técnica de tabelas, models ou migrations para honorários:
  pertence à arquitetura e à implementação.
- Regras de permissão sobre quem pode cadastrar ou visualizar
  honorários: fora do escopo deste PDR de produto.

## Critérios de aceite funcionais

- É possível cadastrar um honorário manualmente, sem depender de
  nenhuma funcionalidade de IA.
- O cadastro de honorário permite registrar tipo, valor estimado, valor
  efetivo, processo, cliente (quando aplicável), data prevista, data
  recebida, status e observações.
- Um honorário pode existir sem qualquer sugestão ou identificação
  automática por IA.
- Quando existir, uma sugestão de IA para honorários resulta em um
  cadastro pendente de confirmação humana, não em um lançamento
  automático definitivo.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [product-vision-original.docx](../../history/source-material/product-vision-original.docx)
