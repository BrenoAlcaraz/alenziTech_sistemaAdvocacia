# Módulo — Dashboard

Painel com três abas: "Visão geral do escritório" (`dashboard:painel`),
"Análise de dados" (`dashboard:analise`) e "Painel do gestor"
(`dashboard:gestor`), derivadas de dados reais e autorizados — nunca
mock ou número fixo (ver [PRODUCT.md](../PRODUCT.md)). Arquivo próprio
pelo volume de regras de agrupamento/escopo específicas do painel — ver
[PRODUCT.md](../PRODUCT.md) para o padrão dos módulos mais simples.

## Visão geral — painéis derivados de Processos

Visíveis apenas quando o usuário tem o módulo `processos` habilitado,
aplicando o mesmo escopo `somente_seus`/`todos` já usado no card
"Processos ativos" (`Processo.responsavel`). Todos excluem processos
com `status="arquivado"`.

- **Movimentação processual**: processos distintos com
  `MovimentacaoProcessual.data` nas últimas 24h e nos últimos 7 dias
  (grupos não excludentes — qualquer movimentação nas últimas 24h está,
  por definição, também dentro dos últimos 7 dias).
- **Processos paralisados**: usa a data da última `MovimentacaoProcessual`
  de cada processo, com fallback para `data_distribuicao` quando não há
  nenhuma. Grupos cumulativos: +1 mês (>30 dias), +3 meses (>90 dias),
  +6 meses (>180 dias) — um processo de 6 meses parado também conta nos
  outros dois grupos.
- **Prazos a vencer**: usa `Processo.prazo_proximo` (não nulo, não
  vencido). Grupos cumulativos: hoje, amanhã, até 3 dias, até 5 dias.

## Card financeiro combinado e "Usuários ativos"

- O bloco financeiro do card de resumo mostra A receber, A pagar e
  Diferença (saldo = a_receber − a_pagar) num único card — mesma regra
  de acesso já existente (`dados_proprios`/`dados_todos`).
- "Usuários ativos" (contagem de `User` ativos, link para
  `configuracoes:index`) não depende do módulo Painel nem de
  Processos — aparece para quem tem a habilitação `gerir_criar_usuario`
  no módulo `gerir` (bypass automático do Administrador do escritório).

## Análise de dados

Só acessível/visível com o módulo `processos` habilitado. Ao contrário
dos painéis da Visão geral, **inclui processos arquivados** (mesma
regra já registrada em [processos.md](processos.md): processo arquivado
continua disponível em análise de dados).

- Filtros compartilhados pelos 4 blocos (natureza/localidade/status/
  patrocínio), todos por query string: Escopo (seletor só aparece
  quando o nível máximo do usuário no módulo `processos` é `todos`),
  Cliente, Equipe, e Usuário (só quando o escopo efetivo é `todos`).
- **Processos por localidade**: hierárquico Estado → Cidade → Vara
  (`Processo.vara_juizo`), com auto-skip de nível quando o subconjunto
  filtrado tem só uma opção naquele nível (não renderiza uma lista de
  1 item só). Usa os campos opcionais `Processo.estado`/`Processo.cidade`
  — ver [processos.md](processos.md).
- **Processos por patrocínio**: best-effort — casa `Processo.cliente`
  com uma `ParteProcesso` do mesmo processo por CPF/CNPJ normalizado
  (`apps.processos.services.patrocinio_do_processo`); sem
  correspondência (cliente não cadastrado como parte, ou processo sem
  cliente), entra em "Não identificado". Não é uma contagem exata —
  depende de o cliente também ter sido cadastrado manualmente como
  parte do processo (ver "Pontos em aberto" em
  [processos.md](processos.md) sobre materialização automática do
  Cliente como Parte).
- **Tempo e resultados**: tempo de vida médio considera só processos
  com `status="ativo"` e `data_distribuicao` preenchida; tempo médio
  entre andamentos usa todas as `MovimentacaoProcessual` do subconjunto
  filtrado, qualquer status; julgados procedente/parcial/improcedente
  conta `Processo.resultado_sentenca` só quando preenchido (sempre
  manual nesta versão, ver [processos.md](processos.md)).

## Intimações

Painel na Visão geral, visível junto com os demais painéis derivados de
Processos (mesma condição `acesso_processos`).

- Modelo `Intimacao` (`apps.processos.models`): `processo` (FK,
  obrigatório), `motivo`, `prazo_manifestacao`, `status`
  (`pendente`/`manifestada`), `origem` (`manual`/`email` — todo
  registro nesta versão nasce `manual`), `criado_por`, `criado_em`.
- **Criação manual** (`processos:nova_intimacao`): processo limitado ao
  escopo de mutação de quem cria (`_processos_mutaveis`, mesma regra
  dos demais formulários de Processo) — não é possível vincular a um
  processo fora desse escopo.
