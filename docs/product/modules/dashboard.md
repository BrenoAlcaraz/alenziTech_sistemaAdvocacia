---
title: Dashboard
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
related_pdrs:
  - PDR-0004
  - PDR-0009
---

# Dashboard

## Objetivo

Apresentar indicadores operacionais, jurídicos, financeiros e
gerenciais derivados de dados reais e autorizados.

## Escopo funcional

O Dashboard organiza três áreas:

1. visão geral do escritório;
2. análise de dados;
3. painel do gestor.

Esta especificação descreve o comportamento pretendido dessas três
áreas. Ela não afirma que todas já estão implementadas — o estado real
de implementação é responsabilidade de um documento de current-state
futuro, não desta especificação.

## Atores e expectativas de acesso

- O Administrador do escritório possui expectativa de supervisão
  ampla dentro do tenant.
- Usuários habilitados podem acessar áreas gerenciais autorizadas,
  incluindo o painel do gestor.
- Um usuário comum acessa somente indicadores compatíveis com seu
  papel e escopo de dados.
- O alcance exato pertence à futura matriz de autorização, em
  `docs/security/`, ainda não criado.
- O backend deve filtrar agregações e registros de origem; ocultar ou
  exibir um card na interface não substitui essa filtragem.

## Conceitos e entidades

O Dashboard não introduz conceitos próprios de domínio. Ele apresenta
indicadores derivados de entidades definidas em outros módulos —
especialmente Processos, Financeiro, Tarefas, Agenda e Equipes —,
conforme o [glossário funcional](../glossary.md). Os indicadores
financeiros seguem as definições de previsto e realizado de
[PDR-0004](../decisions/PDR-0004-previsto-e-realizado.md).

## Regras funcionais

- Os indicadores devem derivar de dados reais.
- Mocks, números fixos no código ou dados demonstrativos não podem
  aparecer como informação operacional.
- Cada indicador respeita a autorização e o escopo de dados do usuário
  que o consulta.
- Cards financeiros só aparecem a usuários autorizados.
- Ocultar um card não substitui a filtragem correspondente no backend.
- Os indicadores financeiros seguem as regras de previsto e realizado
  de [PDR-0004](../decisions/PDR-0004-previsto-e-realizado.md).
- Um processo sem movimentação usa a data do seu último andamento como
  referência.
- O painel do gestor depende da existência de um registro confiável de
  atividade dos usuários.
- Atividade não deve ser inferida apenas por contagem simples de
  ações.
- Esta especificação não cria ranking ou avaliação automática de
  desempenho sem uma decisão específica de produto.

### Indicadores iniciais suportados pelas fontes

- Quantidade de usuários ativos, quando autorizado.
- Processos movimentados nas últimas 24 horas.
- Processos movimentados nos últimos 7 dias.
- Processos sem movimentação há mais de 1 mês.
- Processos sem movimentação há mais de 3 meses.
- Processos sem movimentação há mais de 6 meses.
- Prazos para hoje.
- Prazos para amanhã.
- Prazos em até 3 dias.
- Prazos em até 5 dias.
- Natureza dos processos.
- Localidade.
- Status.
- Fase.
- Posição ou patrocínio processual.
- Tempo médio de existência dos processos.
- Resultados processuais, quando os dados forem confiáveis.

Esta especificação não define a fórmula exata de cada indicador; ver
"Pontos em aberto".

## Fluxos principais

1. Consultar a visão geral do escritório.
2. Consultar a área de análise de dados.
3. Consultar o painel do gestor, quando autorizado.
4. Acessar um módulo a partir de um indicador ou atalho do Dashboard.

## Integrações e dependências

- Depende do módulo Processos para indicadores de movimentação,
  prazos, natureza, localidade, status, fase e patrocínio, conforme
  [processos.md](processos.md).
- Depende do módulo Financeiro para indicadores de previsto e
  realizado, conforme [financeiro.md](financeiro.md) e PDR-0004.
- Depende do módulo Agenda para prazos e compromissos próximos,
  conforme [agenda.md](agenda.md).
- Pode depender do módulo Equipes como referência de escopo para o
  painel do gestor, conforme [equipes.md](equipes.md).
- Depende de um registro confiável de atividade dos usuários, cuja
  origem ainda não está definida (ver "Pontos em aberto").

## Fora do escopo imediato

- Avaliação automática de produtividade.
- Ranking de pessoas.
- Predição por inteligência artificial.
- Indicadores sem base em dados estruturados.
- Analytics avançado, antes da consolidação da qualidade dos dados
  centrais.

## Pontos em aberto

- Quais eventos formam o registro de atividade dos usuários.
- Fórmula exata de cada indicador e de cada média apresentada.
- Se a atualização dos indicadores é em tempo real ou periódica.
- Possibilidade de personalização dos painéis pelo usuário.
- Regras de drill-down a partir de um indicador.
- Critérios jurídicos para classificar um resultado como procedente,
  parcialmente procedente ou improcedente.
- Uso de métricas de desempenho individual.

## Critérios de aceite funcionais

- Nenhum indicador do Dashboard exibe mock, número fixo ou dado
  demonstrativo como informação operacional.
- Um usuário sem autorização financeira não visualiza cards ou
  indicadores financeiros completos.
- Os indicadores financeiros respeitam a separação entre previsto e
  realizado.
- Um processo sem movimentação recente é identificado a partir da data
  do seu último andamento.
- O painel do gestor só é exibido a usuários autorizados e depende de
  um registro de atividade confiável.
- A filtragem por autorização e escopo de dados ocorre no backend, não
  apenas na interface.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0004 — Previsto e realizado](../decisions/PDR-0004-previsto-e-realizado.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)
- [financeiro.md](financeiro.md)
- [processos.md](processos.md)
- [agenda.md](agenda.md)
- [equipes.md](equipes.md)
