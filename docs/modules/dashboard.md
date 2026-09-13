# Módulo — Dashboard

Painel com duas abas: "Visão geral do escritório" (`dashboard:painel`) e
"Análise de dados" (`dashboard:analise`), derivadas de dados reais e
autorizados — nunca mock ou número fixo (ver [PRODUCT.md](../PRODUCT.md)).
Arquivo próprio pelo volume de regras de agrupamento/escopo específicas
do painel — ver [PRODUCT.md](../PRODUCT.md) para o padrão dos módulos
mais simples.

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

## Fora de escopo

- Painel "Intimações" — depende de e-mail de intimações, que não existe
  no sistema.
- Aba "Painel do gestor" — depende de log de atividade/auditoria
  genérico, que não existe em nenhum módulo hoje. Instrumentar login e
  ações em todos os módulos é uma feature própria, maior que este
  Dashboard; exige spec/PDR dedicada antes de iniciar (ver
  [STATUS.md](../STATUS.md#dashboard)).
- Ranking/avaliação automática de desempenho, predição por IA, analytics
  preditivo (fora de escopo do módulo, ver [PRODUCT.md](../PRODUCT.md)).

## Referências

- [STATUS.md](../STATUS.md#dashboard) para o estado real de implementação.
- [processos.md](processos.md) para os campos `estado`/`cidade`/
  `resultado_sentenca` e o modelo de Partes usado pelo patrocínio.
