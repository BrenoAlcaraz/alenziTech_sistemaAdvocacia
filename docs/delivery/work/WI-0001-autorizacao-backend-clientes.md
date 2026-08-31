---
title: WI-0001 — Autorização backend de Clientes
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# WI-0001 — Autorização backend de Clientes

## Estado

done

## Fase do roadmap

Fase: Fase A — Consolidar autorização nas operações

## Objetivo

Aplicar enforcement de autorização backend ao módulo Clientes usando o
kernel já existente (`apps/accounts/permissoes.py`), sem escopo de
dados: toda operação passa a exigir `tem_permissao_modulo(user,
"clientes")`; `novo`/`editar` exigem também `clientes_criar`/
`clientes_editar` via `tem_habilitacao()`.

## Escopo entregue

As sete rotas de `apps/clientes/views.py` (`lista`, `detalhe`, `novo`,
`editar`, `desativar`, `inativos`, `reativar`) negam acesso (`raise
PermissionDenied`, backend, antes de qualquer leitura/mutação) a um
usuário sem autorização de módulo; `novo`/`editar` negam adicionalmente
sem a habilitação correspondente. Nenhuma resposta HTTP customizada foi
criada (sem `handler403`/`403.html` no HEAD auditado) — usa-se a página
padrão do Django. `desativar`/`inativos`/`reativar` só exigem
autorização de módulo, pois a matriz canônica não as vincula a nenhuma
habilitação existente.

## Fora do escopo

Escopo de dados por `Cliente.responsavel`, autorização sobre objeto
(IDOR intra-tenant) e `nivel` (`somente_seus`/`todos`) — entregues
depois por [WI-0002](WI-0002-escopo-responsabilidade-clientes.md).
Templates/UI não foram alterados (botões de ação seguem incondicionais
nesta entrega).

## Estado atual (pós-WI-0002)

O estado de autorização e escopo de Clientes, incluindo o que este item
deixou pendente, está consolidado em
[current-state/clientes.md](../current-state/clientes.md) e
[authorization-matrix.md#clientes](../../security/authorization-matrix.md#clientes)
— não duplicado aqui.

## Critérios de aceite

- [x] as sete rotas exigem autorização de módulo; `novo`/`editar`
  exigem também a habilitação correspondente — negação antes de
  qualquer leitura/mutação, sem alterar nenhum registro;
- [x] usuário autorizado continua alcançando os sete fluxos
  normalmente;
- [x] nenhuma habilitação nova foi criada; `nivel` não foi lido nem
  usado como autorização de ação; nenhuma migration foi criada;
- [x] nenhum arquivo fora do escopo permitido foi modificado.

Evidência: `apps/clientes/tests/test_autorizacao.py` (26 testes —
`TestClientesAutorizacaoModuloConcedido`/`...ModuloNegado`/
`...HabilitacaoCriarAusente`/`...HabilitacaoEditarAusente`), `OK`.
`apps.accounts` (86 testes) sem regressão. `python manage.py check` e
`makemigrations --check --dry-run` sem achados; `git diff --check`
aprovado.

## Achados fora do escopo ainda relevantes

- **Botões de ação sem condicionamento de permissão.** "Novo cliente",
  "Editar", "Desativar", "Reativar" são renderizados incondicionalmente
  nos templates de Clientes, independentemente da autorização real —
  não é falha de segurança (o backend já nega), mas é divergência entre
  interface e autorização; destino provável: item de UI futuro.
- **Sem interface para conceder/revogar habilitações.** Nenhuma tela de
  produto nem Django Admin expõe `PapelAcesso`/`HabilitacaoPapel`/
  `HabilitacaoUsuario` — alterações exigem acesso direto ao banco; ver
  [current-state/configuracoes.md](../current-state/configuracoes.md).

Os demais achados originais deste item (ausência de escopo em
Clientes; busca apenas visual; aba "Documentos" com contador fixo)
foram resolvidos por WI-0002 ou já estão registrados em
[current-state/clientes.md](../current-state/clientes.md).

## Git e encerramento

Branch: `docs/reorganizacao-harness`.

Commit de implementação (H1): `da19001` — "feat(clientes): aplicar
autorização de módulo e habilitação nas views".

- [x] critérios de aceite com evidência;
- [x] diff revisado e escopo respeitado;
- [x] `current-state.md` atualizado nesta entrega;
- [x] achados laterais registrados acima.

## Referências

- [current-state/clientes.md](../current-state/clientes.md)
- [authorization-matrix.md#clientes](../../security/authorization-matrix.md#clientes)
- [WI-0002 — Escopo e responsabilidade de Clientes](WI-0002-escopo-responsabilidade-clientes.md)
