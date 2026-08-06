---
title: Tarefas
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
related_pdrs:
  - PDR-0002
  - PDR-0009
---

# Tarefas

## Objetivo

Permitir que usuários do escritório criem, atribuam e acompanhem
tarefas operacionais, funcionando como uma ordem ou atribuição interna
de trabalho, sem depender de um fluxo de aceite pelo destinatário.

## Escopo funcional

- criação de tarefas para si mesmo ou para outro usuário do
  escritório;
- delegação direta;
- acompanhamento de status;
- reatribuição com histórico mínimo;
- vínculo opcional com cliente e processo;
- visibilidade de tarefas conforme papel de acesso e escopo
  autorizado.

## Atores e expectativas de acesso

[PDR-0002](../decisions/PDR-0002-delegacao-direta-de-tarefas.md) é a
principal fonte deste módulo e define a visibilidade funcional das
tarefas:

| Usuário | O que pode ver |
| --- | --- |
| Administrador do escritório | Todas as tarefas do tenant |
| Usuário com habilitação de gestão | Tarefas da equipe ou escopo autorizado |
| Usuário comum | Tarefas atribuídas a ele e tarefas criadas por ele |

Esta tabela descreve necessidade funcional, não uma matriz técnica
definitiva de permissões; essa matriz pertence a `docs/security/`,
ainda não criado. Autorização e escopo de dados devem ser aplicados no
backend, não apenas ocultando elementos de interface.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Tarefas e agenda":
tarefa, criador, atribuidor, destinatário da atribuição, responsável
atual, delegação direta, reatribuição e prazo da tarefa. Este
documento não redefine esses termos.

## Regras funcionais

- A delegação de tarefas é direta: a tarefa aparece imediatamente para
  o destinatário assim que criada ou delegada, sem fluxo de aceite.
- Não existe, nesta versão, status de tarefa "recusada".
- A tarefa registra separadamente: criador, atribuidor, destinatário
  da atribuição, data da atribuição e responsável atual — mesmo quando
  esses papéis coincidem na mesma pessoa.
- A tarefa possui prazo, prioridade, status e data de conclusão.
- O vínculo com cliente e com processo é opcional.
- O status da tarefa está restrito a: pendente, em andamento,
  concluída ou cancelada.
- Uma tarefa pode ser reatribuída. A reatribuição preserva o
  responsável anterior, o novo responsável, o autor da alteração e a
  data da alteração, sem sobrescrever essa informação silenciosamente.
- A visibilidade de tarefas segue a tabela de atores descrita acima.
- Notificações relacionadas a tarefas são adiadas; a ausência de
  notificações não impede o funcionamento da delegação direta.
- Autorização e escopo de dados devem ser aplicados no backend.

## Fluxos principais

1. Criar tarefa para si mesmo.
2. Delegar tarefa diretamente para outro usuário.
3. Iniciar uma tarefa.
4. Concluir uma tarefa.
5. Cancelar uma tarefa.
6. Reatribuir uma tarefa.
7. Consultar tarefas dentro do escopo autorizado ao usuário.

Não fazem parte deste módulo:

- fluxo de aceite;
- fluxo de recusa;
- gamificação;
- avaliação de desempenho;
- notificação como pré-requisito para a delegação funcionar.

## Integrações e dependências

- Vínculo opcional com o módulo Clientes.
- Vínculo opcional com o módulo Processos.
- O escopo de visibilidade por "habilitação de gestão" pode depender
  de Equipes como referência organizacional, conforme
  [equipes.md](equipes.md); a aplicação exata desse escopo depende do
  trabalho de permissões ainda não formalizado neste lote.

## Fora do escopo imediato

- Aceite ou recusa de tarefas.
- Gamificação.
- Avaliação de desempenho a partir de tarefas.
- Notificações de atribuição, reatribuição ou prazo.

## Pontos em aberto

- A aplicação exata do escopo de visibilidade (equipe, escopo
  habilitado) depende do trabalho de permissões ainda não
  formalizado; PDR-0002 não resolve esse detalhamento.
- Se e como o campo equipe deve existir na tarefa para sustentar o
  escopo por "habilitação de gestão" não é decidido por esta
  especificação.

## Critérios de aceite funcionais

- Ao criar e atribuir uma tarefa, ela aparece imediatamente para o
  destinatário, sem exigir aceite.
- Não existe status de tarefa "recusada".
- A tarefa registra separadamente quem criou, quem atribuiu, o
  destinatário da atribuição, a data da atribuição e o responsável
  atual, mesmo quando esses papéis coincidem na mesma pessoa.
- O status da tarefa está restrito a pendente, em andamento, concluída
  ou cancelada.
- Um Administrador do escritório vê todas as tarefas; um usuário com
  habilitação de gestão vê as tarefas da equipe ou escopo autorizado;
  um usuário comum vê apenas tarefas atribuídas a ele ou criadas por
  ele.
- Ao reatribuir uma tarefa, o sistema preserva responsável anterior,
  novo responsável, autor e data da alteração, sem sobrescrita
  silenciosa.
- A ausência de notificações não impede o funcionamento da delegação
  direta.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0002 — Delegação direta de tarefas](../decisions/PDR-0002-delegacao-direta-de-tarefas.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)
