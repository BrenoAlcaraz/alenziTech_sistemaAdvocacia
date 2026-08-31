---
id: PDR-0010
title: Autorização, escopo e responsabilidade de Processos
status: accepted
owner: product-and-engineering
decision_date: 2026-08-19
last_reviewed: 2026-08-19
supersedes: []
source_files: []
---

# PDR-0010 — Autorização, escopo e responsabilidade de Processos

## Contexto

[STATUS.md](../STATUS.md)
e
[ARCHITECTURE.md](../ARCHITECTURE.md)
descrevem, como alvo canônico anterior a esta decisão, autorização de
módulo combinada a habilitações granulares (`processos_criar`,
`processos_editar`, `processos_andamento_adicionar`) para as operações
correspondentes de Processos, além de escopo de dados por responsável
ou equipe. Nenhuma dessas camadas está aplicada nas views de
`apps/processos` no HEAD auditado — as nove rotas existentes
(`lista`, `detalhe`, `novo`, `editar`, `arquivados`, `arquivar`,
`reabrir`, `adicionar_movimentacao`, `adicionar_parte`) usam
exclusivamente `@login_required`, conforme
[STATUS.md#módulos](../STATUS.md#módulos).

## Problema

Sem uma decisão explícita, a implementação da autorização de Processos
ficaria ambígua entre duas leituras válidas da documentação vigente:
(a) aplicar imediatamente, na mesma unidade de trabalho, as três
habilitações já existentes no kernel para as operações
correspondentes, ou (b) tratar o módulo como uma unidade binária nesta
etapa. Adicionalmente, o modelo de dados atual
(`Processo.responsavel` opcional, sem regra de reatribuição) não
sustenta escopo por responsável sem antes decidir responsabilidade
obrigatória, elegibilidade e transferência — decisão que exige
migração de dado e mudança de comportamento mais ampla do que a
consolidação de autorização de módulo comporta com segurança em um
único item de trabalho.

## Decisão

### Autorização desta versão

Para a versão atual de Processos, o módulo `processos` é tratado como
uma unidade binária de autorização:

- módulo `processos` habilitado ⇒ o usuário pode utilizar todas as
  operações atualmente existentes do módulo;
- módulo `processos` desabilitado ⇒ o usuário não pode acessar nem
  executar nenhuma operação do módulo.

As habilitações já existentes no kernel (`processos_criar`,
`processos_editar`, `processos_andamento_adicionar`) não restringem,
nesta versão, nenhuma operação de Processos. Permanecem definidas em
`ITENS_POR_MODULO`/`ITEM_CHOICES`
(`apps/accounts/permissoes_constants.py`) para reutilização futura, mas
não são consumidas pelas views atuais de Processos.

IA e Laboratório (`processos_usar_ia`, `processos_usar_laboratorio`)
continuam fora de escopo desta decisão e de qualquer Work Item dela
derivado.

### Escopo de dados por responsável — direção aprovada, implementação futura

Fica aprovada, para implementação em Work Item futuro, a seguinte
regra de escopo de leitura sobre `Processo`:

- `Somente os seus`: o usuário alcança processos onde
  `Processo.responsavel == request.user`;
- `Todos`: amplia leitura a qualquer processo do tenant; não amplia
  mutação;
- um usuário não administrador com nível `Todos` pode visualizar
  processos de outros responsáveis, mas só pode modificar processos
  pelos quais é responsável;
- o Administrador do escritório pode visualizar e modificar qualquer
  processo do tenant.

### Responsabilidade obrigatória — direção aprovada, implementação futura

Fica aprovada, para implementação em Work Item futuro, a seguinte
regra de responsabilidade sobre `Processo`:

- um processo nunca pode ficar sem responsável;
- na criação por usuário não administrador, o responsável é sempre o
  próprio criador;
- o Administrador do escritório pode escolher ou redefinir o
  responsável;
- responsável elegível é um usuário ativo com acesso efetivo ao módulo
  Processos;
- se um usuário perder acesso efetivo ao módulo Processos, ou for
  inativado, os processos sob sua responsabilidade passam ao
  Administrador do escritório;
- essa transferência é permanente: recuperar acesso posteriormente não
  devolve automaticamente os processos transferidos;
- equipe (`Processo.equipe`) não interfere nessa regra;
- `Processo.responsavel` deve seguir, na implementação futura, um
  padrão de obrigatoriedade e proteção equivalente ao já adotado em
  `Cliente.responsavel` (`null=False`, `on_delete=PROTECT`, migration
  de dado reprodutível), conforme o padrão descrito em
  [ARCHITECTURE.md](../ARCHITECTURE.md#autorização--padrão-a-reutilizar).

### Clientes dentro de Processos — direção aprovada, implementação futura

O módulo Clientes não funciona como barreira de confidencialidade para
a seleção de clientes em Processos: um usuário autorizado a
criar/editar Processos pode utilizar clientes ativos do escritório
mesmo sem acesso ao módulo Clientes, ou com `Clientes = Somente os
seus`. Esta regra será consolidada no Work Item de escopo/
responsabilidade de Processos quando necessário; não se aplica
retroativamente a nenhuma regra de Clientes.

### Equipe — fora de escopo

Equipe permanece fora da lógica de escopo de Processos nesta etapa e
na etapa aprovada por este PDR para o próximo Work Item.
`Processo.equipe` e `equipe_padrao_para_usuario()` continuam existindo
e operando como hoje (pré-preenchimento na criação, quando o usuário
pertence a exatamente uma equipe ativa), mas: equipe não concede
acesso; equipe não filtra Processos; "Da equipe" não é implementado;
escopo por equipe não é implementado.

## Regras obrigatórias

- Nenhuma view atual de Processos consome `processos_criar`,
  `processos_editar` ou `processos_andamento_adicionar` como condição
  de autorização enquanto esta decisão estiver vigente, sem
  substituição por novo PDR.
- Toda operação atualmente existente de Processos deve exigir, no
  mínimo, autorização do módulo `processos`
  (`tem_permissao_modulo()`).
- Escopo por `Processo.responsavel`, responsabilidade obrigatória,
  reatribuição ao Administrador, e a regra de seleção de clientes
  independente do módulo Clientes, permanecem direção aprovada, não
  implementação exigida, até que um Work Item específico os
  implemente.
- Qualquer implementação futura de escopo ou responsabilidade de
  Processos deve seguir o padrão de segurança já validado em Clientes
  (WI-0001, WI-0002): negação no backend, objeto fora do escopo
  aplicável retorna 404, mutação revalidada no servidor, migration de
  dado restrita ao necessário para tornar o campo obrigatório.

## Consequências

- [modules/processos.md](../modules/processos.md) e
  [ARCHITECTURE.md](../ARCHITECTURE.md) passam a refletir
  autorização binária por módulo como o comportamento correto desta
  versão, não como lacuna a corrigir imediatamente.
- Um usuário com o módulo Processos habilitado, mas sem nenhuma das
  três habilitações específicas, continua podendo criar, editar e
  adicionar movimentação nesta versão — comportamento esperado, não
  regressão.
- Para Processos, a autorização binária por módulo definida nesta
  decisão satisfaz a Fase A do roadmap quando aplicada no backend às
  operações atuais, coberta por testes e pelos gates do Work Item. As
  habilitações granulares preservadas no kernel são possibilidade de
  evolução futura e não constituem dívida bloqueante da Fase A.
- Concluída e fechada essa entrega de Fase A, Processos pode avançar
  verticalmente para a Fase B — escopo e responsabilidade — no
  WI-0005, sem necessidade de novo PDR para implementar as direções já
  aprovadas nesta decisão.
- Fica registrada uma dívida de produto explícita: processo sem
  responsável obrigatório, sem regra de reatribuição, e sem escopo de
  leitura aplicado, até que o Work Item futuro mencionado neste PDR
  seja executado.

## Alternativas ou regras substituídas

A leitura anterior de
[ARCHITECTURE.md](../ARCHITECTURE.md), que classificava a ausência de checagem de
`processos_criar`/`processos_editar`/`processos_andamento_adicionar`
como "lacuna constatada" a corrigir na Fase A, é substituída, para esta
versão, por "evolução planejada": a ausência de enforcement dessas
habilitações passa a ser tratada como decisão deliberada de produto,
não pendência técnica nem bloqueio à conclusão da Fase A, enquanto este
PDR estiver vigente.

## Fora do escopo desta decisão

- Implementação de código de escopo, responsabilidade obrigatória,
  migration ou reatribuição automática — pertence a Work Item futuro.
- Qualquer alteração ao módulo Clientes.
- Modelagem de `ParteProcesso`, atualmente regida por
  [PDR-0013](PDR-0013-partes-processo-modelo-simplificado.md).
- IA e Laboratório, conforme
  [PDR-0008](PDR-0008-ia-apos-nucleo-funcional.md).
- Equipe como base de escopo.

## Critérios de aceite funcionais

- Um usuário com módulo Processos habilitado acessa e executa todas as
  operações atualmente existentes do módulo, independentemente de
  possuir `processos_criar`/`processos_editar`/
  `processos_andamento_adicionar`.
- Um usuário sem módulo Processos habilitado não acessa nem executa
  nenhuma operação do módulo, incluindo tentativa direta por URL ou
  `POST` manual.
- As três habilitações existentes permanecem presentes no kernel
  (`ITEM_CHOICES`/`ITENS_POR_MODULO`), sem remoção.
- O WI-0005 pode implementar diretamente, sem novo PDR: escopo por
  `Processo.responsavel`; níveis `Somente os seus`/`Todos`; leitura
  ampliada por `Todos` sem ampliação de mutação; mutação restrita ao
  responsável para não administrador; acesso integral do Administrador
  do escritório; responsabilidade obrigatória; elegibilidade do
  responsável; transferência permanente ao Administrador quando o
  responsável perder acesso efetivo ao módulo ou for inativado; e
  seleção de clientes ativos do escritório independentemente do acesso
  do usuário ao módulo Clientes.
- Revisão ou complemento deste PDR só é necessária se um Work Item
  introduzir equipe como escopo, implementar `Da equipe`, alterar as
  regras aprovadas acima ou ampliar a funcionalidade além desta decisão.

## Fontes

Esta decisão não deriva de material histórico
(`docs/history/source-material/`) — origina-se de decisão direta do
Product Owner, registrada na condução desta execução (2026-08-19),
consolidando e resolvendo uma ambiguidade anterior sobre o alvo
canônico de autorização do módulo Processos, hoje descrito em
[STATUS.md](../STATUS.md) e [ARCHITECTURE.md](../ARCHITECTURE.md).
