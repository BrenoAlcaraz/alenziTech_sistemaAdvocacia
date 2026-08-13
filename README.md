# Breno - LawSystem

## Visão geral

Breno - LawSystem é um sistema jurídico SaaS white label, multi-tenant,
para escritórios de advocacia. É construído como um monólito modular
Django, com PostgreSQL como banco de dados e isolamento por schema
PostgreSQL por tenant (schema-per-tenant) via django-tenants — cada
escritório opera como um tenant isolado, e a plataforma SaaS (tenants,
planos, assinaturas) permanece em um schema público compartilhado.

## Documentação canônica

A fonte de verdade deste projeto vive em [`docs/`](docs/README.md).
[docs/README.md](docs/README.md) é o índice oficial: organização
documental, ordem de leitura por tarefa e a hierarquia das fontes de
verdade. Este README não repete esse conteúdo — ele apenas orienta por
onde começar.

## Arquitetura

- [docs/architecture/overview.md](docs/architecture/overview.md)
- [docs/architecture/module-map.md](docs/architecture/module-map.md)
- [docs/architecture/multitenancy.md](docs/architecture/multitenancy.md)

## Estado e planejamento

- [docs/delivery/current-state.md](docs/delivery/current-state.md)
- [docs/delivery/roadmap.md](docs/delivery/roadmap.md)

## Desenvolvimento

Preparação de ambiente, dependências, banco de dados, Tailwind e todos
os comandos disponíveis:

- [docs/development/README.md](docs/development/README.md) — visão
  geral e fluxo mínimo para começar;
- [docs/development/commands.md](docs/development/commands.md) —
  comandos confirmados;
- [docs/development/testing.md](docs/development/testing.md) —
  estratégia e comandos de teste;
- [docs/development/workflow.md](docs/development/workflow.md) —
  ciclo de execução de uma unidade de trabalho;
- [docs/development/quality-gates.md](docs/development/quality-gates.md) —
  critérios de validação;
- [docs/development/git-procedure.md](docs/development/git-procedure.md) —
  procedimento de Git.

## Trabalho em andamento

O trabalho executável é organizado como Work Items em
[docs/delivery/work/](docs/delivery/work/README.md), sob o protocolo
definido em
[docs/delivery/work/README.md](docs/delivery/work/README.md).

## Hierarquia de fontes

Os arquivos de entrada na raiz deste repositório, incluindo este
README, orientam a leitura, mas não substituem, redefinem nem duplicam
produto, arquitetura, segurança, estado atual, roadmap ou Work Items. A
hierarquia oficial das fontes de verdade está em
[docs/README.md#hierarquia-das-fontes-de-verdade](docs/README.md#hierarquia-das-fontes-de-verdade).
