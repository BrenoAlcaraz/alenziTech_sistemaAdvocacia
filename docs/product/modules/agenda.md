---
title: Agenda
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
related_pdrs:
  - PDR-0009
---

# Agenda

## Objetivo

Permitir que usuários do escritório registrem, visualizem e gerenciem
compromissos — incluindo prazos processuais relevantes — em lista e em
calendário mensal, com integração funcional aos prazos originados de
processos.

## Escopo funcional

- visualização em lista;
- calendário mensal;
- compromissos, prazos, audiências, perícias, reuniões e outros tipos,
  quando aplicável;
- criação manual de compromisso;
- edição de compromisso;
- eventos originados de processos;
- integração com prazos processuais.

## Atores e expectativas de acesso

- Usuários acessam compromissos conforme papel de acesso, habilitação,
  vínculo com o registro e escopo de dados aplicados.
- O Administrador do escritório possui expectativa de supervisão
  administrativa dentro do tenant.
- O alcance exato do Administrador do escritório e de outros papéis
  sobre agendas individuais de outros usuários será definido em
  docs/security/authorization-matrix.md, documento ainda não criado.
- Nenhuma interface deve conceder acesso sem verificação equivalente no
  backend.
- Ocultar ou exibir elementos de interface não substitui autorização.

Esta seção descreve necessidade funcional, não uma matriz técnica
definitiva de permissões.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Tarefas e agenda":
compromisso, prazo de agenda, evento originado de processo e evento
manual. Este documento não redefine esses termos.

## Regras funcionais

- Um compromisso pode ser manual ou originado de processo.
- Um prazo processual relevante deve poder aparecer na agenda.
- O vínculo entre um prazo processual e o evento correspondente na
  agenda deve preservar a referência à sua origem.
- A alteração de um evento não pode romper silenciosamente a relação
  com o processo de origem.
- Autorização e escopo de dados devem ser aplicados no backend.
- O calendário mensal e a visualização em lista representam os mesmos
  dados; não são bases de dados distintas.
- Cores são um recurso de apresentação visual, não a identidade do
  tipo de compromisso.
- Notificações e lembretes ficam fora deste lote funcional, por não
  estarem formalmente aprovados em nenhum PDR aceito.

A sincronização automática e bidirecional entre prazo processual e
evento de agenda — de modo que uma alteração em um lado atualize o
outro automaticamente — é mencionada como recomendação técnica nas
fontes históricas, mas não está claramente aprovada em nenhum PDR
aceito. Esta especificação não impõe esse comportamento; ver "Pontos
em aberto".

## Fluxos principais

1. Criar evento manual.
2. Editar evento.
3. Visualizar compromissos em lista.
4. Visualizar compromissos em calendário.
5. Consultar eventos vinculados a um processo.
6. Registrar ou refletir um prazo processual na agenda, conforme a
   regra aprovada de integração descrita acima.

## Integrações e dependências

- Depende do módulo Processos para prazos processuais relevantes e
  para eventos originados de processo.
- Vínculo opcional com o módulo Clientes.
- Escopo de dados pode depender de Equipes como referência
  organizacional, conforme [equipes.md](equipes.md).

## Fora do escopo imediato

- Integração com Google Calendar.
- Suporte a múltiplos fusos horários.
- Recorrência de eventos.
- Lembretes automáticos.
- Notificações push.

## Pontos em aberto

- Sincronização automática e bidirecional entre prazo processual e
  evento de agenda — não claramente aprovada em nenhum PDR aceito.
- Conjunto completo de tipos de compromisso além de audiência, prazo,
  reunião e perícia ("outros tipos, quando aplicável") não está
  totalmente enumerado nas fontes canônicas.
- Alcance exato do Administrador do escritório e dos gerentes sobre
  compromissos pertencentes a outros usuários.

## Critérios de aceite funcionais

- A visualização em lista e o calendário mensal exibem os mesmos
  compromissos, sem divergência de dados entre as duas visões.
- Um compromisso criado manualmente não possui vínculo de origem
  processual.
- Um compromisso originado de processo preserva a referência à sua
  origem, mesmo após edição do evento.
- Um prazo processual relevante pode aparecer na agenda.
- Autorização e escopo de dados são aplicados no backend, não apenas
  na interface.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)

Detalhes adicionais de apresentação (por exemplo, ordem de filtros ou
paleta de cores por tipo de compromisso) aparecem apenas em fontes
históricas não canônicas e não são tratados como obrigação funcional
por esta especificação.
