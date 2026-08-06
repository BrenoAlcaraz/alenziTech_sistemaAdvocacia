---
title: Especificações funcionais dos módulos
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Especificações funcionais dos módulos

## Objetivo

Este diretório reúne as especificações funcionais canônicas dos
módulos do Breno - LawSystem. Cada arquivo descreve o comportamento
pretendido de um módulo — o que o produto deve fazer — e não descreve
automaticamente o estado implementado no código. Um documento futuro de
current-state informará o que efetivamente existe implementado em cada
módulo, conforme a hierarquia de fontes descrita em
[../../README.md](../../README.md).

Regras de leitura destas especificações:

- Em caso de conflito, um PDR aceito prevalece sobre uma especificação
  de módulo.
- Regras compartilhadas entre módulos devem ser referenciadas a partir
  do PDR ou do [glossário funcional](../glossary.md) correspondente,
  não duplicadas integralmente em cada documento de módulo.
- Segurança e autorização final — a matriz técnica definitiva de
  papéis, habilitações e permissões — serão documentadas em
  `docs/security/`, ainda não criado. As especificações de módulo
  descrevem apenas a necessidade funcional de acesso.

## Módulos especificados

| Módulo | Documento | Estado da especificação |
| --- | --- | --- |
| Clientes | [clientes.md](clientes.md) | canonical |
| Processos | [processos.md](processos.md) | canonical |
| Tarefas | [tarefas.md](tarefas.md) | canonical |
| Agenda | [agenda.md](agenda.md) | canonical |
| Equipes | [equipes.md](equipes.md) | canonical |

## Módulos ainda não especificados

Os módulos abaixo pertencem ao escopo do produto (ver
[../scope.md](../scope.md)), mas suas especificações funcionais não
foram criadas neste lote de reorganização documental.

| Módulo | Documento | Estado da especificação |
| --- | --- | --- |
| Financeiro | — | pendente neste lote |
| Dashboard | — | pendente neste lote |
| Configurações | — | pendente neste lote |
| Chat | — | pendente neste lote |
| Modelos | — | pendente neste lote |
| Inteligência Artificial | — | pendente neste lote |
