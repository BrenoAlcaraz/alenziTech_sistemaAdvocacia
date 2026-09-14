---
id: PDR-0024
title: Exclusão definitiva de Processo
status: accepted
owner: product-and-engineering
decision_date: 2026-09-14
last_reviewed: 2026-09-14
supersedes: []
complements:
  - PDR-0012
  - PDR-0014
source_files: []
---

# PDR-0024 — Exclusão definitiva de Processo

## Contexto

`docs/modules/processos.md` registrava "exclusão física vs. lógica"
como fora de escopo, sem decisão aprovada — só existia "Arquivar"
(muda `status` para `arquivado`, processo continua em análise de
dados). Na reunião de 13/09, o sócio pediu uma ação de exclusão
definitiva, distinta de arquivar, para remover um processo cadastrado
por engano ou que não deve mais existir no sistema.

## Problema

Sem exclusão definitiva, um processo indevido (duplicado, cadastrado
por engano, teste) permanece para sempre no banco, mesmo arquivado —
arquivar não é a operação certa para esse caso, é para processos
encerrados que devem continuar consultáveis.

## Decisão

Nova ação **Excluir processo**, distinta de Arquivar, condicionada à
nova habilitação granular `processos_excluir` (módulo `processos`) mais
o mesmo escopo de mutação já usado por Arquivar (Administrador do
escritório ou responsável do processo).

### O que é removido

O Processo e tudo que é **intrínseco** a ele — dados que só existem no
contexto desse processo específico e não fazem sentido fora dele:

- Documentos (`Documento`)
- Partes (`ParteProcesso`)
- Andamentos (`MovimentacaoProcessual`)
- Vínculos de apenso (`VinculoProcessoApenso`) — remove só o vínculo,
  nunca o outro processo do par (mesma regra de independência do
  PDR-0012)
- Intimações (`Intimacao`)

Esses cinco já cascateiam automaticamente pelo `on_delete=CASCADE`
existente no modelo — nenhuma alteração de constraint foi necessária
para este PDR.

### O que é preservado

Registros de **outros módulos** vinculados ao processo — lançamentos
financeiros (`LancamentoFinanceiro`, `CustaJudicial`, `Honorario`,
`SolicitacaoFinanceira`), tarefas (`Tarefa`) e compromissos de agenda
(`Compromisso`) — **não são apagados**. A referência ao processo é
desfeita (`on_delete=SET_NULL`, já é o padrão hoje em todos esses
modelos), e a tela correspondente deve tratar "processo excluído" em
vez de exibir um link quebrado ou erro.

### Por quê essa divisão

Documentos/Partes/Andamentos/Apensos/Intimações só têm sentido como
parte do processo — não são "histórico" de outro módulo. Já um
lançamento financeiro, uma tarefa ou um compromisso de agenda são
registros do módulo dono (Financeiro/Tarefas/Agenda), com vida própria
e valor de histórico independente do processo que os originou —
apagá-los junto destruiria um registro que pertence a outro domínio.

## Regras obrigatórias

- Excluir exige `processos_excluir` **e** estar no escopo de mutação
  (Administrador ou responsável) — mesma dupla checagem já usada por
  `processos_documento_adicionar`/`processos_documento_excluir`.
- Exclusão é definitiva — sem lixeira, sem desfazer, sem período de
  retenção.
- Toda tela que hoje exibe o processo vinculado a um lançamento
  financeiro, tarefa ou compromisso deve continuar funcionando após a
  exclusão do processo, mostrando "processo excluído" (ou equivalente)
  em vez de falhar.

## Consequências

- `docs/modules/processos.md` passa a documentar a exclusão definitiva
  e a resolver o ponto que estava marcado como "fora de escopo, sem
  decisão aprovada".
- `docs/STATUS.md`, linha Processos, passa a registrar essa
  funcionalidade como implementada.
- Nova habilitação `processos_excluir` no catálogo de
  `docs/decisions` / `apps/accounts/permissoes_constants.py`.

## Fora do escopo desta decisão

- Exclusão definitiva de Cliente — mesma pergunta em aberto, decisão
  separada (spec `specs/clientes-ajustes-cadastro-vinculos.md`).
- Qualquer lixeira, soft-delete ou período de retenção antes da
  exclusão definitiva — a ação é imediata e irreversível nesta versão.
- Exportação/backup automático antes de excluir — não pedido nesta
  reunião.

## Critérios de aceite funcionais

- Usuário sem `processos_excluir` não vê a ação nem consegue acioná-la
  via requisição direta.
- Excluir um processo remove Documentos/Partes/Andamentos/Apensos/
  Intimações associados.
- Um lançamento financeiro, tarefa ou compromisso que referenciava o
  processo excluído continua existindo e acessível, sem erro.

## Fontes

- Conversa desta sessão (reunião de 13/09, repassada pelo Product
  Owner); spec `specs/processos-ajustes-formulario-detalhe.md` (apagada
  após a promoção deste PDR, conforme
  [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
