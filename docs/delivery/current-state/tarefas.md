---
title: Estado atual — Tarefas
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Tarefas

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [tarefas.md](../../product/modules/tarefas.md) (especificação
canônica) e [authorization-matrix.md#tarefas](../../security/authorization-matrix.md#tarefas).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/tarefas/views.py` implementa `quadro`, `lista`, `nova`,
`editar`, `concluir`, `reabrir`, `iniciar`, `excluir`. Toda tarefa
nasce com `responsavel = request.user`, atribuído diretamente na view
`nova`. `TarefaForm.Meta.fields` não inclui `responsavel` nem
`status`; a view `editar` mesmo assim recarrega
`responsavel_original`/`status_original` antes de salvar e os
reatribui ao objeto após `form.save(commit=False)`, o que hoje é
código defensivo sem efeito prático observável, já que o formulário
não oferece nenhum campo por onde esses valores poderiam ser
alterados nesse fluxo.

## Diferenças para o alvo canônico

[PDR-0002](../../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md)
exige campos separados de criador, atribuidor, destinatário da
atribuição e data da atribuição, além de delegação direta a outro
usuário — nenhum desses campos existe em `Tarefa`, que possui apenas
`responsavel`. A habilitação `tarefas_atribuir_outros` existe no
kernel, mas não há rota ou campo que a consuma. O status `cancelada`
previsto em PDR-0002 não existe (`Tarefa.STATUS_CHOICES` é `a_fazer`,
`em_andamento`, `concluida`); em seu lugar existe `excluir` (exclusão
física). A notificação de conclusão ao criador aprovada em
[PDR-0016](../../product/decisions/PDR-0016-notificacoes-tarefas-agenda.md)
também não está implementada; não há model ou serviço de notificação no
HEAD.

## Dependências ou bloqueios

[PDR-0002](../../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md)
(Fase C do roadmap, modelagem de dados),
[PDR-0016](../../product/decisions/PDR-0016-notificacoes-tarefas-agenda.md);
Fase A e B para autorização e escopo.
