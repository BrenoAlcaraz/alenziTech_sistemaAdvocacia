---
id: PDR-0034
title: Agenda Jurídica — fusão de Tarefas e Agenda
status: accepted
owner: product-and-engineering
decision_date: 2026-09-23
last_reviewed: 2026-09-23
supersedes: []
partially_supersedes:
  - PDR-0016
  - PDR-0020
complements:
  - PDR-0002
  - PDR-0033
source_files: []
---

# PDR-0034 — Agenda Jurídica: fusão de Tarefas e Agenda

## Contexto

Tarefas (afazeres internos) e Agenda (compromissos com hora) eram
módulos separados com responsável, participantes, convite de delegação,
vínculo cliente/processo, escopo e sub-abas praticamente idênticos. O
prazo processual vivia num terceiro lugar (`data_prazo` do andamento,
visível só no Processo e no Dashboard), fora de onde o advogado
organiza o dia. Para o usuário isso significava três lugares para saber
o que tem pela frente; para o código, duplicação crescente.

Referência de mercado (Astrea, EasyJur, Projuris, Legal One, ADVBOX): os
sistemas brasileiros convergem para uma agenda única com item tipado,
kanban como visão das mesmas atividades e prazo com data interna e data
fatal.

## Decisão

- Tarefas e Agenda viram um só módulo, **"Agenda Jurídica"**, com um
  único item tipado. O termo "atividade" permanece reservado ao log de
  atividade.
- Catálogo de tipos **fixo**, em duas naturezas que definem o
  comportamento:
  - **Afazer** (Tarefa, Prazo, Protocolo, Retorno): data para fazer
    (opcional), data fatal (obrigatória em Prazo), prioridade; pode não
    ter data.
  - **Evento** (Audiência, Reunião, Perícia, Julgamento): início com
    hora, fim, local, confirmação de presença de participante.
- **Status único**: A fazer, Em andamento, Concluído, Cancelado (evento
  sem "Em andamento"). Cancelado de qualquer tipo segue a retenção de 7
  dias hoje aplicada a compromisso.
- **Participante** sempre vê o item; confirmação de presença e lembrete
  só em Evento (PDR-0020 restrito a essa natureza).
- **Delegação** por convite (PDR-0033) vale para todos os tipos;
  reatribuição com histórico passa a existir para qualquer item.
- **Prazo processual**: todo andamento com prazo gera automaticamente
  um item Prazo para o responsável do processo, sem convite, com data
  fatal travada na origem e data para fazer padrão de 2 dias corridos
  antes; independe de o andamento ser manual ou vir de integração
  futura.
- **Notificações** (in-app) ampliadas: além do lembrete de 15 minutos de
  Evento e do aviso de conclusão ao criador (PDR-0016), avisos de data
  fatal (véspera e dia), de data para fazer vencida em Prazo, de
  atribuição/reatribuição e de convite recebido.
- **Permissões**: um módulo `agenda`, uma habilitação "atribuir a
  outros"; ver agenda de outro usuário exige `gerir`/Administrador.
- **Tela**: visões Meu dia/Semana (padrão), Calendário e Kanban (só
  afazeres) sobre os mesmos dados, com uma barra de filtros única no
  lugar das sub-abas.

## Consequências

- `apps/tarefas` é removido; dados e permissões migram para `agenda`.
- PDR-0016 é parcialmente substituído: deixa de ser verdade que
  notificação de atribuição/reatribuição/prazo de tarefa está fora de
  escopo.
- PDR-0020 é parcialmente substituído: confirmação de presença passa a
  se aplicar só à natureza Evento.
- Dashboard, Processo, Cliente e Painel do gestor passam a ler o item
  unificado.
- `specs/agenda-prazos-processuais-automaticos.md` (catálogo legal de
  prazos) vira evolução futura sobre esta base, sem bloqueá-la.

## Fora do escopo desta decisão

Integração por API de andamentos; arrastar e soltar; recorrência;
checklist/subtarefas; fluxos de trabalho; dias úteis; sincronização com
calendários externos; canais externos de notificação; catálogo de tipos
configurável por escritório.