- Painel mostra só `status="pendente"`, dentro do mesmo escopo
  `somente_seus`/`todos` de Processos (baseado no processo vinculado),
  ordenado por `prazo_manifestacao`. Marcar como manifestada
  (`processos:manifestar_intimacao`) remove do painel imediatamente.
- **Sem leitura automática de e-mail nesta versão** — decisão e ticket
  de implementação (OAuth vs IMAP) ficam para quando essa integração
  for priorizada. Por isso a tela de "cadastro de e-mail de
  intimações" em Configurações também não foi construída.
- **Pendência futura explícita**: quando o sistema tiver um pipeline de
  IA/LLM em produção, revisitar para interpretar o e-mail e sugerir
  processo/prazo/motivo automaticamente — sempre com revisão humana
  antes de confirmar, nunca criando a Intimação direto sem confirmação.

## Painel do gestor

Visível para Administrador do escritório ou quem tem o módulo `gerir`
habilitado (`tem_permissao_modulo(user, MODULO_GERIR)`). Apoiado por um
log de atividade genérico novo, `apps.atividade.LogAtividade`
(`usuario`, `tipo`, `descricao`, `processo` opcional, `criado_em`) — só
leitura pela interface, nunca editável/removível. Gravado via
`apps.atividade.services.registrar_atividade`, chamado explicitamente
em cada ponto de escrita (nunca por signal genérico de
`post_save`/`post_delete` — a descrição legível exige o contexto que só
a view tem no momento da ação).

- **Fase 1 do catálogo de ações** (login + Processos): `login` (via
  `django.contrib.auth.signals.user_logged_in`); e, em
  `apps/processos/views.py`, `novo`, `editar`, `arquivar`, `reabrir`,
  `adicionar_movimentacao`, `adicionar_parte`, `editar_parte`,
  `adicionar_apenso`, `remover_apenso`, `adicionar_integrante`,
  `remover_integrante`, `adicionar_documento`, `excluir_documento`.
  Outros módulos (Financeiro, Tarefas, Agenda, Chat, Modelos) entram
  depois, sob demanda, reaproveitando o mesmo modelo/helper.
- **Lista de usuários**: todos os usuários ativos do tenant, com
  contagem de `LogAtividade` do dia (fuso local — zera à meia-noite).
- **Detalhe de atividade do usuário**: timeline do dia, ordem
  cronológica. Atalhos:
  - "Ir para Habilitações"/"Ir para Permissões" → ambos apontam para
    `configuracoes:usuario_overrides` (já cobre os dois).
  - "Grupos" → `configuracoes:usuario_equipes` (novo): equipes ativas
    do usuário, com toggle de adicionar/remover — mesmo modelo
    `MembroEquipe` de `equipe_membros`, só que pela perspectiva do
    usuário.
  - "Habilitar em processos" → `configuracoes:usuario_processos_habilitados`
    (novo): filtro por Cliente/Matéria/Data/Busca sobre a lista de
    processos, toggle persistindo em `Processo.integrantes_habilitados`
    — cada linha grava na hora (sem checklist com "Salvar" ao final),
    então trocar o filtro nunca perde uma seleção ainda não salva.
    Mesma habilitação de `adicionar_integrante`/`remover_integrante`
    (`gerir_habilitar_usuario_processos`), e gera o mesmo
    `LogAtividade` que esses dois pontos de entrada.
  - "Ir para Tarefas"/"Ir para Agenda" → `tarefas:quadro?usuario=<id>`
    e `agenda:index?usuario=<id>` (novo suporte a esse parâmetro): só
    tem efeito para quem tem `gerir`/é Administrador — para qualquer
    outro usuário o parâmetro é ignorado (nunca vira brecha de escopo).

## Fora de escopo

- Ranking/avaliação automática de desempenho, predição por IA, analytics
  preditivo (fora de escopo do módulo, ver [PRODUCT.md](../PRODUCT.md)).
- Retenção/expurgo automático do `LogAtividade` — nenhuma política de
  limpeza nesta versão; revisitar junto com o ciclo de vida de tenant
  (OPEN-002 em [STATUS.md](../STATUS.md)) e possíveis obrigações de
  LGPD antes do volume crescer.
- Auditoria de segurança formal (trilha imutável, hash-chain,
  exportação para compliance) — o `LogAtividade` serve à gestão de
  equipe, não a um requisito regulatório específico ainda.

## Referências

- [STATUS.md](../STATUS.md#dashboard) para o estado real de implementação.
- [processos.md](processos.md) para os campos `estado`/`cidade`/
  `resultado_sentenca` e o modelo de Partes usado pelo patrocínio.
