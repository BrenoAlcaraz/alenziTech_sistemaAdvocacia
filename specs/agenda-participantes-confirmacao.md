# Spec — Participantes e confirmação de presença na Agenda

## Objetivo

Dar uso real ao campo `participantes` do `Compromisso` (já existe no
model, sem formulário nem efeito): compromisso passa a ter, além do
responsável obrigatório, participantes que confirmam ou recusam
presença, com visibilidade e lembrete próprios. Fecha o gap de escopo
de dados do módulo Agenda registrado em
[STATUS.md](../docs/STATUS.md#módulos) e a Rodada 2.4 da sequência de
[PDR-0009](../docs/decisions/PDR-0009-sequencia-fase-2.md).

## Comportamento esperado

### Visibilidade

- Escopo de leitura `somente_seus` (Agenda) passa a incluir compromisso
  onde o usuário é participante (qualquer status), além de onde é
  responsável. Escopo `todos` não muda.
- Participante nunca é responsável: não assume a obrigação do
  compromisso, só é convidado a ele.

### Convite e confirmação de presença

- Quem tem autorização de edição do compromisso (regra de módulo já
  existente — sem habilitação nova) adiciona/remove participantes.
- Cada participante tem status individual: pendente, confirmado ou
  recusado. O responsável não passa por esse fluxo — está
  implicitamente "confirmado" no próprio compromisso.
- Confirmar ou recusar presença é ação exclusiva do próprio participante
  sobre si mesmo.
- Ao ser adicionado, o participante recebe notificação (mesma
  infraestrutura de `apps/notificacoes` já usada em Tarefas/Financeiro)
  pedindo para confirmar presença.
- Recusar presença não remove o compromisso da agenda pessoal do
  participante — continua visível, marcado como recusado.

### Reagendamento

- Alterar `data_hora_inicio` do compromisso reseta para pendente a
  confirmação de todo participante que já tinha confirmado.
- Participante afetado recebe notificação avisando do reagendamento e
  da necessidade de reconfirmar.

### Lembrete automático (PDR-0016)

- Lembrete 15 minutos antes chega para o responsável (como já é hoje) e
  para participantes com status confirmado.
- Participante pendente ou recusado não recebe lembrete.

### Cancelamento

- Cancelar um compromisso (`status=cancelado`, já existente no model)
  dispara notificação distinta da de convite/lembrete, para responsável
  e todos os participantes.
- Compromisso cancelado sai da lista operacional padrão da Agenda
  (grade normal) para todos os envolvidos.
- Fica disponível numa seção separada, só de consulta ("Cancelados"),
  acessada por um botão no topo da Agenda — sem opção de reativar.
  Lista nome, data, participantes e responsável do compromisso.
- A seção "Cancelados" respeita o mesmo escopo de leitura do módulo
  (`somente_seus`/`todos`).
- Compromisso cancelado é excluído automaticamente 7 dias após a data
  do **cancelamento** (não a data original do compromisso), via job
  periódico no mesmo padrão do job de lembrete já existente
  (`enviar_lembretes_agenda`).
- A seção "Cancelados" exibe aviso em texto informando essa exclusão
  automática após 7 dias.

### Dashboard

- Passa a existir dois blocos pessoais (sempre sobre o próprio usuário,
  independente do nível `somente_seus`/`todos` do módulo Agenda):
  1. Próximos compromissos confirmados nos próximos 7 dias (onde o
     usuário é responsável ou participante confirmado).
  2. Contador de compromissos com confirmação pendente, com opção de
     expandir para confirmar/recusar presença diretamente do painel.

### Permissões

- Sem habilitação granular nova. Gerenciar participantes reaproveita a
  autorização de edição do compromisso já existente no módulo Agenda.
  Confirmar/recusar presença não passa por checagem de habilitação —
  é ação do usuário sobre o próprio registro de participação.
- Não conflita com `agenda_criar_para_outros` (essa habilitação rege só
  quem pode atribuir *responsável* a outra pessoa; participante nunca é
  responsável).

## Regras de negócio relevantes

- Um compromisso pode ter N participantes além do responsável
  obrigatório.
- Participante só pode ser usuário interno do escritório (mesmo
  universo hoje usado para `responsavel`) — não inclui cliente externo.
- Status de confirmação é individual por participante, não do
  compromisso como um todo.

## Fora do escopo

- Habilitação granular nova para gerenciar participantes ou confirmar
  presença.
- Convite para pessoas fora do escritório (clientes, terceiros).
- Botão de reativar compromisso cancelado.
- Janela de retenção configurável — fixa em 7 dias nesta versão.
- Qualquer alteração em Processos, Tarefas ou nos conceitos de
  responsável/integrante desses módulos.
- Notificação em tempo real fora da infraestrutura já existente de
  `apps/notificacoes`.

## Critérios de aceite

- Usuário marcado como participante de um compromisso o vê no escopo
  `somente_seus`, mesmo sem ser o responsável.
- Participante consegue confirmar ou recusar presença; recusar não o
  remove da própria agenda.
- Alterar a data/hora de um compromisso volta a confirmação de
  participantes já confirmados para pendente e notifica cada um deles.
- Lembrete de 15 minutos antes chega só para responsável e participantes
  confirmados.
- Cancelar um compromisso notifica responsável e participantes, some da
  grade operacional da Agenda para todos, e passa a aparecer na seção
  "Cancelados" (só consulta, sem reativar).
- Compromisso cancelado deixa de existir 7 dias após a data do
  cancelamento.
- Dashboard mostra corretamente os dois blocos pessoais descritos
  (confirmados dos próximos 7 dias; contador de pendentes com
  expansão).
- Adicionar/remover participante exige a mesma autorização de edição do
  compromisso já existente hoje — nenhuma habilitação nova aparece no
  painel de permissões.
