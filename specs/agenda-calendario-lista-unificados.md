# Spec — Agenda: calendário/lista únicos, sub-abas e disponibilidade

## Objetivo

Unificar as visões de lista e calendário numa só página com alternância
dinâmica, replicar a faixa de sub-abas do protótipo (condicionadas por
habilitação) e permitir checar a disponibilidade de um convidado antes de
marcar um compromisso.

## Comportamento esperado

- Calendário e lista convivem na mesma página, com alternância dinâmica
  entre dia/semana/mês/etc. — sem recarregar a página (hoje são duas
  visões acessadas por `?visao=lista|calendario`, em telas separadas).
- Abaixo da lista/calendário, uma faixa de sub-abas, mesma estrutura do
  protótipo (`docs/prototipos/agenda-prototipo.html`):
  - **"Novos na sua agenda (últimas 24h)"** — sempre visível; qualquer
    compromisso que entrou na agenda do usuário nas últimas 24h, de
    qualquer origem (ele mesmo, colega, ou automático).
  - **"Adicionado por terceiro"** — sempre visível; só compromissos que
    outra pessoa colocou na sua agenda.
  - **"Delegados por mim"** — só para quem tem a habilitação de marcar
    compromisso para outros; compromissos que o próprio usuário colocou
    na agenda de outra pessoa, com status de cada um (agendado/
    concluído/cancelado).
  - **"Agenda de outros usuários"** — só para quem tem a Permissão de
    Agenda em "Todos" + habilitação de Gerir; seletor de colega, mostra
    a agenda dele, permite criar compromisso direto nela (campo "Agenda
    de" pré-preenchido e travado no colega selecionado).
- Verificar disponibilidade de convidado: ao adicionar um participante a
  um compromisso, exibir os compromissos que essa pessoa já tem no mesmo
  horário — condicionado à mesma permissão da sub-aba "Agenda de outros
  usuários".

## Regras de negócio relevantes

- Lista e calendário continuam sendo duas visões dos mesmos dados (mesmo
  escopo, mesma exclusão de compromisso cancelado da grade operacional) —
  a mudança é só as duas ficarem na mesma página.
- As quatro sub-abas usam exatamente as condições de habilitação já
  aprovadas hoje (PDR-0020, Permissão "Agenda"/"Todos" + Gerir) — nenhuma
  habilitação nova é criada.

## Fora de escopo

- Sincronização com Google Calendar ou calendários externos.
- Notificação por canal externo (e-mail/push/SMS) — continua só a
  notificação interna 15 min antes (PDR-0016).

## Critérios de aceite

- Alternar entre lista e calendário não sai da página nem perde o
  filtro/data selecionada.
- As sub-abas "Delegados por mim" e "Agenda de outros usuários" só
  aparecem para quem tem a habilitação correspondente.
- Verificar disponibilidade mostra os compromissos existentes do
  convidado no horário selecionado, sem impedir a criação do
  compromisso.
