---
id: PDR-0018
title: Banco compartilhado de Modelos de Peça — CRUD por autoria e habilitações de edição/exclusão alheia
status: accepted
owner: product-and-engineering
decision_date: 2026-09-04
last_reviewed: 2026-09-04
supersedes: []
complements: []
source_files: []
---

# PDR-0018 — Banco compartilhado de Modelos de Peça — CRUD por autoria e habilitações de edição/exclusão alheia

## Contexto

O módulo Modelos de Peça (`apps/modelos`) foi concebido, desde a origem,
como um banco compartilhado de peças jurídicas do escritório: qualquer
usuário com o módulo `modelos` habilitado lista e abre o conteúdo de
qualquer modelo, de qualquer autor — não existe, e nunca existiu, filtro
de visibilidade por usuário. O kernel de autorização, porém, define
`NIVEIS_POR_MODULO[MODULO_MODELOS] = [somente_seus, todos]`, sugerindo
que esse nível controlaria visibilidade, quando nenhuma view o consulta
de fato.

Hoje não existe nenhum controle de autoria sobre edição: qualquer
usuário com o módulo `modelos` habilitado edita o modelo de peça de
qualquer outro usuário, sem checagem de habilitação alguma
(`HAB_MODELOS_EDITAR` não existe no kernel). Não existe função de
exclusão de `ModeloPeca`.

## Problema

Sem controle de autoria, qualquer usuário com acesso ao módulo altera
peças que não criou — incluindo peças estratégicas de outros
advogados/sócios — sem nenhum registro de quem autorizou a alteração.
E não há mecanismo para o escritório limpar peças obsoletas ou de baixa
qualidade criadas por um usuário específico, já que exclusão não existe.

## Decisão

- Visibilidade (listar/abrir) permanece **sempre total** para qualquer
  usuário com o módulo `modelos` habilitado — reafirmação do
  comportamento já existente, não uma mudança de comportamento.
- Passa a existir uma regra fixa de autoria: **editar** e **excluir**
  um `ModeloPeca` exige ser o autor (`modelo.criado_por == usuário`)
  OU possuir a habilitação granular correspondente:
  - `modelos_editar_alheio` — edita modelo de peça de outro usuário;
  - `modelos_excluir_alheio` — exclui modelo de peça de outro usuário.
- As duas habilitações são **independentes** entre si (não uma única
  habilitação combinada) — um papel pode ter uma sem a outra, porque
  editar peça alheia (corrigir algo) é um risco menor que excluir peça
  alheia (perda definitiva de item do banco compartilhado).
- O direito do autor sobre o que criou é **incondicional**: não depende
  de o usuário ainda possuir `modelos_criar` ativa. Perder
  `modelos_criar` impede criar peça nova; não afeta o que já foi criado.
- Administrador do escritório mantém bypass total (edita/exclui
  qualquer peça), pelo mecanismo de bypass já existente no kernel
  (`habilitacao_efetiva`) — nenhuma lógica nova é necessária para isso.
- Exclusão é definitiva (hard delete). Ao excluir peça alheia, a UI
  exige confirmação explícita mencionando o autor original.
- Em ambos os casos (editar ou excluir peça alheia), o autor original
  recebe uma `Notificacao`, seguindo o padrão já usado para reabertura
  de lançamento financeiro (PDR-0006/PDR-0015) e conclusão de tarefa
  (PDR-0016). Editar/excluir a própria peça não gera notificação.

### O que fica deliberadamente inalterado

- `NIVEIS_POR_MODULO[MODULO_MODELOS]` continua `[somente_seus, todos]`
  no kernel, mesmo esse nível não tendo efeito prático sobre Modelos.
  Mudar isso tocaria uma `CheckConstraint` de banco (`apps/accounts/models.py`)
  e exigiria migration própria — fora do escopo desta decisão. Fica
  registrado como inconsistência conhecida em `docs/STATUS.md`.
- `modelos_editar_estilo` e a aba "Meu estilo" continuam fora de
  escopo (`docs/STATUS.md` já registra isso).
- Nenhuma forma de versionamento, rascunho ou cópia privada de modelo é
  introduzida — visibilidade total do banco compartilhado é mantida
  sem exceção.

## Regras obrigatórias

- `modelos:editar` (GET/POST) e a nova rota `modelos:excluir` (POST)
  checam, nesta ordem: `tem_permissao_modulo` → autoria OU
  `tem_habilitacao` do item correspondente.
- Falta de autoria e de habilitação resulta em `PermissionDenied`,
  nunca em ocultação silenciosa de UI sem proteção equivalente no
  backend.
- A UI oculta os botões de editar/excluir quando nem autoria nem
  habilitação existem.

## Consequências

- `docs/STATUS.md` passa a registrar Modelos com autorização de
  edição/exclusão por autoria + habilitações granulares aplicadas.
- Um Administrador que hoje delega o módulo `modelos` sem conceder as
  duas novas habilitações passa, a partir da implementação, a
  restringir de fato edição/exclusão de peça alheia para esse usuário
  — mudança de comportamento esperada, não regressão.

## Fora do escopo desta decisão

- Alterar `NIVEIS_POR_MODULO`/constraint de banco do módulo Modelos.
- Versionamento, rascunho ou cópia privada de peça.
- Qualquer alteração à aba "Meu estilo"/`modelos_editar_estilo`.
- Lixeira/soft delete.

## Critérios de aceite funcionais

- Autor edita/exclui a própria peça mesmo sem `modelos_criar` ativa e
  sem nenhuma das duas habilitações alheias.
- Usuário sem autoria e sem `modelos_editar_alheio` não edita peça de
  outro usuário (GET e POST).
- Usuário sem autoria e sem `modelos_excluir_alheio` não exclui peça
  de outro usuário (POST).
- Administrador edita/exclui qualquer peça sem depender de nenhuma
  habilitação.
- Editar ou excluir peça alheia gera `Notificacao` para o autor
  original; editar/excluir a própria peça não gera.
- Listar/abrir modelo de peça continua sempre total, sem filtro por
  usuário.

## Fontes

- Sessão de grilling com o Product Owner em 2026-09-04, a partir da
  constatação de que a feature originalmente proposta (escopo de
  leitura `dados_proprios`/`dados_todos` em Modelos) partia de premissa
  errada sobre o propósito do módulo — banco compartilhado do
  escritório, não dado privado por usuário.
