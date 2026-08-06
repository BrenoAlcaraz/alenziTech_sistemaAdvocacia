---
title: Documentação do Breno - LawSystem
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Documentação do Breno - LawSystem

## Objetivo

Este diretório contém as fontes versionadas utilizadas para produto,
arquitetura, segurança, entrega e desenvolvimento do Breno - LawSystem.
É o ponto de partida para qualquer pessoa ou agente que precise entender
o que o sistema é, como é construído e por que decisões foram tomadas.

## Arquitetura atual resumida

- Monólito modular Django.
- PostgreSQL como banco de dados.
- Multi-tenancy por schema, um schema PostgreSQL por escritório, via
  django-tenants.
- Módulos internos separados por apps Django (`accounts`, `clientes`,
  `processos`, etc.).
- Não há, na arquitetura atual, microserviços independentes.

## Organização documental

- `governance/` — políticas sobre como a documentação é organizada,
  mantida e nomeada, e o índice de decisões do projeto.
- `product/` — visão, escopo, glossário e especificações canônicas do
  produto.
- `architecture/` — decisões e especificações canônicas de arquitetura
  técnica.
- `security/` — regras, políticas e decisões de segurança do sistema.
- `delivery/` — estado atual, roadmap, tarefas ativas e relatórios de
  implementação.
- `development/` — procedimentos operacionais de desenvolvimento, testes,
  migrations e uso de agentes de IA.
- `history/` — material documental preservado para rastreabilidade, sem
  autoridade sobre o estado atual do sistema.

Algumas dessas áreas ainda não existem no repositório e serão criadas em
lotes futuros da reorganização documental.

## Hierarquia das fontes de verdade

Em ordem decrescente de autoridade:

1. PDR ou ADR aceito e vigente.
2. Especificação canônica do produto.
3. Arquitetura e segurança canônicas.
4. Tarefa ativa aprovada.
5. Código e testes como evidência do comportamento implementado.
6. Current-state verificado em um commit.
7. Roadmap.
8. Material histórico, apenas como contexto.

O código demonstra o que existe. A especificação demonstra o que
deveria existir. Quando os dois divergem, a divergência não pode ser
resolvida silenciosamente por uma IA — ela deve ser registrada e
levada a uma decisão humana, conforme a [Regra de conflito](#regra-de-conflito).

## Ordem de leitura por tarefa

### Para entender o produto

- `docs/product/vision.md`
- `docs/product/scope.md`
- `docs/product/glossary.md`
- Documento do módulo relacionado

### Para planejar uma implementação

- Documentação do produto
- PDRs relacionados
- Arquitetura
- Segurança
- Current-state
- Tarefa ativa

### Para revisar uma implementação

- Tarefa ativa
- Plano aprovado
- Diff
- Testes
- Arquitetura
- Segurança

### Para consultar histórico

- `docs/history/`

## Regra de conflito

Diante de uma divergência relevante entre documentação e código, ou entre
documentos canônicos, o agente deve:

1. Interromper a decisão afetada.
2. Registrar a divergência encontrada.
3. Apontar os documentos e o código envolvidos.
4. Solicitar decisão humana.
5. Atualizar a fonte canônica antes de implementar.

## Estado da reorganização

A estrutura documental está sendo implantada gradualmente na branch
`docs/reorganizacao-harness`, em lotes sucessivos. Documentos referenciados
neste índice que ainda não existem no repositório fazem parte de lotes
futuros e não devem ser tratados como concluídos até que sejam
efetivamente criados.
