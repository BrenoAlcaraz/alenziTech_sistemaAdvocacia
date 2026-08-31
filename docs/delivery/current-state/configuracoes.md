---
title: Estado atual — Configurações
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Configurações

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [configuracoes.md](../../product/modules/configuracoes.md)
(especificação canônica) e
[authorization-matrix.md#configurações-e-administração-do-escritório](../../security/authorization-matrix.md#configurações-e-administração-do-escritório).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/configuracoes/views.py` implementa `index`, `editar_perfil`
(`@login_required`, opera sobre `request.user`) e as rotas
administrativas `novo_usuario`, `equipes`, `nova_equipe`,
`editar_equipe`, `equipe_membros`, `remover_membro_equipe`,
`alternar_gerente_equipe`, `permissoes`, `editar_escritorio`, todas
protegidas por `@requer_admin_escritorio`. A tela `permissoes`
configura `PermissaoPapel` apenas pelo caminho legado de `tipo_conta`
(`limitado`/`financeiro`), não por `PapelAcesso`/`UsuarioPapel`.

## Diferenças para o alvo canônico

[configuracoes.md](../../product/modules/configuracoes.md) lista
"papéis de acesso" e "habilitações" no escopo funcional — nenhuma
rota foi identificada para administrar `PapelAcesso` ou
`HabilitacaoPapel`/`HabilitacaoUsuario` diretamente. Edição de
identidade visual (`ConfiguracaoVisual`) não possui rota tenant
identificada; permanece administrável apenas via Django Admin no
schema público.

## Dependências ou bloqueios

Fase A do roadmap (a tela que configura autorização deveria, ela
mesma, refletir o kernel dinâmico que administra).
