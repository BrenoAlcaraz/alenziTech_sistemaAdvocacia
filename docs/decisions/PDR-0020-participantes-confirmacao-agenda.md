---
id: PDR-0020
title: Participantes e confirmação de presença em Compromisso (Agenda)
status: accepted
owner: product-and-engineering
decision_date: 2026-09-08
last_reviewed: 2026-09-08
supersedes: []
complements:
  - PDR-0016
source_files: []
---

# PDR-0020 — Participantes e confirmação de presença em Compromisso (Agenda)

## Contexto

O campo `Compromisso.participantes` existia desde a modelagem original da
Agenda, sem formulário, sem efeito sobre escopo de leitura e sem fluxo de
confirmação — gap registrado em [STATUS.md](../STATUS.md#módulos)
("Escopo por participante não existe... sem regra de produto") e
correspondente à Rodada 2.4 da sequência de
[PDR-0009](PDR-0009-sequencia-fase-2.md). Esta decisão fecha esse gap.

## Decisão

Compromisso passa a ter, além do responsável obrigatório, N participantes
com confirmação de presença individual:

- status por participante: pendente, confirmado ou recusado;
- o responsável nunca passa por esse fluxo — está implicitamente
  confirmado no próprio compromisso;
- confirmar/recusar é ação do próprio participante sobre o próprio
  registro, sem checagem de habilitação;
- gerenciar participantes (adicionar/remover) reaproveita a autorização
  de edição do compromisso já existente — sem habilitação granular
  nova;
- escopo de leitura `somente_seus` passa a incluir compromisso onde o
  usuário é participante (qualquer status), além de onde é responsável;
  escopo `todos` não muda;
- reagendar (mudar `data_hora_inicio`) reseta para pendente a
  confirmação já dada e notifica cada participante afetado;
- lembrete automático (PDR-0016) passa a alcançar também participante
  confirmado, com controle de envio próprio por participante — pendente
  ou recusado nunca recebe;
- cancelar (`status=cancelado`) notifica responsável e todos os
  participantes (qualquer status) com mensagem distinta de
  convite/lembrete, e o compromisso sai da grade operacional padrão da
  Agenda para todos os envolvidos, ficando disponível só para consulta
  por até 7 dias — contados da data do **cancelamento**, não da data
  original do compromisso — numa seção própria ("Cancelados"), sem
  opção de reativar, antes de expurgo automático definitivo;
- Dashboard passa a ter dois blocos sempre pessoais, independentes do
  nível `somente_seus`/`todos` do módulo: próximos compromissos
  confirmados dos próximos 7 dias (responsável ou participante
  confirmado), e contador de confirmação pendente com
  confirmar/recusar diretamente do painel.

## Regras obrigatórias

- Nenhuma view do módulo Agenda passa a exigir habilitação granular
  nova como consequência desta decisão — `agenda_criar_para_outros`
  continua sendo a única habilitação do módulo, com o mesmo escopo de
  sempre (rege só atribuição de responsável a terceiro; não rege
  gerenciar participante nem confirmar/recusar presença).
- `cancelar` é idempotente: reexecutar sobre um compromisso já
  cancelado não reseta `cancelado_em` nem reenvia a notificação de
  cancelamento.

## Consequências

- Compromisso cancelado deixa de aparecer na listagem padrão da Agenda
  para qualquer usuário, inclusive Administrador do escritório —
  mudança de comportamento esperada (antes aparecia junto no filtro
  "Todos"), não regressão.
- `docs/STATUS.md`, linha de Agenda, passa a registrar participantes,
  confirmação de presença, cancelamento consultável com expurgo
  automático e os blocos pessoais do Dashboard como implementados.

## Fora do escopo desta decisão

- Geração automática de prazo processual a partir de andamento —
  tratada em spec própria
  (`specs/agenda-prazos-processuais-automaticos.md`), parada aguardando
  validação jurídica externa; nada nesta decisão antecipa ou condiciona
  aquela feature futura.
- Convite de participante para pessoa fora do escritório (cliente,
  terceiro) — participante continua restrito ao mesmo universo de
  usuário interno já usado para responsável.
- Janela de retenção do compromisso cancelado configurável pelo
  usuário — fixa em 7 dias nesta versão.
- Qualquer alteração aos módulos Processos ou Tarefas, ou aos conceitos
  de responsável/integrante desses módulos (PDR-0014).

## Critérios de aceite funcionais

- Usuário marcado como participante vê o compromisso no escopo
  `somente_seus` mesmo sem ser responsável; recusar presença não o
  remove da própria agenda.
- Reagendar volta a confirmação de participante já confirmado para
  pendente e notifica cada um deles.
- Lembrete de 15 minutos antes (PDR-0016) chega só para responsável e
  participante confirmado.
- Cancelar notifica responsável e participantes, remove o compromisso
  da grade operacional da Agenda para todos, e ele fica consultável na
  seção "Cancelados" por 7 dias a partir do cancelamento antes de
  expurgo automático.
- Adicionar/remover participante exige a mesma autorização de edição do
  compromisso já existente hoje — nenhuma habilitação nova aparece no
  painel de permissões.
- Reexecutar `cancelar` sobre compromisso já cancelado não altera
  `cancelado_em` nem gera notificação duplicada.

## Fontes

- Issues #8 e #9 do repositório (implementação, revisão e testes);
  spec `specs/agenda-participantes-confirmacao.md` (apagada após esta
  promoção, conforme [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
