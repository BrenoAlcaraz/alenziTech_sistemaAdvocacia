---
title: Política de documentação
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Política de documentação

## Objetivo

Definir como os documentos deste repositório são categorizados,
nomeados, mantidos e utilizados, de modo que pessoas e agentes de IA
possam identificar consistentemente o que é vigente, o que é decisão
formal e o que é apenas histórico.

## Categorias documentais

### Canônica

Descreve o comportamento, a arquitetura ou a regra vigente do sistema.
É a referência ativa para como o sistema deve funcionar.

### Decisão

PDRs (product decision records) e ADRs (architecture decision records)
que explicam decisões aprovadas, seu contexto e suas consequências.

### Operacional

Procedimentos de desenvolvimento, testes, migrations e uso de agentes
de IA no dia a dia do projeto.

### Entrega

Estado atual (current-state), roadmap, tarefas, planos e relatórios de
implementação.

### Histórica

Materiais preservados para rastreabilidade. Não possuem autoridade sobre
o estado atual do sistema.

## Estados permitidos

- **draft** — rascunho inicial, ainda em elaboração, não deve ser usado
  como referência vigente.
- **under-review** — em revisão, conteúdo sujeito a mudanças antes da
  aprovação.
- **accepted** — aprovado como decisão, mas ainda não necessariamente
  incorporado como documentação canônica corrente.
- **canonical** — vigente e autoritativo para o comportamento ou decisão
  que descreve.
- **superseded** — substituído por outro documento, mantido apenas para
  rastreabilidade.
- **historical** — preservado como contexto, sem autoridade sobre o
  estado atual.

## Front matter obrigatório

Documentos canônicos novos devem possuir, no mínimo, os seguintes campos
em front matter YAML:

- `title`
- `status`
- `owner`
- `last_reviewed`

PDRs e ADRs possuirão adicionalmente:

- `id`
- `decision_date`
- `supersedes`, quando aplicável

## Regras de atualização

- Documentos históricos não são reescritos para parecer atuais.
- Mudanças de produto atualizam a especificação e, quando necessário,
  criam ou substituem um PDR.
- Mudanças arquiteturais relevantes exigem um ADR.
- O current-state deve indicar o commit verificado ao qual corresponde.
- O roadmap não deve duplicar o conteúdo de especificações.
- Tarefas não devem redefinir silenciosamente decisões já aprovadas.
- A documentação deve ser atualizada na mesma entrega do código
  relacionado a ela.

## Código versus documentação

Código e testes são evidência da implementação real. Documentos
canônicos são a fonte do comportamento pretendido. Nenhum dos dois deve
ser alterado com o objetivo de esconder uma divergência entre eles.
Divergências devem ser registradas explicitamente e resolvidas por
decisão humana, não silenciadas.

## Regra de não duplicação

Cada regra deve possuir uma única fonte canônica principal. Outros
documentos que precisem referenciá-la devem apontar para essa fonte, não
copiar seu conteúdo integral.

## Uso por agentes de IA

Agentes de IA que trabalham neste repositório devem:

- Ler apenas os documentos necessários para a tarefa em questão.
- Não usar `docs/history/` como instrução vigente.
- Não preencher lacunas de informação com suposições.
- Parar diante de contradições relevantes entre documentos ou entre
  documentação e código.
- Citar caminhos de arquivos ao justificar decisões.
- Não alterar requisitos durante a implementação.

## Revisão periódica

Documentos canônicos devem ser revisados quando:

- O comportamento que descrevem mudar.
- Uma decisão relacionada for substituída.
- O código revelar uma divergência em relação ao documento.
- Uma nova fase ou módulo for iniciado.
- Houver preparação para produção.
