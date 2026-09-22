# Spec — Delegação por convite em Agenda e Tarefas

## Objetivo

Introduzir um fluxo de convite (aceitar/recusar) para delegação de
Tarefa e de Compromisso (Agenda) quando a delegação parte de um
usuário comum ou ocorre entre pessoas sem relação hierárquica direta
de equipe — preservando delegação direta (sem convite) apenas para os
dois casos hierárquicos já claros: Administrador delegando para
qualquer usuário, e gerente delegando para subordinado da própria
Equipe.

Mesma regra conceitual reaproveitada nos dois módulos, respeitando as
diferenças naturais de modelo entre Tarefa e Compromisso.

## Nota sobre decisão anterior (PDR-0002)

[PDR-0002](../docs/decisions/PDR-0002-delegacao-direta-de-tarefas.md)
decidiu que a delegação de Tarefa é sempre direta, sem fluxo de aceite,
e descartou explicitamente status "recusada". Esta spec **altera
parcialmente** essa decisão: passa a existir aceite/recusa condicional
conforme quem delega e para quem. A parte de PDR-0002 que permanece
válida: os dois casos que continuam diretos (agora Admin→qualquer um e
gerente→subordinado da própria equipe) seguem exatamente o
comportamento "aparece imediatamente, sem aceite" já decidido. Ao
promover esta spec, abrir um novo PDR que supersede/complementa
PDR-0002 registrando essa mudança — não editar PDR-0002 retroativamente
(decisão registrada é imutável; PDRs se substituem, não se reescrevem).

## Comportamento esperado

### Quando a delegação exige convite

Delegar Tarefa (atribuir) ou Compromisso (definir responsável por
outra pessoa) gera um **convite** — estado pendente até o destinatário
aceitar ou recusar — em todos os casos, **exceto** os dois listados em
"Quando a delegação é direta" abaixo.

Isso cobre, entre outros: usuário comum delegando para qualquer outro
usuário; gerente delegando para usuário fora da própria Equipe; gerente
delegando para outro gerente da mesma Equipe; gerente delegando para
usuário de Equipe diferente da sua.

Delegar continua exigindo a habilitação já existente de atribuir a
terceiros (`tarefas_atribuir_outros` em Tarefas, `agenda_criar_para_outros`
em Agenda) — nenhuma habilitação nova é criada por esta spec. Ser
gerente de Equipe não substitui essa habilitação nos casos que exigem
convite (gerente sem a habilitação não delega a ninguém, do mesmo jeito
que hoje).

### Quando a delegação é direta (sem convite)

1. **Administrador do escritório** delegando para qualquer usuário do
   tenant — direto, sem convite, sem exigir a habilitação de atribuir a
   terceiros (mesmo bypass que Administrador já tem hoje nos módulos).
2. **Gerente de Equipe** delegando para um **subordinado da própria
   Equipe** — direto, sem convite, desde que o gerente tenha a
   habilitação de atribuir a terceiros. "Subordinado da própria Equipe"
   significa: o destinatário é membro ativo de uma Equipe em que quem
   delega é gerente ativo (`eh_gerente=True`), **e o destinatário não é
   ele próprio gerente dessa mesma Equipe** — entre dois gerentes da
   mesma Equipe, o convite continua obrigatório (regra de negócio
   explícita do pedido original).

Nesses dois casos o item entra imediatamente para o destinatário, no
mesmo estado que a delegação direta já tem hoje (comportamento
inalterado de PDR-0002 para Tarefa; comportamento já existente hoje
para Compromisso).

### Fluxo do convite

- Convite nasce com status **pendente**.
- Só o próprio destinatário aceita ou recusa o próprio convite — ação
  sobre o próprio registro, sem checagem de habilitação adicional
  (mesmo princípio já usado na confirmação de presença de participante
  da Agenda, PDR-0020).
- **Aceitar**: o item (Tarefa/Compromisso) passa a existir normalmente
  para o destinatário, no mesmo estado inicial que uma delegação direta
  teria (ex.: Tarefa nasce "a fazer"; Compromisso nasce "agendado").
- **Recusar**: o item não passa a existir como ativo para o
  destinatário. Recusa aceita uma justificativa em texto livre,
  **opcional** — sem justificativa é uma recusa válida.
- Enquanto pendente, o item não aparece como atribuição ativa do
  destinatário (não entra no quadro de tarefas nem na agenda dele como
  compromisso confirmado) — só existe como convite aguardando resposta.

### Visibilidade para quem delegou

