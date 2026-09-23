# Spec — Agenda Jurídica (fusão de Tarefas e Agenda)

Decisão de produto: [PDR-0034](../docs/decisions/PDR-0034-agenda-juridica-unificada.md).
Execução em 3 tickets (GitHub Issues), nesta ordem: #31 → #32 → #33.

## Objetivo

Um único lugar onde o advogado vê e organiza tudo o que tem pela frente
— afazeres internos, prazos processuais e compromissos com hora —
substituindo os módulos Tarefas e Agenda por um módulo só, "Agenda
Jurídica", sem perder nenhum comportamento que hoje importa.

## Comportamento esperado

### Item da agenda

Um único item (`ItemAgenda`, evolução de `Compromisso` em `apps/agenda`)
com tipo de catálogo fixo. A natureza é derivada do tipo e define os
campos e ações:

| Natureza | Tipos | Datas | Específico |
|---|---|---|---|
| Afazer | Tarefa, Prazo, Protocolo, Retorno | data para fazer (opcional, hora opcional); data fatal (opcional; obrigatória em Prazo) | prioridade; kanban |
| Evento | Audiência, Reunião, Perícia, Julgamento | início obrigatório com hora; fim opcional; dia inteiro | local; confirmação de presença; lembrete 15 min |

- Afazer sem nenhuma data é permitido: aparece só em lista/kanban
  ("Sem data"), nunca no calendário.
- Campos comuns: título, descrição, responsável, participantes,
  cliente, processo (integridade cliente↔processo como hoje), criador,
  atribuidor/atribuído em, convite de delegação.
- Na interface não há nome genérico: o usuário vê o tipo; o botão é
  "+ Novo" com escolha de tipo. "Atividade" continua reservado ao log
  (`apps/atividade`).

### Status

Um conjunto: A fazer / Em andamento / Concluído / Cancelado.
- Evento não oferece "Em andamento".
- Concluído/Cancelado podem ser reabertos.
- Cancelado sai das visões operacionais, fica consultável em
  "Cancelados" por 7 dias a partir do cancelamento e é expurgado
  (regra que hoje vale só para compromisso passa a valer para todos).
- Cancelar avisa responsável e participantes.

### Responsável, participantes, delegação

- Um responsável formal. Só responsável ou Administrador edita, muda
  status, reatribui, exclui e gerencia participantes.
- Participante sempre vê o item. Em Evento, confirma/recusa presença
  (PDR-0020) e recebe lembrete se confirmado; reagendar volta
  confirmados para pendente e os avisa. Em Afazer, só visibilidade.
- Criar com responsável ≠ criador exige a habilitação "atribuir a
  outros"; direto vs convite segue PDR-0033 para qualquer tipo.
- Reatribuição existe para qualquer item, com histórico (anterior,
  novo, autor, data), livre como hoje em Tarefas.
- Na criação, "Atribuir a" (vários) + "Responsável" entre os
  atribuídos, como em Tarefas hoje; equipe como atalho (PDR-0028).
- Verificação de disponibilidade de convidado (Evento) mantida.

### Prazo gerado pelo processo

- Todo `MovimentacaoProcessual` com `data_prazo` gera exatamente um
  item tipo Prazo, vinculado ao andamento de origem, ao processo e ao
  cliente, com responsável = `Processo.responsavel`, sem convite.
- Data fatal = `data_prazo`, travada no item (editável só no
  andamento). Data para fazer padrão = fatal − 2 dias corridos,
  editável.
- Alterar `data_prazo` atualiza o item e notifica o responsável;
  remover o prazo ou apagar o andamento remove o item.
- Vale para qualquer origem de andamento (manual hoje, API no futuro).
- Processo sempre tem responsável (FK obrigatória; exclusão/perda de
  acesso transfere ao Administrador). Quando o responsável do processo
  muda, os Prazos gerados por andamento ainda não concluídos nem
  cancelados passam automaticamente para o novo responsável; Prazo
  concluído/cancelado mantém o histórico e Prazo manual segue a
  reatribuição normal.
- Prazo criado manualmente (sem andamento) é permitido, com data fatal
  editável.

### Notificações (in-app)

- Evento: lembrete 15 min antes ao responsável e participantes
  confirmados (mantém PDR-0016/0020).
- Afazer com data fatal: aviso no dia anterior e no dia da fatal, se
  não concluído.
- Prazo: aviso quando passar a data para fazer sem conclusão.
- Atribuição (direta ou reatribuição) e convite de delegação recebido:
  aviso ao destinatário.
- Conclusão: aviso ao criador (mantém PDR-0016).
- Cada aviso é enviado uma única vez por item/destinatário/motivo.

### Tela

Menu "Agenda Jurídica" (substitui Tarefas e Agenda). Uma página com:

- Cabeçalho: título, "+ Novo" (escolha de tipo), link "Cancelados".
- Aviso fixo com contador "Convites recebidos (n)" quando houver, com
  aceitar/recusar (justificativa opcional) sem sair da página.
- Barra de filtros única, aplicada a todas as visões e preservada ao
  alternar: Tipo, Natureza, Escopo (meus/todos, conforme nível),
  Pessoa (só `gerir`/Admin — ver agenda de outro; "+ Novo para esta
  pessoa" trava o responsável), "Delegados por mim", Origem
  (manual/gerado pelo processo), Processo, Cliente.
- Visões (alternância sem recarregar dados, como a Agenda hoje):
  - Meu dia/Semana (padrão): grupos Atrasados · Hoje · Amanhã ·
    Próximos 7 dias · Sem data. Atrasado = afazer não concluído com
    data (fatal ou para fazer) no passado, ou evento agendado já
    passado.
  - Calendário mensal: afazer na data para fazer (ou na fatal, se só
    houver ela), marcador vermelho no dia da fatal; evento no início;
    cor por tipo; clicar no dia lista os itens.
  - Kanban: só afazeres, colunas por status, ordenação (prazo,
    prioridade, recentes) como hoje em Tarefas.
- Card comum: ícone/cor do tipo, título, datas (fatal destacada
  quando ≤ 3 dias ou vencida), responsável, processo/cliente, selo de
  origem "Processo" em prazo gerado, estado do convite, ações
  permitidas. Evento mostra local e minha presença.
- Formulário único: tipo primeiro; campos mudam pela natureza; data
  fatal só leitura em prazo gerado, com link para o andamento.

### Permissões

- Um módulo `agenda` (níveis somente_seus/todos). "Todos" continua
  sendo escopo de leitura, nunca de mutação.
- Uma habilitação "atribuir a outros".
- Ver agenda de outro usuário: `gerir`/Admin.
- Permissões/overrides existentes de `tarefas` são migrados para
  `agenda` (maior nível e união das habilitações).

### Integrações

- Detalhe de Processo e Cliente: card "Agenda do processo/cliente"
  (itens de qualquer tipo, "+ Novo" pré-preenchido, "ver todos" com
  filtro).
- Aba Prazos do processo mantém a timeline, cada prazo leva ao item.
- Dashboard: "Prazos a vencer" lê itens tipo Prazo; blocos de
  tarefas e de confirmados/pendentes adaptados ao novo modelo.
- Painel do gestor: um atalho "Ir para Agenda Jurídica" filtrado por
  usuário.
- Log de atividade continua registrando criação/edição/status/
  reatribuição/exclusão.
- Rotas `/tarefas/...` redirecionam para a Agenda Jurídica.

## Regras de negócio relevantes

- Tarefas existentes (dados de teste) são migradas para itens tipo
  Tarefa preservando responsável, participantes, status, prazo (vira
  data fatal), prioridade, vínculos, convite e histórico de
  reatribuição; `apps/tarefas` é removido.
- Andamentos existentes com `data_prazo` geram seus itens Prazo na
  migração.
- Autorização e escopo sempre no backend, com os mesmos controles de
  tenant, IDOR e convite já estabelecidos.

## Fora do escopo

Integração por API de andamentos (feature separada); arrastar e
soltar em calendário/kanban; recorrência; checklist/subtarefas;
modelos de fluxo de trabalho; dias úteis/feriados; catálogo legal de
prazos (`specs/agenda-prazos-processuais-automaticos.md`, agora
evolução futura sobre esta base); Google/Outlook; e-mail/push/SMS;
catálogo de tipos configurável por escritório.

## Critérios de aceite

- Não existe mais menu/módulo Tarefas; "Agenda Jurídica" cobre todos
  os fluxos acima; `/tarefas/` redireciona.
- Criar cada tipo mostra só os campos da sua natureza; Prazo sem data
  fatal é rejeitado; afazer sem data aparece em "Sem data".
- Lançar andamento com prazo cria um Prazo para o responsável do
  processo; alterar a data atualiza e notifica; apagar remove; nunca
  duplica.
- Delegação, convite, reatribuição, participantes e presença seguem as
  regras acima para todos os tipos, validadas no backend.
- As 3 visões e todos os filtros funcionam juntos; filtro de
  processo/cliente vale em todas.
- Notificações disparam uma única vez por motivo.
- Permissões antigas de `tarefas` continuam dando o mesmo acesso após
  a migração.
- Dashboard, Processo, Cliente e Painel do gestor mostram os dados do
  novo modelo.
- Testes existentes de Tarefas e Agenda são portados para o novo
  módulo cobrindo autorização, escopo, convite, participantes,
  lembretes e expurgo.
