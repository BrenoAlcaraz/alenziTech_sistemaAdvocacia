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
- **Prazos a vencer**: itens tipo Prazo da Agenda Jurídica em aberto,
  pela data fatal (não vencida), no escopo de leitura da agenda do
  usuário (PDR-0034) — exige o módulo Agenda Jurídica, não Processos.
  Grupos excludentes: hoje, amanhã, em 2–3 dias, em 4–5 dias; cada prazo
  aparece uma única vez na tela e leva ao item. Hoje e amanhã ficam na
  faixa "Hoje"; os demais, no bloco "Prazos a vencer" logo abaixo dela.

## Faixa "Hoje"

Primeiro bloco da Visão geral, antes de qualquer card de indicador. Só
reúne o que o Painel já calcula, com a autorização de cada origem:
prazos com data fatal hoje e amanhã e convites de Evento aguardando
resposta (módulo Agenda Jurídica), intimações pendentes (módulo
Processos). Cada item leva ao registro; sem nada pendente, mostra um
estado vazio positivo.

- O card "Afazeres pendentes" não conta os prazos da janela de 5 dias
  (já contados na faixa/"Prazos a vencer") — nenhum prazo é contado duas
  vezes na tela.
- "Marcar como manifestada" (efeito jurídico) só grava depois de
  confirmação em diálogo; voltar não altera nada.

## Cards financeiros e "Usuários ativos"

Cards financeiros por nível de acesso ao módulo Financeiro. Cada número
usa a mesma regra e o mesmo escopo do filtro do Financeiro para onde o
clique leva (o clique carrega o período). Cancelado (lançamento/
honorário) e rejeitada (solicitação) nunca entram. "Atrasado" =
pendente vencido antes de hoje, de qualquer mês, sempre exibido separado
do que vence no período.

**Período** (`?periodo=dia|semana|mes`): seletor Dia | Semana | Mês
acima dos cards financeiros — só eles mudam. Dia = hoje; Semana =
segunda a domingo corrente; Mês = mês civil corrente (fuso local).
Padrão Dia, e o período nunca é lembrado: sem o parâmetro (ou com valor
inválido) o Painel volta a Dia. O que é "vence no período" vai de hoje
ao fim do período (o que venceu antes já é atrasado); saldo previsto e
honorários usam a janela inteira. Fila de solicitações abertas e custas
a cobrar são estado atual e não mudam com o período.

- **Nível `solicitacoes`** (só as próprias solicitações):
  - *Solicitações pendentes*: quantidade e valor das abertas
    (`solicitada`/`em_analise`/`aprovada`), com "X vencidas" e "X
    vencem no período" → lista `situacao=pendentes`
    (`vencimento=vencidas` / `vencimento=dia|semana|mes`).
  - *Pagas no período*: `paga` com `data_pagamento` na janela → lista
    `situacao=pagas` com `pago_de`/`pago_ate`.
- **Nível de dados** (`dados_proprios` só lançamentos em que é
  `responsavel`; `dados_todos` o escritório):
  - *A pagar* / *A receber*: despesas/receitas pendentes que vencem no
    período, mais a linha de atrasadas → filtros
    `apagar_periodo`/`areceber_periodo` (com `periodo=`) e
    `apagar_atrasados`/`areceber_atrasados`. Contam todos os
    lançamentos pendentes (o que há para pagar/receber), inclusive
    custas e reembolsos de cliente — a exclusão do PDR-0029 vale para os
    totais de resumo, não para a fila de pendências.
  - *Solicitações em aberto*: total do escritório (mesmo número de
    "Solicitações (n)"), dividido em aguardando análise
    (`solicitada`+`em_analise`) e aprovadas aguardando pagamento, com
    destaque para vencidas e que vencem no período.
- **Administrador do escritório**: os cards do nível de dados, mais:
  - *Saldo previsto*: a fórmula do saldo previsto do Financeiro
    (PDR-0029: a receber + recebido − a pagar − pago, pendentes pelo
    vencimento e pagos pela data de pagamento) aplicada à janela, com
    "realizado até agora" (recebido − pago) → Financeiro com o mesmo
    `periodo=` (em Mês, é exatamente o saldo do mês corrente).
  - *Honorários previstos*: receitas de honorários/sucumbência com
    vencimento na janela (pagas em recebido e previsto) + saldo
    pendente do contratual de valor único ainda previsto na janela
    (`valor_efetivo`, ou `valor_estimado`, − `valor_recebido`), que só
    vira lançamento ao ser confirmado. Êxito e sucumbência sem
    lançamento não entram; nada é contado duas vezes → aba Honorários
    (sem filtro). Honorário único pendente aparece só aqui — não entra
    no saldo previsto nem no a receber.
  - *Custas a cobrar*: soma dos saldos de custas negativos e quantidade
    de devedores — os mesmos do filtro "Em débito" da tela de Custas
    (clientes ativos fora de grupo e grupos) → `custas?saldo=em_debito`.
