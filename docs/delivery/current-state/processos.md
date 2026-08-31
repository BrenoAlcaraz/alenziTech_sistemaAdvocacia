---
title: Estado atual — Processos
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Processos

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [processos.md](../../product/modules/processos.md) (especificação
canônica) e [authorization-matrix.md#processos](../../security/authorization-matrix.md#processos).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/processos/views.py` implementa `lista`, `detalhe`, `novo`,
`editar`, `arquivados`, `arquivar`, `reabrir`, `adicionar_movimentacao`,
`adicionar_apenso`, `remover_apenso`, `adicionar_parte`,
`adicionar_advogado`, `alterar_classificacao_parte`,
`remover_advogado`, todas com `@login_required` combinado com
`tem_permissao_modulo(request.user, "processos")`, negado com `raise
PermissionDenied` antes de qualquer leitura ou mutação (WI-0004).
Nenhuma rota consulta `tem_habilitacao()`: as habilitações já
existentes no kernel (`processos_criar`, `processos_editar`,
`processos_andamento_adicionar`) não restringem nenhuma operação nesta
versão, conforme
[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md).

Escopo e responsabilidade (WI-0005) estão implementados:
`Processo.responsavel` é obrigatório e protegido (`on_delete=PROTECT`,
sem `null=True`); `_resolver_escopo`/`_processos_no_escopo` aplicam
`somente_seus`/`todos` tanto na listagem quanto no carregamento do
objeto em `detalhe`; `_processos_mutaveis` restringe mutação ao
Administrador do escritório ou ao responsável. Reatribuir o responsável
(via `editar`, com `ProcessoResponsavelForm`) é exclusivo do
Administrador — checado por `is_admin`, não por habilitação; não há
ainda a habilitação `processos_atribuir_responsavel` aprovada em
[PDR-0014](../../product/decisions/PDR-0014-responsavel-integrantes-processos.md),
nem a relação de integrante habilitado (`usuario_processos`) que o
mesmo PDR aprova.

Partes (WI-0006) estão implementadas segundo o modelo de três dimensões
de PDR-0001/PDR-0011: `ParteProcesso` (polo, qualificação, vínculo),
`RepresentanteParte` (1:N, interno/externo), `AutoridadeProcessual`
(juiz separado das partes) e `HistoricoClassificacaoParte`
(rastreabilidade). Esse modelo foi substituído por
[PDR-0013](../../product/decisions/PDR-0013-partes-processo-modelo-simplificado.md),
que aprova um único campo de papel e advogado em texto livre — o código
ainda reflete o modelo substituído, não o vigente.

Apensos (WI-0007) estão implementados como `VinculoProcessoApenso`,
relação simétrica sem hierarquia, com `adicionar_apenso`/
`remover_apenso` — consistente com
[PDR-0012](../../product/decisions/PDR-0012-relacao-simetrica-processos-apensos.md),
que permanece vigente sem alteração.

`arquivar`/`reabrir` alternam `Processo.status` entre `ativo` e
`arquivado`, restritos por `_processos_mutaveis` (Administrador ou
responsável), sem consultar habilitação granular — comportamento coerente
com a autorização binária vigente de PDR-0010/PDR-0014.

`Processo.equipe` é pré-preenchido via `equipe_padrao_para_usuario()`
quando o usuário pertence a exatamente uma equipe ativa, mas não
participa de escopo ou autorização. Cobertura de teste:
`apps/processos/tests/test_autorizacao.py`, `test_escopo.py`,
`test_apensos.py` — ver [current-state.md#testes](../current-state.md#testes).

> Nota de consistência: as entregas de WI-0005 e WI-0006 acima descritas
> já estão refletidas no código auditado, mas os respectivos Work Items
> ([WI-0005](../work/WI-0005-escopo-responsabilidade-processos.md),
> [WI-0006](../work/WI-0006-participantes-advogados-processos.md))
> seguem com `Estado: in_progress` — fechamento formal (evidência final,
> review, encerramento) ainda pendente nos próprios WIs.

## Diferenças para o alvo canônico

Habilitação granular (`processos_criar`/`processos_editar`/
`processos_andamento_adicionar`) permanece deliberadamente não
aplicada nesta versão, conforme PDR-0010 — evolução futura possível,
não dívida bloqueante da Fase A.

`processos_atribuir_responsavel` ([PDR-0014](../../product/decisions/PDR-0014-responsavel-integrantes-processos.md))
ainda não existe no kernel; reatribuição de responsável continua
exclusiva do Administrador no código, sem a via delegável aprovada.
Integrante habilitado (`usuario_processos`, N por processo, distinto de
responsável e de equipe) ainda não existe no código.

O modelo de Partes implementado (três dimensões, `RepresentanteParte`,
`AutoridadeProcessual`, `HistoricoClassificacaoParte`) segue PDR-0001/
PDR-0011, que foram substituídos por
[PDR-0013](../../product/decisions/PDR-0013-partes-processo-modelo-simplificado.md).
É uma divergência no sentido oposto ao usual: o código está mais
elaborado do que o modelo hoje aprovado, não menos. Um Work Item de
simplificação/reversão fica pendente.

Equipe não concede acesso, não filtra Processos e não participa do
escopo aprovado, conforme PDR-0010.

## Dependências ou bloqueios

[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
(autorização, escopo e responsabilidade de Processos — Fases A e B
concluídas via WI-0004/WI-0005);
[PDR-0012](../../product/decisions/PDR-0012-relacao-simetrica-processos-apensos.md)
(apensos, concluído via WI-0007, sem divergência);
[PDR-0013](../../product/decisions/PDR-0013-partes-processo-modelo-simplificado.md)
(Partes — Work Item de simplificação pendente, revertendo parte do que
WI-0006 implementou);
[PDR-0014](../../product/decisions/PDR-0014-responsavel-integrantes-processos.md)
(habilitação de responsabilidade delegável e integrantes habilitados —
Work Item de implementação pendente).
