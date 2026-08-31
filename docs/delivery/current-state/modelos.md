---
title: Estado atual — Modelos
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Modelos

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [modelos.md](../../product/modules/modelos.md) (especificação
canônica) e [authorization-matrix.md#modelos](../../security/authorization-matrix.md#modelos).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/modelos/views.py` implementa `lista`, `novo`, `detalhe`,
`editar`, `importar`. `ModeloPeca.conteudo` é um campo de texto (sem
`FileField`). A importação (`ImportarModeloPecaForm`) valida extensão
(`.pdf`/`.docx`) e tamanho máximo (10 MB) e extrai texto via `pypdf`/
`python-docx`. A busca em `lista` (`?q=...`) é real: o `QuerySet` é
filtrado por `titulo`/`categoria`/`area_direito`/`conteudo` a partir
do parâmetro `q`. `EstiloEscritorio` existe como model, sem
`views.py`/`urls.py` identificados; `templates/modelos/lista.html`
tem uma aba "Meu estilo" (`?aba=estilo`) cujo conteúdo é um texto
estático informando que "a configuração de estilo do escritório será
implementada na próxima fase de revisão" — a interface já anuncia
essa ausência, em vez de apresentar um formulário não funcional.

## Diferenças para o alvo canônico

[modelos.md](../../product/modules/modelos.md) prevê integração futura
com IA (condicionada ao PDR-0008) e versionamento — nenhum desses pontos
está implementado; categorização por texto livre e área do direito já
existem. A habilitação
`modelos_editar_estilo` existe no kernel sem rota correspondente para
`EstiloEscritorio`. O acervo já é listado sem filtro por `criado_por`,
coerente com o novo alvo institucional, mas as views ainda não exigem
autorização de módulo e o kernel ainda mantém o nível obsoleto
`somente_seus`/`todos` para Modelos.

## Dependências ou bloqueios

[PDR-0008](../../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
para a integração futura com IA; Fase A e B para autorização/escopo.
