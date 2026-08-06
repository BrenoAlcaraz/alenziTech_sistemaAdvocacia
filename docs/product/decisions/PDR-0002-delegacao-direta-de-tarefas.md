---
id: PDR-0002
title: Delegação direta de tarefas
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-06
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/product-vision-original.docx
---

# PDR-0002 — Delegação direta de tarefas

## Contexto

O produto precisa de um mecanismo para que uma pessoa atribua trabalho a
outra dentro do escritório. Era necessário decidir se essa atribuição
dependeria de um fluxo de aceite pelo destinatário ou se funcionaria
como uma ordem direta de trabalho.

## Problema

Um fluxo de aceite ou recusa adiciona um estado intermediário à
atribuição de tarefas e cria ambiguidade sobre quando uma tarefa
efetivamente existe para o destinatário. Isso não corresponde ao
funcionamento esperado de uma atribuição interna de trabalho dentro de
um escritório, na qual a tarefa deve valer a partir do momento em que é
criada.

## Decisão

A delegação de tarefas é direta. Não há fluxo de:

delegar → aguardar aceite → aceitar ou recusar

O comportamento é:

criar/delegar → a tarefa aparece imediatamente para o destinatário

A tarefa funciona como uma ordem ou atribuição interna de trabalho. O
destinatário não precisa aceitar para que a atribuição exista. Não
haverá status "recusada" nesta versão, por ser incompatível com a lógica
de delegação direta.

## Regras obrigatórias

A tarefa deve guardar, de forma separada:

- quem criou;
- quem atribuiu;
- destinatário da atribuição;
- data da atribuição;
- responsável atual;
- prazo;
- prioridade;
- status;
- data de conclusão;
- cliente relacionado, quando aplicável;
- processo relacionado, quando aplicável.

Mesmo quando quem cria e quem atribui é a mesma pessoa, os dois
conceitos permanecem separados, para permitir automações futuras.

Os status iniciais da tarefa são:

- pendente;
- em andamento;
- concluída;
- cancelada.

Visibilidade funcional das tarefas:

| Usuário | O que pode ver |
| --- | --- |
| Administrador do escritório | Todas as tarefas |
| Usuário com habilitação de gestão | Tarefas da equipe ou escopo autorizado |
| Usuário comum | Tarefas atribuídas a ele e tarefas criadas por ele |

Uma tarefa pode ser reatribuída. A reatribuição deve preservar:

- o responsável anterior;
- o novo responsável;
- o autor da alteração;
- a data da alteração.

A reatribuição não pode sobrescrever silenciosamente esse histórico
mínimo.

Notificações não são pré-requisito da delegação direta e ficam fora
desta entrega.

## Consequências

- O modelo de dados de tarefa precisa separar criador, atribuidor e
  responsável atual como campos distintos, mesmo quando coincidentes.
- A ausência de um estado de aceite simplifica o ciclo de vida da
  tarefa, mas exige que a visibilidade funcional (por perfil) seja a
  principal barreira de controle sobre quem vê o quê.
- A reatribuição exige preservar um histórico mínimo, o que impacta a
  modelagem de dados além de um simples campo de "responsável".
- A aplicação exata do escopo de visibilidade (equipe, escopo
  habilitado) depende do trabalho de permissões previsto para a Rodada
  2.1, e não é resolvida por este PDR.

## Alternativas ou regras substituídas

O material de visão inicial (`product-vision-original.docx`) descrevia
tarefas ("tasks") como listas de afazeres atribuíveis a si mesmo ou a
outro usuário, sem detalhar um fluxo de aceite. A decisão consolidada
posterior não contradiz essa visão inicial, mas formaliza explicitamente
a ausência de aceite/recusa e a lista de dados obrigatórios, o que não
estava definido nas fontes anteriores.

## Fora do escopo desta decisão

- Notificações de atribuição, reatribuição ou prazo de tarefas: fora
  desta entrega, por decisão explícita das fontes.
- Regras detalhadas de escopo de visibilidade por equipe ou habilitação
  específica: dependem do trabalho de permissões da Rodada 2.1.
- Mecanismo técnico de auditoria completa de reatribuições: este PDR
  exige preservar responsável anterior, novo responsável, autor e data
  da alteração, mas não define a estrutura técnica desse histórico.
- Status "recusada" ou qualquer fluxo de aceite: explicitamente
  descartados nesta versão.

## Critérios de aceite funcionais

- Ao criar e atribuir uma tarefa, ela aparece imediatamente para o
  destinatário, sem exigir aceite.
- Não existe, nesta versão, um status de tarefa "recusada".
- A tarefa registra separadamente quem criou, quem atribuiu, o
  destinatário da atribuição, a data da atribuição e o responsável
  atual, mesmo quando esses papéis coincidem na mesma pessoa.
- A tarefa possui prazo, prioridade, status, data de conclusão, e
  vínculo opcional com cliente e processo.
- O status da tarefa está restrito a: pendente, em andamento, concluída
  ou cancelada.
- Um Administrador do escritório vê todas as tarefas; um usuário com
  habilitação de gestão vê as tarefas da equipe ou escopo autorizado; um
  usuário comum vê apenas tarefas atribuídas a ele ou criadas por ele.
- Ao reatribuir uma tarefa, o sistema preserva o responsável anterior, o
  novo responsável, quem fez a alteração e a data da alteração, sem
  sobrescrever essa informação silenciosamente.
- A ausência de notificações não impede o funcionamento da delegação de
  tarefas.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [product-vision-original.docx](../../history/source-material/product-vision-original.docx)
