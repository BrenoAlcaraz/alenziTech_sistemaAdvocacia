---
id: PDR-0014
title: Responsável principal e integrantes habilitados de Processos
status: accepted
owner: product-and-engineering
decision_date: 2026-08-31
last_reviewed: 2026-08-31
supersedes: []
complements:
  - PDR-0010
source_files: []
---

# PDR-0014 — Responsável principal e integrantes habilitados de Processos

## Contexto

[PDR-0010](PDR-0010-autorizacao-escopo-responsabilidade-processos.md) aprovou,
para implementação futura, responsabilidade obrigatória sobre `Processo`
com reatribuição exclusiva do Administrador do escritório. O WI-0005
implementou essa direção: `Processo.responsavel` obrigatório, protegido, e
reatribuível apenas pelo Administrador.

A especificação validada a partir dos protótipos funcionais
(`docs/prototipos/processo-prototipo.html`) descreve dois conceitos que
PDR-0010 não previu: uma habilitação dedicada para atribuir/reatribuir o
responsável, delegável a quem não é Administrador; e uma segunda relação,
"integrantes habilitados" (`usuario_processos`, N por processo), distinta
tanto do responsável quanto da equipe.

O Product Owner decidiu incorporar os dois conceitos e tornar a
reatribuição de responsável delegável por habilitação.

## Decisão

### Habilitação "Atribuir responsabilidade de processos"

Cria-se uma nova habilitação granular no módulo `processos`:
`processos_atribuir_responsavel` — "Atribuir responsabilidade de
processos".

- quem possui essa habilitação pode definir ou redefinir o responsável
  principal de qualquer processo dentro do seu escopo de mutação, a partir
  de qualquer conta do escritório com acesso efetivo ao módulo Processos;
- o Administrador do escritório continua podendo fazer o mesmo,
  independentemente desta habilitação, por sua autoridade administrativa
  geral;
- esta é a primeira habilitação granular de Processos efetivamente
  aplicada nas views, encerrando, apenas para esta ação, a autorização
  binária de módulo definida em PDR-0010. As demais habilitações do
  módulo (`processos_criar`, `processos_editar`,
  `processos_andamento_adicionar`, `processos_usar_ia`,
  `processos_usar_laboratorio`) continuam não aplicadas, conforme
  PDR-0010, até nova decisão específica para cada uma.

### Responsável principal

`Processo.responsavel` passa a ser referido como responsável principal.
Continua único por processo, obrigatório, e é a referência do processo
para:

- distribuição automática de prazos na Agenda;
- indicadores e Análise de dados por usuário;
- escopo de leitura/mutação por responsável, conforme já aprovado em
  PDR-0010.

As demais regras de PDR-0010 sobre responsabilidade obrigatória —
elegibilidade do responsável, transferência permanente ao Administrador
quando o responsável perder acesso efetivo ao módulo ou for inativado, e o
padrão de proteção equivalente a `Cliente.responsavel` — permanecem
integralmente vigentes e não são alteradas por esta decisão.

### Integrantes habilitados

Cria-se uma relação N:N entre `Processo` e usuário — integrante habilitado
do processo — distinta do responsável principal (único) e da equipe
(`Processo.equipe`, que não concede acesso, conforme PDR-0010):

- um processo pode ter N integrantes habilitados, além do responsável
  principal;
- integrante habilitado participa do processo, mas não se torna
  responsável principal automaticamente por essa condição;
- integrante habilitado não recebe automaticamente os prazos do processo
  na Agenda — apenas o responsável principal recebe;
- gerenciar quem é integrante habilitado de um processo é visível e
  operável apenas por quem possui a habilitação já existente no kernel
  `gerir_habilitar_usuario_processos` ("Habilitar usuário em processos").
  Esta decisão não cria habilitação nova para essa ação.

## Relação com PDR-0010

Esta decisão complementa PDR-0010 e não o substitui. Permanecem vigentes,
sem alteração: autorização binária de módulo para as demais operações,
escopo de leitura "somente os seus"/"todos" por responsável, elegibilidade
do responsável, transferência automática ao Administrador, independência
do módulo Clientes na seleção de clientes em Processos, e a posição de
equipe como fora da lógica de escopo.

O único ponto de PDR-0010 alterado é: "reatribuir o responsável principal"
deixa de ser exclusivo do Administrador do escritório e passa a também
estar disponível a quem possui `processos_atribuir_responsavel`.

## Consequências

- nova habilitação `processos_atribuir_responsavel` entra em
  `ITENS_POR_MODULO`/`ITEM_CHOICES` do módulo `processos`;
- nova relação N:N `usuario_processos` (integrante habilitado × processo),
  distinta de responsável e de equipe;
- a view/rota de reatribuição de responsável (WI-0005) precisa passar a
  aceitar tanto o Administrador quanto usuários com
  `processos_atribuir_responsavel`, em vez de checar exclusivamente
  função administrativa;
- `docs/security/authorization-matrix.md` registra
  `processos_atribuir_responsavel` como alvo aprovado e ainda não
  implementado; só poderá classificá-la como efetivamente aplicada depois
  do respectivo Work Item e da evidência no HEAD;
- integrantes habilitados não são propagados entre processos apensos. A
  relação de apensos continua sem herança de propriedades, conforme
  [PDR-0012](PDR-0012-relacao-simetrica-processos-apensos.md); a cascata
  demonstrada no protótipo não foi incorporada por esta decisão.

## Fora do escopo desta decisão

- as demais habilitações granulares de Processos (`processos_criar`,
  `processos_editar`, `processos_andamento_adicionar`), que permanecem
  regidas por PDR-0010;
- equipe como base de escopo;
- captura automática de andamentos e qualquer integração com tribunais;
- IA e Laboratório.

## Critérios de aceite funcionais

- um usuário sem `processos_atribuir_responsavel` e sem função de
  Administrador não consegue reatribuir o responsável principal de nenhum
  processo, incluindo tentativa direta por `POST`;
- um usuário com `processos_atribuir_responsavel` consegue reatribuir o
  responsável principal de um processo dentro do seu escopo de mutação;
- um processo pode ter N integrantes habilitados além do responsável
  principal;
- adicionar ou remover um integrante habilitado não altera o responsável
  principal do processo;
- adicionar ou remover um integrante habilitado não altera integrantes de
  processos apensos;
- prazos do processo são distribuídos automaticamente apenas ao
  responsável principal, nunca aos demais integrantes habilitados;
- gerenciar integrantes habilitados exige `gerir_habilitar_usuario_processos`.

## Fontes

- decisão direta do Product Owner registrada em 2026-08-31, durante a
  revisão estrutural de documentação a partir dos protótipos funcionais;
- [docs/prototipos/processo-prototipo.html](../../prototipos/processo-prototipo.html)
  (referência visual; a propagação entre apensos nele demonstrada não foi
  adotada, por conflito com PDR-0012);
- [PDR-0010 — Autorização, escopo e responsabilidade de Processos](PDR-0010-autorizacao-escopo-responsabilidade-processos.md).
