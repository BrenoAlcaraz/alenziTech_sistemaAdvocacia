---
id: PDR-0033
title: Delegação por convite em Tarefas e Agenda
status: accepted
owner: product-and-engineering
decision_date: 2026-09-22
last_reviewed: 2026-09-22
supersedes: []
partially_supersedes:
  - PDR-0002
complements: []
source_files: []
---

# PDR-0033 — Delegação por convite em Tarefas e Agenda

## Contexto

[PDR-0002](PDR-0002-delegacao-direta-de-tarefas.md) decidiu que delegar
uma Tarefa é sempre direto, sem fluxo de aceite. Essa regra não
distinguia quem delega: um usuário comum delegando para um colega
qualquer tinha o mesmo efeito imediato que um gerente delegando para o
próprio subordinado. Passou a existir demanda de produto para que
delegação entre pessoas sem relação hierárquica clara passe por
convite (aceitar/recusar), preservando a delegação direta só onde a
autoridade sobre o destinatário já é inequívoca — Administrador e
gerente de Equipe sobre subordinado direto.

Agenda tinha o mesmo problema para o responsável de um Compromisso
delegado (`criado_por != responsavel`), sem decisão própria — este PDR
resolve os dois módulos com a mesma regra conceitual, reaproveitando o
mecanismo compartilhado descrito abaixo.

## Decisão

Delegar Tarefa (atribuir) ou Compromisso (definir responsável por
outra pessoa) gera um **convite** — pendente até o destinatário aceitar
ou recusar — em todos os casos, exceto dois, que permanecem diretos
(sem convite), herdando o comportamento já decidido em PDR-0002:

- **Administrador do escritório** delegando para qualquer usuário;
- **gerente de Equipe** (`MembroEquipe.eh_gerente=True`) delegando para
  um **subordinado da própria Equipe** — membro ativo dessa mesma
  Equipe que não é, ele próprio, gerente dela. Entre dois gerentes da
  mesma Equipe, o convite continua obrigatório.

Delegar continua exigindo a habilitação já existente de atribuir a
terceiros (`tarefas_atribuir_outros`/`agenda_criar_para_outros`) — ser
gerente de Equipe não substitui essa habilitação; sem ela, gerente não
delega a ninguém, nem no caso direto.

Auto-atribuição (delegar para si mesmo) nunca passa por convite.

### Fluxo do convite

- Nasce **pendente**; só o próprio destinatário aceita ou recusa,
  sem checagem de habilitação adicional (mesmo princípio da
  confirmação de presença de participante da Agenda, PDR-0020).
- **Aceitar**: a Tarefa/Compromisso passa a existir normalmente para o
  destinatário, no mesmo estado que uma delegação direta teria.
- **Recusar**: aceita justificativa em texto livre, **opcional**.
  Enquanto pendente ou recusada, a Tarefa/Compromisso não aparece como
  atribuição ativa do destinatário (fora das listas/quadro/agenda
  operacionais dele).
- Quem delegou continua vendo o que delegou, com o estado
  correspondente (pendente/aceito ou direto/recusado com justificativa),
  nas sub-abas já existentes "Delegadas por mim"/"Delegados por mim".

### Mecanismo compartilhado

`ConviteDelegacao` (`apps.accounts.models`) e a função de decisão
`delegacao_exige_convite` (`apps.accounts.delegacao`) são compartilhados
entre os dois módulos — vínculo genérico (`content_type`/`object_id`)
com a Tarefa ou o Compromisso delegado, para não criar dependência de
`apps.accounts` sobre `apps.tarefas`/`apps.agenda`.

## Regras obrigatórias

- Convite guarda: delegante, destinatário, status
  (pendente/aceito/recusado), justificativa de recusa (opcional),
  item delegado, data de criação e de resposta.
- Recusar não impede visibilidade da tentativa por quem delegou — o
  item e o convite continuam existindo, só não entram como atribuição
  ativa do destinatário.
- Decisão direto-vs-convite é sempre calculada no backend, nunca só na
  interface.

## Consequências

- `Tarefa`/`Compromisso` ganham FK opcional (`convite_delegacao`) —
  presente e não-aceita enquanto a atribuição não é ativa para o
  responsável.
- Querysets de leitura "ativa" de cada módulo (quadro/lista/agenda,
  sub-abas "Recentes"/"Atribuídas por terceiros"/"Novos na
  agenda"/"Adicionado por terceiro", e a queryset de mutação) passam a
  excluir item com convite pendente/recusado para quem não é
  Administrador.
- Nova sub-aba "Convites recebidos" em Tarefas e em Agenda, com ação de
  aceitar/recusar.

## Alternativas ou regras substituídas

PDR-0002 permanece integralmente válido para os dois casos que
continuam diretos (Administrador e gerente→subordinado da própria
Equipe): comportamento "aparece imediatamente, sem aceite", registro
separado de criador/atribuidor/responsável, e histórico de
reatribuição. A parte substituída é só a generalização "delegação de
tarefa é sempre direta" — agora depende de quem delega e para quem.

## Fora do escopo desta decisão

- Notificação (push/e-mail/in-app) de convite recebido, aceito ou
  recusado.
- Expiração automática, lembrete ou cancelamento/retirada de convite
  pendente por quem delegou.
- Reatribuição de Tarefa/Compromisso **já existente** para outro
  responsável — decisão confirmada nesta rodada: continua livre, sem
  convite e sem exigir habilitação, exatamente como o comportamento
  vigente de PDR-0002 para Tarefas. Este PDR cobre só a delegação que
  **cria** a atribuição inicial.
- Múltiplas Equipes por usuário, hierarquia/aninhamento entre Equipes,
  herança de permissão entre Equipes — continuam em aberto (ver
  glossário de Equipe em [PRODUCT.md](../PRODUCT.md)); este PDR só usa
  a relação direta gerente↔membro dentro de uma mesma Equipe.
- Qualquer alteração à confirmação de presença de participante da
  Agenda (PDR-0020) — conceito distinto, que decide presença, não quem
  é o responsável.

## Critérios de aceite funcionais

- Usuário comum com habilitação de atribuir a terceiros delega
  Tarefa/Compromisso para outro usuário → nasce convite pendente; item
  não aparece como atribuição ativa do destinatário até aceite.
- Destinatário aceita → item passa a existir normalmente para ele.
- Destinatário recusa, com ou sem justificativa → item não é ativo
  para ele; convite fica "recusado" (com a justificativa, quando
  houver).
- Gerente ativo de uma Equipe delega para membro ativo não-gerente
  dessa mesma Equipe → direto, sem convite.
- Gerente delega para outro gerente da mesma Equipe, ou para usuário
  fora de qualquer Equipe que gerencia → exige convite.
- Administrador do escritório delega para qualquer usuário → direto,
  sem convite, mesmo sem a habilitação de atribuir a terceiros.
- Quem delegou vê, em "Delegadas/Delegados por mim", o estado atual de
  cada delegação.
- Reatribuir uma Tarefa/Compromisso já existente continua funcionando
  exatamente como hoje (livre, sem convite).
- Confirmação de presença de participante da Agenda (PDR-0020) não
  muda em nada.
