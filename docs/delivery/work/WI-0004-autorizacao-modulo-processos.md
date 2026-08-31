---
title: WI-0004 — Autorização do módulo Processos
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# WI-0004 — Autorização do módulo Processos

## Estado

done

## Fase do roadmap

Fase: Fase A — Consolidar autorização nas operações

## Objetivo

Aplicar autorização backend do módulo `processos`
(`tem_permissao_modulo(user, "processos")`) às nove operações de
`apps/processos/views.py`, sem habilitações granulares nem escopo de
dados — política de autorização binária por módulo formalizada em
[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md).

## Escopo entregue

As nove rotas (`lista`, `detalhe`, `novo`, `editar`, `arquivados`,
`arquivar`, `reabrir`, `adicionar_movimentacao`, `adicionar_parte`)
negam acesso (`raise PermissionDenied`, backend, antes de qualquer
leitura/mutação) a um usuário sem autorização de módulo. Nenhuma
habilitação (`processos_criar`/`processos_editar`/
`processos_andamento_adicionar`) é consultada — decisão deliberada do
PDR-0010, não lacuna. Administrador do escritório autorizado
independentemente do kernel de papéis dinâmicos.

## Fora do escopo

Escopo por `Processo.responsavel`, responsabilidade obrigatória,
`nivel` como filtro e IDOR intra-tenant — pendentes para
[WI-0005](WI-0005-escopo-responsabilidade-processos.md) (`in_progress`).
Módulo Clientes, `ParteProcesso`/PDR-0001, IA/Laboratório e templates
não foram tocados.

## Estado atual

O estado consolidado de autorização de Processos está em
[current-state/processos.md](../current-state/processos.md) e
[authorization-matrix.md#processos](../../security/authorization-matrix.md#processos)
— não duplicado aqui.

## Critérios de aceite

Usuário sem módulo `processos` negado (403, sem mutação) nas nove
rotas; usuário com módulo autorizado (mesmo sem nenhuma habilitação
granular) preserva as nove rotas; Administrador autorizado
independentemente de `UsuarioPapel`/`PermissaoPapel`; `nivel` não lido;
nenhuma migration criada. Evidência:
`apps/processos/tests/test_autorizacao.py` — 30 testes
(`TestProcessosAutorizacaoModuloNegado`/`...ModuloConcedido`/
`...Administrador`), `OK`. `apps.accounts` (86) e `apps.clientes` (57)
sem regressão.

## Review independente

Review completo encontrou quatro findings, todos exclusivamente
documentais (sem finding funcional, de teste, autorização, migration
ou escopo de código); corrigidos no delta aprovado. Delta-review final:
**APROVADO**.

## Achados fora do escopo

Nenhum achado funcional fora do escopo.

## Git e encerramento

Branch: `docs/reorganizacao-harness`.

Commit de implementação (H1): `ece9ead` — "feat(processos): aplicar
autorização do módulo".

```text
python manage.py test apps.processos --noinput → 30 testes, OK
python manage.py test apps.accounts --noinput → 86 testes, OK
python manage.py test apps.clientes --noinput → 57 testes, OK
python manage.py check → sem achados
python manage.py makemigrations --check --dry-run → sem alteração pendente
git diff --check → aprovado
```

Validação manual: não aplicável (autorização backend pura, sem mudança
de template/rota/fluxo).

- [x] critérios de aceite com evidência;
- [x] diff revisado e escopo respeitado;
- [x] `current-state.md`, `roadmap.md`, matriz de autorização e
  `processos.md` atualizados nesta entrega;
- [x] review independente e delta-review registrados — aprovados;
- [x] Fase A de Processos concluída; Fase B pendente no WI-0005.

## Referências

- [current-state/processos.md](../current-state/processos.md)
- [authorization-matrix.md#processos](../../security/authorization-matrix.md#processos)
- [PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [WI-0005 — Escopo e responsabilidade em Processos](WI-0005-escopo-responsabilidade-processos.md) (`in_progress`)