- "Usuários ativos" (contagem de `User` ativos, link para
  `configuracoes:index`) não depende do módulo Painel nem de
  Processos — aparece para quem tem a habilitação `gerir_criar_usuario`
  no módulo `gerir` (bypass automático do Administrador do escritório).

## Análise de dados

Só acessível/visível com o módulo `processos` habilitado. Ao contrário
dos painéis da Visão geral, **inclui processos arquivados** (mesma
regra já registrada em [processos.md](processos.md): processo arquivado
continua disponível em análise de dados).

- Filtros compartilhados por todos os blocos (natureza/localidade/
  status/fase/fase do andamento/patrocínio/clientes por localidade),
  todos por query string: Escopo (seletor só aparece quando o nível
  máximo do usuário no módulo `processos` é `todos`), Cliente, Equipe,
  e Usuário (só quando o escopo efetivo é `todos`).
- **Processos por localidade**: hierárquico Estado → Cidade → Comarca →
  Vara (`Processo.comarca`/`Processo.vara` — campo único `vara_juizo`
  separado em dois na reunião de 13/09), com auto-skip de nível quando o
  subconjunto filtrado tem só uma opção naquele nível (não renderiza uma
  lista de 1 item só). Usa os campos opcionais `Processo.estado`/`Processo.cidade`
  — ver [processos.md](processos.md).
- **Processos por fase**: usa `Processo.fase` (Conhecimento/Recursal/
  Cumprimento de Sentença/Execução/Outro), já existente — só expõe como
  bloco novo, sem exigir preenchimento retroativo.
- **Fase do andamento atual**: usa `Processo.fase_andamento_atual` (ver
  [processos.md](processos.md)); inclui "Não informado" para quem ainda
  não preencheu o campo. **Sem sugestão automática** por tipo de
  andamento nesta versão — campo só é preenchido manualmente a partir
  do formulário de "Adicionar andamento".
- **Clientes por localidade**: mesmo padrão hierárquico de "Processos
  por localidade", mas Estado → Cidade → Bairro e usando o endereço do
  próprio `Cliente` (não a comarca do processo). Restrito aos clientes
  vinculados (`processo.clientes`) aos processos já filtrados pelo
  escopo/filtros da página — um cliente com vários processos no
  subconjunto conta uma vez só.
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

- **Catálogo de ações**: `login`/`logout` (via
  `user_logged_in`/`user_logged_out`);
  Processos (`apps/processos/views.py`: `novo`, `editar`, `arquivar`,
  `reabrir`, `adicionar_movimentacao`, `adicionar_parte`,
  `editar_parte`, `adicionar_apenso`, `remover_apenso`,
  `adicionar_integrante`, `remover_integrante`, `adicionar_documento`,
  `excluir_documento`); e, no mesmo padrão, os pontos de escrita de
  Agenda Jurídica, Financeiro (lançamentos, custas, honorários,
  solicitações), Clientes e Configurações (usuários, equipes, papéis,
  permissões, dados do escritório). Chat e Modelos seguem fora do
  catálogo — entram depois, sob demanda, reaproveitando o mesmo
  modelo/helper.
- `LogAtividade.TIPOS_NAO_PRODUTIVOS = {"login", "logout"}` — os dois
  continuam gravados, mas nunca contam nos contadores de ação
  produtiva (lista de usuários abaixo).
- **Lista de usuários**: todos os usuários ativos do tenant, com
  contagem de ações produtivas do dia, da semana (segunda a domingo,
  fuso local) e do mês corrente (fuso local) — `login`/`logout`
  excluídos das três contagens.
- **Minha atividade** (`dashboard:minha_atividade`, link em
  Configurações): qualquer usuário autenticado vê a própria timeline do
  dia, sem depender do módulo `gerir`/Painel — estritamente escopada ao
  usuário logado.
- **Detalhe de atividade do usuário** (painel do gestor): timeline do
  dia, ordem cronológica. Atalhos:
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
  - "Ir para Agenda Jurídica" → `agenda:index?usuario=<id>`: só tem
    efeito para quem tem `gerir`/é Administrador — para qualquer outro
    usuário o parâmetro é ignorado (nunca vira brecha de escopo).

## Fora de escopo

- Ranking/avaliação automática de desempenho, predição por IA, analytics
  preditivo (fora de escopo do módulo, ver [PRODUCT.md](../PRODUCT.md)).
- Tempo de tela ativo, detecção de inatividade e métricas de
  produtividade baseadas em tempo (duração de sessão, tempo entre
  ações) — o log de atividade conta ações, nunca tempo.
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
