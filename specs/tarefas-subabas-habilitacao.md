# Spec — Tarefas: sub-abas condicionadas por habilitação

## Objetivo

Replicar o padrão visual e de interação do protótipo
(`docs/prototipos/tarefas-prototipo.html`), incluindo a faixa de
sub-abas abaixo da lista principal, condicionadas por habilitação.

## Comportamento esperado

- Abaixo da lista principal de tarefas, faixa de sub-abas (mesmo padrão
  usado em Agenda, ver `agenda-calendario-lista-unificados.md`):
  - **"Recentes (últimas 24h)"** — sempre visível; tarefas que entraram
    na lista do usuário nas últimas 24h, de qualquer origem.
  - **"Atribuídas a mim por terceiros"** — sempre visível; só tarefas
    que outra pessoa atribuiu ao usuário.
  - **"Delegadas por mim"** — só para quem tem a habilitação de atribuir
    tarefa a terceiros; todas as tarefas que o próprio usuário atribuiu
    a outra pessoa, com status de cada uma.
  - **"Ver tarefas de outra pessoa"** — só para quem tem a mesma
    habilitação; seletor de colega, mostra a lista de tarefas dele, com
    botão para criar uma tarefa nova direto para essa pessoa (campo
    "Atribuir a" pré-preenchido e travado).
- Demais telas do módulo (quadro, formulário) revisadas visualmente
  contra o protótipo.

## Regras de negócio relevantes

- As sub-abas usam a habilitação de atribuir tarefa a terceiros já
  existente — nenhuma habilitação nova.
- Nenhuma mudança na regra de delegação direta sem aceite (PDR-0002) nem
  na notificação de conclusão (PDR-0016).

## Fora de escopo

- Qualquer alteração de status além dos já existentes (pendente/em
  andamento/concluída/cancelada).

## Critérios de aceite

- As quatro sub-abas aparecem com a mesma condição de habilitação
  descrita acima.
- "Ver tarefas de outra pessoa" permite criar tarefa nova já atribuída à
  pessoa selecionada.
