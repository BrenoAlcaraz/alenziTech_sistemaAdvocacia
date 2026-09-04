---
id: PDR-0017
title: Habilitações granulares de criar, editar e adicionar andamento em Processos
status: accepted
owner: product-and-engineering
decision_date: 2026-09-03
last_reviewed: 2026-09-03
supersedes: []
complements:
  - PDR-0010
source_files: []
---

# PDR-0017 — Habilitações granulares de criar, editar e adicionar andamento em Processos

## Contexto

[PDR-0010](PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
tratou o módulo `processos` como unidade binária de autorização nesta
versão e decidiu, como regra obrigatória, que nenhuma view de Processos
consumiria `processos_criar`, `processos_editar` ou
`processos_andamento_adicionar` como condição de autorização "sem
substituição por novo PDR". As três habilitações permaneceram
definidas no kernel (`ITENS_POR_MODULO`/`ITEM_CHOICES`), sem nenhum
ponto de aplicação.

[PDR-0014](PDR-0014-responsavel-integrantes-processos.md) já
estabeleceu o precedente de encerrar essa autorização binária de forma
pontual, uma habilitação por vez, ao aplicar
`processos_atribuir_responsavel` sem reabrir PDR-0010 por inteiro — e
registrou explicitamente que as demais habilitações continuavam
regidas por PDR-0010 "até nova decisão específica para cada uma".

Esta é essa decisão específica para as três habilitações restantes de
operação básica: `processos_criar`, `processos_editar` e
`processos_andamento_adicionar`.

## Problema

O módulo Processos lida com dado processual sensível. Hoje, qualquer
usuário com o módulo `processos` habilitado pode criar processo,
editar qualquer processo dentro do seu escopo de mutação e adicionar
andamento, independentemente de possuir as habilitações específicas já
modeladas no kernel para essas três ações — que existem sem nenhum
efeito prático. Isso diverge do padrão já aplicado em Clientes
(`clientes_criar`/`clientes_editar`) e em `processos_atribuir_responsavel`
(PDR-0014), e mantém uma lacuna de controle de acesso granular no
módulo mais sensível do produto sem necessidade de novo desenho —
o mecanismo já existe e já está validado em produção nesses outros
pontos.

## Decisão

As três habilitações passam a ser efetivamente aplicadas, uma por
operação, seguindo o padrão já validado em Clientes (WI-0001/WI-0002) e
em `processos_atribuir_responsavel` (PDR-0014):

| Habilitação | View aplicada | Efeito quando ausente |
|---|---|---|
| `processos_criar` | `processos:novo` | `PermissionDenied` (403) |
| `processos_editar` | `processos:editar` | `PermissionDenied` (403) |
| `processos_andamento_adicionar` | `processos:adicionar_movimentacao` | `PermissionDenied` (403) |

- cada view passa a checar, além da autorização de módulo já existente
  (`tem_permissao_modulo`), a habilitação específica
  (`tem_habilitacao`) antes de processar `GET` ou `POST`;
- o Administrador do escritório mantém acesso a todas as três ações
  independentemente destas habilitações, por bypass já existente no
  kernel (`habilitacao_efetiva`/`ctx.is_admin`) — nenhuma lógica nova é
  necessária para isso;
- um usuário sem a habilitação específica, mas com o módulo
  `processos` habilitado, é bloqueado tanto pela UI quanto por
  tentativa direta de `POST`.

### O que não muda

- `processos_usar_ia` e `processos_usar_laboratorio` continuam fora de
  escopo, conforme PDR-0010 e [PDR-0008](PDR-0008-ia-apos-nucleo-funcional.md)
  — não são tratadas por esta decisão;
- as demais operações mutáveis do módulo — arquivar, reabrir, adicionar/
  remover apenso, adicionar/editar parte — continuam regidas apenas
  pela autorização binária de módulo definida em PDR-0010; esta decisão
  não cria habilitação nova para nenhuma delas;
- escopo de leitura/mutação por responsável (`Somente os seus`/`Todos`),
  responsabilidade obrigatória, elegibilidade e transferência ao
  Administrador — já implementados via WI-0005 — permanecem
  inalterados; a habilitação específica é adicional ao escopo
  existente, não o substitui;
- equipe permanece fora da lógica de escopo, conforme PDR-0010.

## Relação com PDR-0010

Esta decisão complementa PDR-0010 e não o substitui. O único ponto
alterado é: `processos_criar`, `processos_editar` e
`processos_andamento_adicionar` deixam de ser habilitações sem efeito
prático e passam a condicionar, respectivamente, `processos:novo`,
`processos:editar` e `processos:adicionar_movimentacao`. Todas as
demais regras de PDR-0010 — incluindo a autorização binária de módulo
para as operações não listadas na tabela acima — permanecem vigentes
sem alteração.

## Regras obrigatórias

- `processos:novo`, `processos:editar` e `processos:adicionar_movimentacao`
  devem checar `tem_permissao_modulo(user, MODULO_PROCESSOS)` **e**
  `tem_habilitacao(user, MODULO_PROCESSOS, <item>)` antes de qualquer
  efeito de `GET` ou `POST`, na mesma ordem e forma já usada em
  `apps/clientes/views.py` (`novo`/`editar`).
- Falta de habilitação resulta em `PermissionDenied`, nunca em
  ocultação silenciosa de UI sem proteção equivalente no backend.
- Nenhuma outra view de Processos passa a checar habilitação granular
  como parte desta decisão.
- `processos_usar_ia` e `processos_usar_laboratorio` não são
  aplicadas por esta decisão nem por nenhum Work Item dela derivado.

## Consequências

- `docs/modules/processos.md` e a linha de Processos em
  [STATUS.md](../STATUS.md#módulos) passam a registrar
  `processos_criar`/`processos_editar`/`processos_andamento_adicionar`
  como aplicadas, mantendo `processos_usar_ia`/`processos_usar_laboratorio`
  como pendentes;
- se existir `docs/security/authorization-matrix.md`, passa a
  classificar as três habilitações como efetivamente aplicadas somente
  após o Work Item correspondente e evidência no HEAD;
- um Administrador de escritório que hoje delega acesso ao módulo
  Processos sem conceder estas três habilitações passa, a partir da
  implementação, a restringir de fato criação, edição e adição de
  andamento para esse usuário — mudança de comportamento esperada, não
  regressão.

## Alternativas ou regras substituídas

A regra de PDR-0010 que classificava a ausência de enforcement dessas
três habilitações como "decisão deliberada de produto... enquanto este
PDR estiver vigente" deixa de valer especificamente para
`processos_criar`, `processos_editar` e `processos_andamento_adicionar`
a partir desta decisão. PDR-0010 permanece vigente para tudo o mais,
incluindo `processos_usar_ia`/`processos_usar_laboratorio` e as demais
operações mutáveis não listadas na tabela da seção "Decisão".

## Fora do escopo desta decisão

- `processos_usar_ia` e `processos_usar_laboratorio`;
- habilitação granular para arquivar, reabrir, apensos ou partes de
  processo — nenhuma dessas ações ganha habilitação nova;
- qualquer alteração ao escopo de leitura/mutação por responsável, à
  responsabilidade obrigatória, ou à habilitação
  `processos_atribuir_responsavel` (PDR-0014);
- equipe como base de escopo;
- qualquer alteração ao módulo Clientes.

## Critérios de aceite funcionais

- um usuário com módulo `processos` habilitado mas sem
  `processos_criar` não consegue acessar `processos:novo` nem criar
  processo por `POST` direto;
- um usuário com módulo `processos` habilitado mas sem
  `processos_editar` não consegue acessar `processos:editar` nem
  submeter `POST` para essa rota, mesmo para um processo dentro do seu
  próprio escopo de mutação;
- um usuário com módulo `processos` habilitado mas sem
  `processos_andamento_adicionar` não consegue adicionar andamento por
  `POST` em `processos:adicionar_movimentacao`;
- o Administrador do escritório continua criando, editando e
  adicionando andamento normalmente, sem depender de nenhuma das três
  habilitações;
- arquivar, reabrir, apensos e partes continuam funcionando exatamente
  como hoje, sem exigir nenhuma habilitação nova;
- `processos_usar_ia` e `processos_usar_laboratorio` continuam sem
  nenhum ponto de aplicação após esta decisão.

## Fontes

- decisão direta do Product Owner registrada em 2026-09-03, dando
  sequência ao precedente aberto por
  [PDR-0014](PDR-0014-responsavel-integrantes-processos.md) para
  encerrar, habilitação por habilitação, a autorização binária de
  módulo definida em
  [PDR-0010](PDR-0010-autorizacao-escopo-responsabilidade-processos.md).
