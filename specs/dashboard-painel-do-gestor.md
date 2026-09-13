# Dashboard — aba "Painel do gestor" + log de atividade

## Objetivo

Implementar a aba "Painel do gestor" do protótipo
(`docs/prototipos/dashboard-prototipo.html`), apoiada por um log de
atividade genérico novo. Fase 1 do log cobre só login e o módulo
Processos — outros módulos entram depois, sob demanda.

## Decisões já tomadas (não reabrir sem novo pedido)

- Log registra só **ações de escrita**, nunca visualização/abertura de
  tela (diferente do texto do protótipo, que citava "abriu o
  processo X" como exemplo).
- Fase 1 do catálogo de ações: login + tudo que já é escrita em
  `apps/processos/views.py`.
- Os 4 atalhos do detalhe do usuário que o protótipo assumia como
  "reaproveitamento" (Grupos, Habilitar em processos, Ir para Tarefas,
  Ir para Agenda) **não existem hoje** em nenhuma tela — verificado no
  código. Serão construídos nesta spec, não adiados.

## Comportamento esperado

### Log de atividade (novo, app `apps.atividade`)

- Modelo `LogAtividade`: `usuario` (FK User), `tipo` (catálogo fechado
  em código — ver lista abaixo), `descricao` (texto já pronto para
  exibição, montado no momento do registro — não reconstruído depois a
  partir de FK), `processo` (FK `Processo`, opcional,
  `on_delete=SET_NULL` — só a fase 1 usa; módulos futuros que não sejam
  Processo deixam em branco), `criado_em` (auto_now_add).
- Helper único de registro (`registrar_atividade(usuario, tipo,
  descricao, processo=None)`), chamado explicitamente em cada ponto de
  escrita — sem signal genérico de `post_save`/`post_delete` (a
  descrição legível exige contexto que só a view tem no momento da
  ação).
- Grava na mesma transação da ação principal — sem tratamento especial
  de falha; se o registro do log falhar, a ação inteira falha (simples,
  sem caminho paralelo silencioso).
- Catálogo de ações da fase 1:
  - `login` — via `django.contrib.auth.signals.user_logged_in` (único
    caso que usa signal, pois não há uma "view de login" própria a
    instrumentar).
  - Em `apps/processos/views.py`: `novo`, `editar`, `arquivar`,
    `reabrir`, `adicionar_movimentacao`, `adicionar_parte`,
    `editar_parte`, `adicionar_apenso`, `remover_apenso`,
    `adicionar_integrante`, `remover_integrante`,
    `adicionar_documento`, `excluir_documento`.

### Aba "Painel do gestor" (`dashboard:gestor`, nova)

- Visível para Administrador do escritório ou quem tem o módulo
  `gerir` habilitado (`tem_permissao_modulo(user, MODULO_GERIR)`) —
  igual à regra já usada em outras áreas de gerência.
- **Lista de usuários**: todos os usuários ativos do tenant — nome,
  papel principal (reaproveita `obter_papel_principal_usuario`/
  `nome_legivel_grupo`, já usados em
  `apps/configuracoes/views.py::index`), contagem de `LogAtividade` de
  hoje (fuso local — vira 0 à meia-noite). Clicar abre o detalhe.
- **Detalhe de atividade do usuário**: timeline do dia (tipo +
  descrição + hora, ordem cronológica). Atalhos:
  - "Ir para Habilitações" e "Ir para Permissões" → ambos apontam para
    `configuracoes:usuario_overrides` (já existe e já cobre os dois).
  - "Grupos" (**novo**) → mostra as equipes ativas desse usuário
    (`MembroEquipe.objects.filter(usuario=..., ativo=True)`), com ação
    de adicionar/remover de uma equipe ali mesmo — sem duplicar
    `configuracoes:equipe_membros`, só uma visão "pelo usuário" sobre
    o mesmo modelo `MembroEquipe`.
  - "Habilitar em processos" (**novo**) → tela em Configurações, pela
    perspectiva do usuário: filtro por Cliente/Matéria/Data/Busca sobre
    a lista de processos, checklist persistindo a seleção em
    `Processo.integrantes_habilitados`. Mesma autorização de
    `adicionar_integrante`/`remover_integrante`
    (`gerir_habilitar_usuario_processos`).
  - "Ir para Tarefas" (**novo suporte**) → `tarefas:quadro?usuario=<id>`;
    a view `quadro` passa a aceitar esse parâmetro, com efeito só
    quando quem pede tem `gerir` ou é Administrador (senão o parâmetro
    é ignorado e o comportamento atual — escopo do próprio usuário
    logado — permanece).
  - "Ir para Agenda" (**novo suporte**) → mesma ideia em
    `agenda:index?usuario=<id>`.

## Regras de negócio relevantes

- O log é só leitura pela interface — nunca editável/removível.
- Nenhuma ação de escrita ganha uma nova camada de autorização por
  causa do log; ele é efeito colateral de uma ação já autorizada hoje.
- `?usuario=` em Tarefas/Agenda só tem efeito para quem tem `gerir`/é
  Administrador — outro usuário usando o parâmetro é ignorado, nunca
  vira brecha de escopo.

## Fora de escopo

- Módulos além de login e Processos nesta fase (Financeiro, Tarefas,
  Agenda, Chat, Modelos) — entram depois, sob demanda, reaproveitando
  o mesmo `LogAtividade`/`registrar_atividade`.
- Qualquer registro de leitura/visualização de tela.
- Retenção/expurgo automático do log — nenhuma política de limpeza
  nesta versão; revisitar junto com o ciclo de vida de tenant
  (OPEN-002 em `docs/STATUS.md`) e possíveis obrigações de LGPD antes
  do volume crescer ou de expor o log a outros consumidores.
- Auditoria de segurança formal (trilha imutável, hash-chain,
  exportação para compliance) — este log serve à gestão de equipe, não
  a um requisito regulatório específico ainda.

## Critérios de aceite

- Login bem-sucedido e cada ação de escrita listada em Processos geram
  exatamente 1 `LogAtividade`, com descrição legível (ex: "Adicionou
  andamento (Contestação) na Ação de Danos Morais").
- Aba Painel do gestor invisível para quem não é Admin nem tem `gerir`
  habilitado — inclusive por acesso direto à URL (`PermissionDenied`).
- Lista de usuários mostra contagem correta de ações de hoje.
- Detalhe do usuário mostra timeline do dia em ordem cronológica.
- "Ir para Tarefas"/"Ir para Agenda" com `?usuario=` só filtra de fato
  para quem tem `gerir`/Admin.
- "Habilitar em processos" e "Grupos" persistem mudança real em
  `integrantes_habilitados`/`MembroEquipe`.
