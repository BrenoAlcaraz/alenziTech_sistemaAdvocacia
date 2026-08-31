---
title: Estado atual — Clientes
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Clientes

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [clientes.md](../../product/modules/clientes.md) (especificação
canônica) e [authorization-matrix.md#clientes](../../security/authorization-matrix.md#clientes).

## Estado

Parcialmente implementado.

## Implementado no HEAD

`apps/clientes/views.py` implementa `lista`, `detalhe`, `novo`,
`editar`, `desativar`, `inativos`, `reativar`, todas com
`@login_required` combinado com `tem_permissao_modulo(request.user,
"clientes")`, negado com `raise PermissionDenied` antes de qualquer
leitura ou mutação (WI-0001, commit `da19001`). `novo` também exige
`tem_habilitacao(request.user, "clientes", "clientes_criar")` e
`editar` exige `tem_habilitacao(request.user, "clientes",
"clientes_editar")`, ambas verificadas antes da lógica da view.
`desativar`, `inativos` e `reativar` permanecem apenas com autorização
de módulo — nenhuma habilitação específica existe para essas três
operações no kernel atual.

**Escopo de dados e responsabilidade (WI-0002, commit `07675f7`)**:
`Cliente.responsavel` é obrigatório no schema (`null=False`,
`on_delete=PROTECT`), garantido também por migration de dados
(`0006_cliente_responsavel_obrigatorio.py`) que remove, de forma
reproduzível, qualquer `Cliente` remanescente com `responsavel IS
NULL` antes de tornar o campo obrigatório — a contagem desses registros
no banco de desenvolvimento auditado era zero antes da migration.
`lista`, `detalhe` e `inativos` resolvem um escopo efetivo de leitura
(`todos`/`somente_seus`) por requisição, via `nivel_acesso_modulo()` e
um parâmetro `?escopo=` opcional, sem estado persistente; o parâmetro
nunca amplia acesso acima do nível máximo autorizado do usuário, e um
valor ausente, vazio ou desconhecido é tratado distintamente (ausente
usa o padrão; presente e inválido nega com 403). `editar`, `desativar`
e `reativar` usam um `QuerySet` de mutação separado, restrito ao
Administrador do escritório ou a `Cliente.responsavel ==
request.user`, independente do escopo de leitura resolvido — um usuário
não administrador com nível máximo `todos` visualiza qualquer cliente
do tenant, mas só muta os de sua própria responsabilidade; um cliente
fora do escopo aplicável retorna 404 em todas as operações que
carregam objeto por `pk`. Na criação, conta não administrador tem
`responsavel` sempre definido como `request.user`, sem campo editável
no formulário (adulteração via `POST` é ignorada, pois o campo não
integra o formulário dessa conta); o Administrador do escritório vê o
campo pré-preenchido com o próprio usuário, editável, restrito a
usuários ativos do tenant atual e pesquisável por nome (filtro
client-side em JavaScript). Reatribuição de responsável em edição é
exclusiva do Administrador do escritório, com a mesma restrição de
usuários ativos. Escopo por equipe ("da equipe") existe apenas como
placeholder visual desabilitado, em `templates/clientes/lista.html`/
`inativos.html` e em `templates/configuracoes/permissoes.html`, sem
nenhuma regra funcional nem valor persistido.

`templates/clientes/lista.html` e `templates/processos/lista.html`
incluem o mesmo componente de busca (`components/search_bar.html`),
marcado no próprio template como "Barra de busca visual — sem lógica
real nesta fase"; nem `clientes/views.py::lista` nem
`processos/views.py::lista` leem um parâmetro de busca da URL,
confirmando que a busca é apenas visual. Cobertura de teste:
`apps/clientes/tests/test_autorizacao.py` (26 testes, WI-0001) e
`apps/clientes/tests/test_escopo.py` (31 testes, WI-0002) — ver
[current-state.md#testes](../current-state.md#testes).

## Diferenças para o alvo canônico

Escopo por `responsavel` está aplicado (WI-0002), atendendo à exigência
de [clientes.md](../../product/modules/clientes.md) de que um usuário com
atuação restrita não alcance clientes fora de seu escopo. Permanecem
como diferença: escopo por equipe não possui nenhuma regra funcional
(apenas placeholder visual); `desativar`/`reativar`/`inativos` não
possuem habilitação específica no kernel atual (candidatas a
habilitação futura, ver
[authorization-matrix.md#clientes](../../security/authorization-matrix.md#clientes));
nenhuma administração de `PapelAcesso`/`HabilitacaoPapel`/
`HabilitacaoUsuario` existe por interface de produto ou Django Admin —
lacuna já registrada em
[WI-0001](../work/WI-0001-autorizacao-backend-clientes.md).
`templates/clientes/detalhe.html` exibe uma aba "Documentos" com um
contador fixo `(2)` no rótulo da aba, sem relação com nenhum
`QuerySet` ou model — ao abrir a aba, o conteúdo é sempre um estado
vazio ("Nenhum documento anexado."), consistente com a ausência de
`FileField` em `Cliente` já registrada em
[data-scope.md](../../security/data-scope.md).

## Dependências ou bloqueios

Fase A (autorização conforme a política canônica do módulo) e Fase B
(escopo de dados) aplicadas em Clientes via WI-0001 e WI-0002,
respectivamente. Em Processos, o WI-0004 concluiu a Fase A com
autorização binária por módulo, conforme PDR-0010 e o commit `ece9ead`;
o módulo já possui a implementação do WI-0005 no HEAD, embora o
fechamento formal desse WI permaneça pendente.
Tarefas, Agenda, Financeiro, Dashboard, Chat, Modelos, Laboratório e
Configurações permanecem na Fase A. Nenhum PDR específico de Clientes
está em aberto.