Quem delega continua vendo o que delegou, com o estado correspondente
(pendente / aceito / recusado, com a justificativa quando houver) — nas
sub-abas já existentes "Delegadas por mim" (Tarefas) e "Delegados por
mim" (Agenda), sem criar nova aba. Delegação direta (Admin/gerente→
subordinado) aparece nessa mesma visão já no estado equivalente a
aceito, coerente com "sem convite".

### Não confundir com RSVP de participante da Agenda

O convite de delegação decide **quem é o responsável** pela Tarefa/
Compromisso. É distinto da confirmação de presença de **participante**
de Compromisso (PDR-0020, `pendente`/`confirmado`/`recusado` por
participante) — fluxo já existente, que não muda por esta spec e
continua não passando pelo responsável.

## Regras de negócio relevantes

- Mesmo conceito de convite reaproveitado entre Tarefas e Compromisso;
  diferenças de modelo entre os dois módulos (ex.: Tarefa já separa
  criador/atribuidor por PDR-0002; Compromisso hoje só tem
  `criado_por`) são absorvidas na implementação de cada módulo, sem
  mudar a regra de produto.
- "Própria Equipe" para fins de bypass de gerente usa a relação já
  existente `MembroEquipe.eh_gerente` (ver `apps/accounts/escopo.py`,
  já usada para escopo — reaproveitar, não recriar). Usuário pode ter
  múltiplas Equipes; basta existir **uma** Equipe ativa em comum onde
  quem delega é gerente ativo e o destinatário é membro ativo não-
  gerente para o caminho direto se aplicar.
- Autorização e a decisão convite-vs-direto são sempre calculadas no
  backend, nunca só na interface.
- Convite, aceite e recusa não usam nem alteram o fluxo de participantes/
  confirmação de presença da Agenda.

## Fora do escopo

- Notificação (push/e-mail/in-app) de convite recebido, aceito ou
  recusado — mecanismo de notificação específico não é decidido por
  esta spec.
- Expiração automática de convite pendente, lembrete de convite
  parado, ou cancelamento/retirada do convite por quem delegou antes da
  resposta — não solicitado, não decidir agora.
- Reatribuição de Tarefa/Compromisso **já existente** para outro
  responsável — decisão confirmada: continua livre, exatamente como
  hoje (qualquer usuário ativo reatribui, sem convite, sem exigir a
  habilitação de atribuir a terceiros — regra vigente de Tarefas,
  PDR-0002). Esta spec cobre só a delegação que **cria** a atribuição
  inicial; reatribuição de item já existente não muda.
- Múltiplas Equipes por usuário como regra geral, hierarquia/aninhamento
  entre Equipes, herança de permissão entre Equipes — continuam em
  aberto conforme já registrado em PRODUCT.md; esta spec só usa a
  relação direta gerente↔membro dentro de uma mesma Equipe, sem
  resolver esses gaps maiores.
- Qualquer habilitação nova de autorização — reaproveita
  `tarefas_atribuir_outros` e `agenda_criar_para_outros` já existentes.

## Critérios de aceite

- Usuário comum com a habilitação de atribuir a terceiros delega
  Tarefa/Compromisso para outro usuário → nasce convite pendente; item
  não aparece como atribuição ativa do destinatário até aceite.
- Destinatário aceita → item passa a existir normalmente para ele,
  responsável = destinatário, mesmo estado inicial de uma delegação
  direta.
- Destinatário recusa, com ou sem justificativa → item não é criado
  como ativo para ele; convite fica "recusado" (com a justificativa,
  quando informada).
- Gerente ativo de uma Equipe delega para membro ativo não-gerente
  dessa mesma Equipe → direto, sem convite, item aparece imediatamente
  para o destinatário.
- Gerente delega para outro gerente da mesma Equipe → exige convite.
- Gerente delega para usuário fora de qualquer Equipe em que é gerente
  → exige convite.
- Administrador do escritório delega para qualquer usuário → direto,
  sem convite, mesmo sem a habilitação de atribuir a terceiros.
- Quem delegou vê, em "Delegadas/Delegados por mim", o estado atual de
  cada delegação (pendente, aceito/direto, ou recusado com
  justificativa quando houver).
- Reatribuir uma Tarefa/Compromisso já existente para outro usuário
  continua funcionando exatamente como hoje (livre, sem convite, sem
  exigir habilitação) — comportamento inalterado por esta spec.
- Nenhuma mudança de comportamento na confirmação de presença de
  participante de Compromisso (PDR-0020) nem nas habilitações já
  existentes de Tarefas/Agenda.
- Autorização (quem pode delegar, e se a delegação exige convite ou é
  direta) é aplicada no backend independente do que a interface
  mostra.
