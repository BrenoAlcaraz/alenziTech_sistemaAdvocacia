---
id: PDR-0025
title: Exclusão definitiva de Cliente
status: accepted
owner: product-and-engineering
decision_date: 2026-09-15
last_reviewed: 2026-09-15
supersedes: []
complements:
  - PDR-0024
source_files: []
---

# PDR-0025 — Exclusão definitiva de Cliente

## Contexto

`docs/PRODUCT.md`, seção Clientes, registrava "exclusão física vs.
lógica" como fora de escopo, sem decisão aprovada — só existia
"Desativar" (`ativo=False`, cliente some das listas mas continua no
banco). Na reunião de 13/09, o sócio pediu uma ação de exclusão
definitiva, distinta de desativar, mesma necessidade já resolvida para
Processos em PDR-0024.

## Decisão

Nova ação **Excluir cliente**, distinta de Desativar, condicionada à
nova habilitação granular `clientes_excluir` (módulo `clientes`) mais o
mesmo escopo de mutação já usado por Desativar/Reativar (Administrador
do escritório ou responsável do cliente).

Mesma divisão já adotada em PDR-0024 para Processo: o Cliente é
removido; registros de **outros módulos** vinculados a ele —
lançamentos financeiros (`LancamentoFinanceiro`, `CustaJudicial`,
`Honorario`, `SolicitacaoFinanceira`), tarefas (`Tarefa`) e compromissos
de agenda (`Compromisso`) — **não são apagados**. A referência ao
cliente é desfeita (`on_delete=SET_NULL`, já era o padrão em todos esses
modelos antes desta decisão), e a tela correspondente continua
funcionando sem exibir erro.

Diferente de Processo, Cliente não tem dado "intrínseco" próprio
cascateável (Documentos/Partes/Andamentos são do Processo, não do
Cliente) — a exclusão de Cliente é, na prática, só a remoção do próprio
registro e do vínculo M2M com `Processo.clientes`.

## Regras obrigatórias

- Excluir exige `clientes_excluir` **e** estar no escopo de mutação
  (Administrador ou responsável) — mesma dupla checagem já usada pelas
  demais habilitações granulares de Clientes.
- Exclusão é definitiva — sem lixeira, sem desfazer.
- Disponível tanto a partir da lista de clientes ativos (detalhe do
  cliente) quanto da lista de inativos — um cliente não precisa estar
  desativado antes de ser excluído.

## Consequências

- `docs/PRODUCT.md`, seção Clientes, deixa de listar "exclusão física
  vs. lógica" como fora de escopo sem decisão — passa a documentar a
  regra decidida aqui.
- `docs/STATUS.md`, linha Clientes, passa a registrar essa
  funcionalidade como implementada.
- Nova habilitação `clientes_excluir` no catálogo de
  `apps/accounts/permissoes_constants.py` (e no `CheckConstraint` de
  `HabilitacaoPapel`/`HabilitacaoUsuario`, que replica essa lista
  separadamente no schema do banco).

## Fora do escopo desta decisão

- Dedup automática por CPF/CNPJ entre clientes — continua sem decisão
  aprovada.
- Cardinalidade de múltiplos endereços/contatos por cliente — continua
  sem decisão aprovada.
- Qualquer lixeira, soft-delete ou período de retenção antes da
  exclusão definitiva.

## Critérios de aceite funcionais

- Usuário sem `clientes_excluir` não vê a ação nem consegue acioná-la
  via requisição direta.
- Excluir um cliente o remove da listagem (ativos e inativos).
- Um lançamento financeiro, tarefa ou compromisso que referenciava o
  cliente excluído continua existindo e acessível, sem erro.

## Fontes

- Conversa desta sessão (reunião de 13/09, repassada pelo Product
  Owner); spec `specs/clientes-ajustes-cadastro-vinculos.md` (apagada
  após a promoção deste PDR, conforme
  [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
