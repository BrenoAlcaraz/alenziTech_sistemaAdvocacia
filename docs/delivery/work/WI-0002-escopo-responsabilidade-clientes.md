---
title: WI-0002 — Escopo e responsabilidade de Clientes
status: canonical
owner: delivery
last_reviewed: 2026-08-18
---

# WI-0002 — Escopo e responsabilidade de Clientes

## Estado

done

## Fase do roadmap

Fase: Fase B — Aplicar escopo de dados

Objetivo relacionado: filtrar `QuerySet`s de listagem por escopo
(responsável), carregar objetos de detalhe/edição/exclusão já dentro do
escopo autorizado, e criar testes intra-tenant, conforme
[roadmap.md](../roadmap.md#fase-b--aplicar-escopo-de-dados).

Dependência: Fase A de Clientes, concluída por
[WI-0001](WI-0001-autorizacao-backend-clientes.md) (`done`, commit
`da19001`). [roadmap.md](../roadmap.md#sequência-oficial) permite avanço
de fase módulo a módulo: "se a Fase A de Clientes está concluída,
Clientes pode avançar para a Fase B mesmo que Processos, Tarefas, Agenda
ou outros módulos ainda estejam na Fase A."

## Objetivo

Aplicar escopo de dados por responsável ao módulo Clientes, sobre a
autorização de módulo/habilitação já aplicada pelo WI-0001, sem
implementar escopo por equipe. Consolida:

1. escopo de visualização por responsável (`somente_seus`/`todos`);
2. proteção de objeto contra acesso fora do escopo (IDOR intra-tenant
   → 404);
3. `Cliente.responsavel` obrigatório;
4. reatribuição de responsável restrita ao Administrador do escritório;
5. seletor visual de escopo, com o backend como fonte de verdade;
6. mesma lógica para clientes ativos e inativos.

## Contexto e motivação

[WI-0001](WI-0001-autorizacao-backend-clientes.md) aplicou autorização
de módulo (`tem_permissao_modulo`) e habilitação
(`clientes_criar`/`clientes_editar`) às sete rotas de
`apps/clientes/views.py`, mas registrou explicitamente, em "Fora de
escopo" e em "Achados fora do escopo", que nenhuma delas filtra por
`Cliente.responsavel`: um usuário autorizado ao módulo alcança qualquer
cliente do tenant por `pk`, independentemente de quem seja o
responsável. Isso é consistente com
[data-scope.md](../../security/data-scope.md#aplicação-por-módulo) e com
[authorization-matrix.md](../../security/authorization-matrix.md#clientes),
que classificam todas as sete operações de Clientes como "Lacuna
constatada" quanto a escopo e autorização sobre objeto. Este item é a
próxima unidade de trabalho autorizada pelo Product Owner: aplicar a
Fase B especificamente a Clientes.

## Evidência do estado atual

Reconfirmada por leitura direta do HEAD (commit `26ba2ec`) nesta
preparação:

- **Comportamento existente**: `apps/clientes/views.py::lista` filtra
  apenas por `ativo=True`; `inativos` apenas por `ativo=False`; nenhuma
  das sete views lê `Cliente.responsavel` como filtro.
  `detalhe`/`editar`/`desativar`/`reativar` usam `get_object_or_404`
  com, no máximo, uma condição de `ativo`, sem condição de posse —
  qualquer usuário autorizado ao módulo alcança qualquer cliente do
  tenant por `pk`.
- **Lacuna constatada**:
  [data-scope.md](../../security/data-scope.md#aplicação-por-módulo) e
  [authorization-matrix.md](../../security/authorization-matrix.md#clientes)
  confirmam a ausência de escopo aplicado a Clientes.
- **Cobertura de teste ausente**: `apps/clientes/tests/test_autorizacao.py`
  (26 testes) cobre autorização de módulo/habilitação, mas nenhum teste
  cobre escopo por `responsavel`, IDOR intra-tenant, ou o seletor de
  escopo — confirmado por leitura integral do arquivo.
- **Model atual**: `Cliente.responsavel` é `ForeignKey(AUTH_USER_MODEL,
  on_delete=SET_NULL, null=True, blank=True)` — opcional, permite
  clientes sem responsável.
- **Kernel disponível**: `nivel_acesso_modulo(user, "clientes")` já
  resolve `somente_seus`/`todos` via `permissao_efetiva()`
  (`apps/accounts/permissoes.py`), incluindo o caminho de administrador
  (`_nivel_admin` retorna o maior nível, `todos`, para
  `usuario_admin_escritorio()`). Nenhuma view de Clientes o consulta
  hoje — confirmado nesta auditoria e já registrado em
  [authorization-model.md](../../security/authorization-model.md#distinções-obrigatórias).
- **Operação planejada**: [roadmap.md](../roadmap.md#fase-b--aplicar-escopo-de-dados)
  define, como objetivo da Fase B, "filtrar `QuerySet`s de listagem por
  escopo... carregar objetos de detalhe/edição/exclusão já dentro do
  escopo autorizado... criar testes intra-tenant".
- **Contagem inicial de `Cliente.responsavel IS NULL`**: **0** (zero) em
  todos os tenants do banco de desenvolvimento auditado nesta
  preparação (schema `demo`: 12 clientes, 0 com `responsavel` nulo;
  nenhum outro schema de tenant de dados encontrado além de `demo`).
  Comando usado: iteração via `django_tenants.utils.schema_context` sobre
  `get_tenant_model().objects.all()`, contando
  `Cliente.objects.filter(responsavel__isnull=True).count()` por schema.
  Apesar da contagem atual ser zero, a migration de remoção é criada de
  forma reproduzível (não condicionada a este resultado específico),
  pois o Product Owner autorizou essa remoção como salvaguarda para
  qualquer dado fictício remanescente em outro ambiente/schema no
  momento da aplicação real da migration.
- **Templates atuais**: `templates/clientes/lista.html`,
  `detalhe.html`, `form.html` e `inativos.html` não possuem nenhum
  seletor de escopo nem exibem `responsavel`; `form.html` não expõe
  nenhum campo de responsável (a atribuição ocorre apenas no backend,
  em `views.py::novo`).
- **Tela de permissões**: `apps/configuracoes/views.py::permissoes` e
  `templates/configuracoes/permissoes.html` já expõem, para os tipos de
  conta configuráveis (`limitado`, `financeiro`), radios
  `somente_seus`/`todos` por módulo (incluindo `clientes`), persistidos
  em `PermissaoPapel`. Não existe hoje nenhuma opção "Da equipe" nessa
  tela, nem qualquer campo `equipe` em `Cliente`.

## Resultado esperado

Todas as seis operações de leitura/mutação de Clientes que dependem de
um `Cliente` específico ou de uma listagem (`lista`, `detalhe`,
`editar`, `desativar`, `inativos`, `reativar`) passam a resolver um
escopo efetivo (`somente_seus`/`todos`) por requisição, com o backend
como única fonte de verdade: quando o escopo efetivo é `somente_seus`,
o `QuerySet`/objeto carregado é restrito a `Cliente.responsavel ==
request.user`; uma tentativa de acessar por URL um cliente fora desse
escopo retorna 404; uma tentativa de solicitar um escopo acima do nível
máximo autorizado do usuário retorna 403. `Cliente.responsavel` passa a
ser obrigatório no schema; a criação sempre preenche `responsavel`
(usuário autenticado para conta limitada; usuário selecionado ou o
próprio Administrador para Administrador do escritório); a edição só
permite trocar `responsavel` quando o usuário for Administrador do
escritório, com a lista restrita a usuários ativos do tenant. Nenhuma
regra funcional de "Da equipe" é implementada — apenas placeholder
visual desabilitado. Este resultado não estende autorização de módulo
nem habilitação além do que o WI-0001 já aplica — ver "Fora de escopo".

## Fontes canônicas

- [../../security/overview.md](../../security/overview.md)
- [../../security/authorization-model.md](../../security/authorization-model.md)
- [../../security/data-scope.md](../../security/data-scope.md)
- [../../security/authorization-matrix.md](../../security/authorization-matrix.md#clientes)
- [../../product/modules/clientes.md](../../product/modules/clientes.md)
- [../../product/open-decisions.md](../../product/open-decisions.md)
- [../current-state.md](../current-state.md)
- [../roadmap.md](../roadmap.md#fase-b--aplicar-escopo-de-dados)
- [WI-0001](WI-0001-autorizacao-backend-clientes.md)

## Arquivos do HEAD a auditar antes da implementação

- `apps/clientes/models.py`
- `apps/clientes/forms.py`
- `apps/clientes/views.py`
- `apps/clientes/urls.py`
- `apps/clientes/tests/test_autorizacao.py`
- `apps/clientes/migrations/` (última: `0005_remove_cliente_departamento.py`)
- `templates/clientes/lista.html`, `detalhe.html`, `form.html`,
  `inativos.html`
- `apps/accounts/permissoes.py`
- `apps/accounts/permissoes_constants.py`
- `apps/accounts/models.py`
- `apps/accounts/decorators.py`
- `apps/configuracoes/views.py`
- `templates/configuracoes/permissoes.html`
- `config/settings/base.py` (confirmação de `TENANT_APPS`/`SHARED_APPS`
  para `django.contrib.auth` e `apps.clientes`)

A evidência acima foi reconfirmada no HEAD nesta preparação; qualquer
divergência encontrada durante a implementação deve ser revalidada
antes de alterar o arquivo correspondente.

**Confirmação relevante de Etapa 4 (workflow.md)**: `django.contrib.auth`
está listado tanto em `SHARED_APPS` quanto em `TENANT_APPS`
(`config/settings/base.py`), o que, no padrão `django-tenants`, resulta
em uma tabela `auth_user` própria por schema de tenant. Isso confirma
que `User.objects.filter(is_active=True)`, executado dentro do contexto
de schema da requisição atual, já retorna exclusivamente usuários do
tenant atual — nenhum filtro adicional de tenant é necessário para
cumprir "nunca pode selecionar usuário de outro tenant".

## Escopo permitido

### Pode alterar

- `apps/clientes/models.py` — tornar `responsavel` obrigatório
  (`null=False`, `blank=False`) e ajustar `on_delete` para um valor
  compatível com campo obrigatório (`PROTECT`, para não perder
  integridade referencial quando `null=True` deixa de ser válido).
  Nenhuma outra alteração de modelo.
- `apps/clientes/forms.py` — adicionar variante de formulário que expõe
  `responsavel` como campo selecionável (apenas para uso por
  Administrador do escritório), restrito a usuários ativos do tenant.
- `apps/clientes/views.py` — resolução de escopo efetivo, filtro de
  `QuerySet`/objeto por escopo nas seis operações aplicáveis, seleção
  condicional de formulário (Administrador vs. conta limitada),
  preenchimento/proteção de `responsavel`.
- `templates/clientes/lista.html`, `templates/clientes/inativos.html` —
  seletor visual de escopo (`Todos`/`Somente os seus`, mais placeholder
  desabilitado `Da equipe`), condicionado ao nível máximo autorizado do
  usuário.
- `templates/clientes/form.html` — exibição condicional do campo
  `responsavel` (editável e pesquisável para Administrador; somente
  leitura para conta limitada).
- `templates/configuracoes/permissoes.html` — alteração pequena e
  puramente visual: inserir a opção desabilitada "Da equipe" entre
  "Somente os seus" e "Todos", nas linhas que já usam esse padrão de
  nível. Nenhum valor novo é persistido por essa alteração.
- `docs/delivery/current-state.md` — apenas ao final da implementação, e
  apenas se o estado material tiver mudado.

### Pode criar

- `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
  (nome definitivo confirmado na implementação) — migration de dados
  (remoção de `Cliente` com `responsavel IS NULL`) seguida de migration
  de schema (`AlterField` tornando `responsavel` obrigatório).
- Testes novos em `apps/clientes/tests/` cobrindo os critérios de aceite
  deste item (arquivo novo, por exemplo
  `apps/clientes/tests/test_escopo.py`, para não misturar com os testes
  de autorização de módulo/habilitação do WI-0001).

### Migrations

Autorizadas, e exigidas pelo objetivo deste item — ver "Regra de
responsabilidade" e "Integridade do banco" abaixo. Limitadas
estritamente a: (1) remoção de `Cliente` com `responsavel IS NULL`; (2)
tornar `Cliente.responsavel` obrigatório. Nenhuma outra alteração de
schema é autorizada por este item (nenhum campo `equipe` em `Cliente`,
nenhuma nova habilitação, nenhuma alteração em `apps/accounts/models.py`).

### Documentação

- `docs/delivery/current-state.md`, somente ao final e somente se o
  estado material tiver mudado.

Nenhuma outra documentação pode ser alterada por este item, incluindo
`docs/delivery/roadmap.md`, PDRs, ADRs, e qualquer arquivo de instrução
de agente ou de configuração do repositório fora de `docs/delivery/`.

## Fora de escopo

> qualquer alteração útil, mas não necessária para satisfazer os
> critérios deste item, permanece fora do escopo até ser explicitamente
> incorporada.

- Escopo real por equipe, regra de gerente de equipe, compartilhamento
  de cliente entre equipes, `Cliente.equipe`, qualquer helper de escopo
  de equipe, qualquer interpretação funcional de "Da equipe" — apenas
  placeholder visual desabilitado é permitido, conforme "Direção da
  equipe" abaixo.
- Múltiplos responsáveis por cliente, responsável por processo, escopo
  de Processos/Tarefas/Agenda/Financeiro/Dashboard/Chat/Modelos.
- Administração completa de `PapelAcesso`/`Habilitacao*` (interface de
  concessão/revogação de papéis e habilitações) — permanece a mesma
  lacuna operacional já registrada em "Achados fora do escopo" do
  WI-0001.
- Novas habilitações `clientes_desativar`/`clientes_reativar` — as
  operações `desativar`/`inativos`/`reativar` continuam exigindo apenas
  autorização de módulo (Camada 1 do WI-0001) mais o escopo de dados
  deste item; nenhuma habilitação nova é criada.
- Hard delete de `Cliente` — a migration deste item remove apenas
  registros fictícios com `responsavel IS NULL`, por autorização
  explícita do Product Owner registrada em "Integridade do banco"; não
  introduz capacidade de exclusão física de `Cliente` como
  funcionalidade de produto.
- Qualquer regra de IA.
- `apps/accounts/permissoes.py`, `apps/accounts/permissoes_constants.py`,
  `apps/accounts/models.py`, `apps/accounts/decorators.py` são fontes a
  auditar, não alvo de alteração — o kernel já expõe tudo que este item
  precisa (`nivel_acesso_modulo`, `usuario_admin_escritorio`).
- `apps/configuracoes/views.py` não é alterado — apenas o template
  `permissoes.html` recebe o ajuste visual descrito acima.
- Busca textual funcional em `templates/clientes/lista.html`
  (`components/search_bar.html` permanece "visual, sem lógica real",
  achado já registrado pelo WI-0001).

## Regras funcionais e técnicas

### Direção da equipe

A hierarquia futura aprovada é `Todos > Da equipe > Somente os seus`.
Neste item, "Da equipe" não recebe nenhuma regra funcional: não filtra
dado algum, não é um valor selecionável que produza um escopo diferente
de `somente_seus`/`todos`, e não é persistido em nenhuma tabela. Ela
existe apenas como:

- opção visualmente desabilitada, com indicação "Em breve", no seletor
  de escopo de `templates/clientes/lista.html`/`inativos.html`;
- opção visualmente desabilitada, entre "Somente os seus" e "Todos", em
  `templates/configuracoes/permissoes.html`, nas linhas que já usam o
  padrão `somente_seus`/`todos`.

Uma tentativa de solicitar `escopo=da_equipe` (ou qualquer valor fora de
`somente_seus`/`todos`) pelo seletor de Clientes deve ser negada no
backend (403), pelo mesmo motivo que qualquer outro valor desconhecido:
o backend não reconhece esse escopo como válido.

### Seletor de escopo — mecanismo técnico

Mecanismo escolhido, entre as alternativas possíveis: **parâmetro de
consulta (`?escopo=`) sem estado persistente**, avaliado a cada
requisição, nas seis rotas aplicáveis (`lista`, `detalhe`, `editar`,
`desativar`, `inativos`, `reativar`). Não há sessão, cookie ou
preferência de usuário armazenada para o escopo selecionado — cada
requisição resolve seu próprio escopo efetivo a partir do parâmetro
presente nela e do nível máximo autorizado do usuário. Esta é a solução
mais simples identificada nesta auditoria, compatível com "Audite a
implementação atual e escolha a solução mais simples, preferencialmente
sem estado persistente desnecessário", e não exige nova tabela, sessão
nem middleware.

Resolução do escopo efetivo, por requisição:

1. Resolver `nivel_maximo = nivel_acesso_modulo(request.user,
   "clientes")` — já retorna `todos` para Administrador do escritório
   (via `_nivel_admin`) e o nível configurado (papel/individual/legado)
   para os demais usuários autorizados ao módulo. Se o valor resolvido
   não for `somente_seus` nem `todos` (por exemplo, string vazia por
   inconsistência de dados), tratar como `somente_seus` — mínimo seguro,
   nunca amplia acesso por omissão.
2. Ler `request.GET.get("escopo")`.
   - Ausente → escopo efetivo = `nivel_maximo` (comportamento padrão:
     Administrador e conta com máximo `todos` abrem em "Todos"; conta
     com máximo `somente_seus` abre em "Somente os seus").
   - Presente e fora de `{"somente_seus", "todos"}` (inclui
     `"da_equipe"` e qualquer outro valor) → `raise PermissionDenied`
     (403).
   - Presente e igual a `"todos"`, mas `nivel_maximo != "todos"` →
     `raise PermissionDenied` (403) — não é permitido ampliar acima do
     máximo autorizado.
   - Presente e igual a `"somente_seus"` → sempre permitido (reduzir a
     visualização é sempre permitido a qualquer usuário autorizado ao
     módulo, incluindo Administrador).
3. Em `lista`/`detalhe`/`inativos` (leitura), o escopo efetivo resultante
   determina o filtro do `QuerySet`/objeto. Em `editar`/`desativar`/
   `reativar` (mutação), o parâmetro `escopo` continua sendo validado
   (passos 1–2 acima, incluindo a negação de valor vazio/desconhecido/
   acima do máximo), mas o carregamento do objeto usa um `QuerySet`
   distinto, restrito a Administrador ou a `responsavel == request.user`,
   independente do valor de escopo resolvido — ver "Escopo de dados —
   leitura versus mutação" abaixo.

Esta resolução ocorre **depois** da Camada 1 (autorização de módulo) e,
em `novo`/`editar`, depois da Camada 2 (habilitação), preservando
integralmente o enforcement do WI-0001 — ver "Preservação do WI-0001"
abaixo.

### Escopo de dados — leitura versus mutação (distinção obrigatória)

`"todos"` é **escopo de visualização**, não autorização de mutação sobre
qualquer cliente. Esta distinção é obrigatória e foi corrigida após
review independente (ver "Evidência de execução" — Correção pós-review):

**Leitura** (`lista`, `detalhe`, `inativos`) — usa o escopo efetivo
resolvido por requisição (`_resolver_escopo`/`_clientes_no_escopo`):

- escopo efetivo `somente_seus` → `Cliente.responsavel == request.user`;
- escopo efetivo `todos` → nenhum filtro adicional por `responsavel`; o
  usuário alcança todos os clientes ativos/inativos autorizados do
  tenant, incluindo `detalhe` de um cliente cujo responsável é outro
  usuário — ver um usuário não administrador com nível máximo `todos`
  recebeu autorização para **visualizar** todo o tenant, não apenas os
  seus.

**Mutação** (`editar`, `desativar`, `reativar`) — usa um `QuerySet`
distinto (`_clientes_mutaveis`), independente do parâmetro `escopo` da
requisição:

- Administrador do escritório (`usuario_admin_escritorio()`) → alcança
  qualquer cliente do tenant para mutação;
- qualquer outro usuário, **mesmo com nível máximo `todos`** → só alcança,
  para mutação, `Cliente.responsavel == request.user`. Um cliente de
  outro responsável retorna 404 em `editar`/`desativar`/`reativar`,
  independentemente do escopo de visualização que esse usuário possua.

O parâmetro `?escopo=` continua sendo validado (403 em valor inválido,
vazio ou acima do máximo) mesmo nas rotas de mutação, por consistência
com a regra geral de negação de escalonamento — mas seu valor resolvido
não determina o `QuerySet` de mutação, apenas o de leitura.

### Autorização sobre objeto (IDOR intra-tenant)

Um `Cliente` que existe no tenant mas está fora do escopo aplicável à
operação (escopo de leitura para `detalhe`; posse por `responsavel`,
salvo Administrador, para `editar`/`desativar`/`reativar`) deve retornar
**404** — nunca carregar o objeto livremente para validar posse depois.
O carregamento nasce do `QuerySet` já restrito
(`get_object_or_404(<queryset>, pk=pk)`), conforme
[data-scope.md](../../security/data-scope.md#critérios-arquiteturais).
Administrador do escritório continua alcançando qualquer cliente do
tenant, tanto para leitura quanto para mutação.

### Regra de responsabilidade

`Cliente.responsavel` passa a ser obrigatório (`null=False`,
`blank=False`).

**Criação (`novo`)**:

- conta limitada (não administrador): `responsavel` não é exposto como
  campo editável no formulário; o backend sempre grava
  `cliente.responsavel = request.user`, mesmo que o `POST` contenha um
  campo `responsavel` manipulado — o campo não integra o formulário
  usado por essa conta, portanto qualquer valor de `responsavel` enviado
  no `POST` é ignorado pelo binding do formulário;
- Administrador do escritório: `responsavel` é exposto, pré-selecionado
  com o próprio Administrador, e pode ser alterado antes de salvar; a
  lista de opções é restrita a usuários ativos do tenant atual
  (`User.objects.filter(is_active=True)`, já implicitamente restrita ao
  tenant pela arquitetura de schema, conforme "Confirmação relevante de
  Etapa 4" acima); um usuário inativo não pode ser selecionado, pois não
  pertence ao `QuerySet` do campo.

**Edição (`editar`)**:

- conta limitada: `responsavel` não é exposto no formulário; o backend
  não altera `Cliente.responsavel` durante a edição, independentemente
  do conteúdo do `POST`;
- Administrador do escritório: `responsavel` é exposto, editável,
  restrito a usuários ativos do tenant, com busca por nome de usuário no
  campo (filtro client-side sobre as opções already carregadas — ver
  "Campo pesquisável" abaixo).

### Campo pesquisável

"Pesquisável por nome de usuário" é implementado como um campo de texto
auxiliar, ao lado do `<select>` de responsável, que filtra as opções já
carregadas por correspondência de texto (JavaScript vanilla, sem nova
dependência de frontend) — solução mais simples identificada, consistente
com o padrão já usado no projeto para campos de seleção de usuário
(nenhuma biblioteca de combobox pesquisável foi encontrada em uso no
HEAD auditado).

### Preservação do WI-0001

`tem_permissao_modulo(request.user, "clientes")` continua sendo exigido,
sem alteração de comportamento, nas sete rotas. `tem_habilitacao(...,
"clientes_criar")` continua exigido em `novo`; `tem_habilitacao(...,
"clientes_editar")` continua exigido em `editar`. O escopo de dados
deste item é uma camada adicional, avaliada depois dessas duas — nunca
as substitui.

### Integridade do banco

Estado aprovado pelo Product Owner: o sistema está em desenvolvimento e
os registros atuais são dados fictícios/mock. A contagem de
`Cliente.responsavel IS NULL` no banco de desenvolvimento auditado nesta
preparação é **0** (ver "Evidência do estado atual"). A remoção desses
registros fictícios está autorizada pelo Product Owner. A migration deve
ser reproduzível (`RunPython` explícito, não um `DELETE` manual fora de
migration) e deve, nesta ordem: (1) remover `Cliente` com `responsavel
IS NULL`; (2) tornar `Cliente.responsavel` obrigatório
(`null=False`). O arquivo de migration gerado deve ser lido e revisado
integralmente antes de ser aceito, conforme
[docs/delivery/work/README.md#migrations](README.md#migrations).

## Segurança e autorização

- Backend como autoridade: a resolução de escopo e a autorização sobre
  objeto ocorrem no backend, antes de qualquer leitura ou mutação de
  `Cliente`, independentemente do que a interface exiba ou oculte.
- Uma tentativa de solicitar escopo acima do máximo autorizado
  (`?escopo=todos` para um usuário com máximo `somente_seus`, ou
  `?escopo=da_equipe` para qualquer usuário) é negada no backend com
  403 — não depende de a interface esconder a opção.
- Um `POST` manipulado de `responsavel` por uma conta limitada não
  produz efeito, pois o campo não faz parte do formulário usado por essa
  conta — o binding do Django `ModelForm` ignora dados de `POST` que não
  correspondem a um campo declarado.
- Nenhuma resposta deste item amplia o escopo que o usuário já teria
  diretamente, conforme
  [overview.md](../../security/overview.md#princípios-canônicos).
- Este item não resolve escopo por equipe, autorização de ação para
  desativar/reativar (além da autorização de módulo já aplicada pelo
  WI-0001), nem qualquer lacuna já registrada em "Achados fora do
  escopo" do WI-0001 que não seja escopo por responsável.

## Decisões abertas e bloqueios

Nenhuma decisão em aberto (`OPEN-001`, `OPEN-002`) afeta este item —
ambas pertencem exclusivamente ao módulo Financeiro. Nenhum bloqueio foi
identificado: a Fase A de Clientes está concluída (WI-0001, `done`); o
kernel já expõe `nivel_acesso_modulo()`; o Product Owner já autorizou a
remoção de registros fictícios sem responsável; a arquitetura de schema
já garante isolamento de tenant para a lista de usuários selecionáveis.

Uma decisão técnica foi necessária durante esta preparação, sem
constituir decisão de produto nem exigir escalonamento: o `on_delete` de
`Cliente.responsavel` precisa mudar de `SET_NULL` (incompatível com
`null=False`) para outro valor. Optou-se por `PROTECT` — impede a
exclusão de um `User` que ainda seja responsável por algum `Cliente`,
preservando integridade referencial sem apagar dados de cliente como
efeito colateral de excluir um usuário. Nenhuma view do HEAD auditado
implementa exclusão física de `User`, portanto este comportamento não é
exercitado por nenhum fluxo existente; caso o produto venha a precisar
de exclusão física de usuários no futuro, o tratamento de
`Cliente.responsavel` nesse fluxo é decisão de outro item.

## Dependências

- Depende de [WI-0001](WI-0001-autorizacao-backend-clientes.md) (`done`),
  que aplicou autorização de módulo/habilitação a Clientes.
- Depende apenas do kernel já implementado em
  `apps/accounts/permissoes.py` (`nivel_acesso_modulo`,
  `usuario_admin_escritorio`), que este item não altera.
- Não pode ser executado em paralelo com outro Work Item que também
  altere `apps/clientes/views.py`, `apps/clientes/models.py` ou
  `apps/clientes/forms.py`, para evitar conflito de escopo nos mesmos
  arquivos.

## Critérios de aceite

- [x] `lista` com escopo efetivo `somente_seus` retorna apenas clientes
  ativos com `responsavel == request.user` —
  `TestClientesEscopoSomenteSeus.test_lista_mostra_apenas_clientes_proprios`;
- [x] `lista` com escopo efetivo `todos` retorna todos os clientes ativos
  autorizados do tenant —
  `TestClientesEscopoTodos.test_lista_padrao_mostra_todos`;
- [x] Administrador do escritório, sem parâmetro de escopo, vê `todos` —
  `TestClientesEscopoAdmin.test_lista_admin_ve_todos_por_padrao`;
- [x] `detalhe` de cliente próprio (dentro do escopo) funciona
  normalmente — `TestClientesEscopoSomenteSeus.test_detalhe_proprio_funciona`;
- [x] `detalhe` de cliente alheio (fora do escopo efetivo `somente_seus`)
  retorna 404 — `TestClientesEscopoSomenteSeus.test_detalhe_alheio_retorna_404`;
- [x] `editar` de cliente próprio funciona normalmente —
  `TestClientesEscopoAdmin.test_admin_pode_reatribuir_responsavel` (via
  `editar`) e regressão de `TestClientesAutorizacaoModuloConcedido.test_editar_post_autorizado_altera_cliente`;
- [x] `editar` de cliente alheio (fora do escopo) retorna 404 —
  `TestClientesEscopoSomenteSeus.test_editar_alheio_retorna_404`;
- [x] `desativar` de cliente próprio funciona normalmente —
  `TestClientesEscopoSomenteSeus.test_desativar_proprio_funciona`;
- [x] `desativar` de cliente alheio (fora do escopo) retorna 404, sem
  alterar `ativo` —
  `TestClientesEscopoSomenteSeus.test_desativar_alheio_retorna_404_sem_alterar`;
- [x] `inativos` respeita o mesmo escopo de `lista` —
  `TestClientesEscopoSomenteSeus.test_inativos_respeita_escopo`;
- [x] `reativar` de cliente próprio funciona normalmente —
  `TestClientesEscopoSomenteSeus.test_reativar_proprio_funciona`;
- [x] `reativar` de cliente alheio (fora do escopo) retorna 404, sem
  alterar `ativo` —
  `TestClientesEscopoSomenteSeus.test_reativar_alheio_retorna_404_sem_alterar`;
- [x] conta limitada cria cliente com `responsavel == request.user`,
  independentemente do que o `POST` contenha —
  `TestClientesEscopoSomenteSeus.test_criar_cliente_forca_responsavel_request_user`;
- [x] um `POST` de `novo`/`editar` por conta limitada tentando adulterar
  `responsavel` não altera o responsável persistido —
  `TestClientesEscopoSomenteSeus.test_post_adulterado_em_editar_nao_troca_responsavel`
  (e o teste de criação acima);
- [x] Administrador do escritório pode reatribuir `responsavel` de
  qualquer cliente do tenant —
  `TestClientesEscopoAdmin.test_admin_pode_reatribuir_responsavel`;
- [x] Administrador do escritório não pode atribuir um usuário inativo
  como `responsavel` (rejeitado pela validação do formulário) —
  `TestClientesEscopoAdmin.test_admin_nao_pode_atribuir_usuario_inativo`;
- [x] nenhum `Cliente` novo pode ser persistido sem `responsavel` —
  garantido tanto pela regra de aplicação (view) quanto pela restrição
  de schema (`null=False`) —
  `TestClienteResponsavelObrigatorio.test_cliente_sem_responsavel_nao_pode_ser_persistido`;
- [x] uma tentativa de solicitar `?escopo=todos` acima do nível máximo
  autorizado do usuário retorna 403 —
  `TestClientesEscopoSomenteSeus.test_escalar_para_todos_retorna_403`;
- [x] uma tentativa de solicitar `?escopo=da_equipe` (ou qualquer valor
  inválido) retorna 403 —
  `TestClientesEscopoSomenteSeus.test_escopo_da_equipe_retorna_403`;
- [x] o seletor do Administrador (ou de conta com máximo `todos`) permite
  alternar entre `Todos` e `Somente os seus` —
  `TestClientesEscopoAdmin.test_admin_pode_reduzir_para_somente_seus`,
  `TestClientesEscopoTodos.test_reduzir_para_somente_seus_funciona` e
  `TestClientesEscopoTodos.test_seletor_exibe_todos_e_somente_seus`;
- [x] "Da equipe" não produz nenhum escopo funcional — nem como valor de
  `?escopo=`, nem como campo persistido — confirmado pelo teste de 403
  acima e por leitura do template (`templates/configuracoes/permissoes.html`
  usa `<input disabled>`, nunca submetido);
- [x] nenhuma migration fora do escopo declarado foi criada — apenas
  `0006_cliente_responsavel_obrigatorio.py`, revisada integralmente
  nesta sessão;
- [x] `Cliente.objects.filter(responsavel__isnull=True).count()` é zero
  após a migration, no ambiente de desenvolvimento auditado — já era
  zero antes da migration (ver "Evidência do estado atual"); confirmado
  também estruturalmente pela restrição `null=False` do schema;
- [x] os testes negativos de autorização de módulo/habilitação do
  WI-0001 continuam passando sem alteração de comportamento — 26/26
  testes de `test_autorizacao.py` `OK` (fixture `_cliente()` adaptada
  para exigir `responsavel`, sem alterar nenhuma asserção existente).

Critérios adicionados após correção pós-review (ver "Evidência de
execução" — Correção pós-review):

- [x] `?escopo=` presente e vazio retorna 403, distinto de `escopo`
  ausente (que usa o padrão) —
  `TestClientesEscopoSomenteSeus.test_escopo_vazio_retorna_403`;
- [x] em edição, o campo somente leitura de responsável (conta não-admin)
  sempre mostra `cliente.responsavel`, nunca o usuário autenticado —
  `TestClientesEscopoSomenteSeus.test_editar_get_exibe_responsavel_real_do_cliente`;
  em criação, mostra `request.user` —
  `TestClientesEscopoSomenteSeus.test_novo_get_exibe_o_proprio_usuario_como_responsavel`;
- [x] um usuário não administrador com nível máximo `todos` visualiza
  (`lista`/`detalhe`) qualquer cliente do tenant, mas só edita/desativa/
  reativa clientes de sua própria responsabilidade — cliente alheio em
  `editar`/`desativar`/`reativar` retorna 404 mesmo com nível `todos` —
  `TestClientesEscopoTodos.test_detalhe_alheio_funciona_com_nivel_todos`,
  `test_editar_alheio_retorna_404_mesmo_com_nivel_todos`,
  `test_desativar_alheio_retorna_404_mesmo_com_nivel_todos`,
  `test_reativar_alheio_retorna_404_mesmo_com_nivel_todos`,
  `test_editar_proprio_funciona_com_nivel_todos`.

## Testes esperados

### Existentes a considerar

- `apps/clientes/tests/test_autorizacao.py` (26 testes, WI-0001) — a
  fixture `_cliente()` cria `Cliente` sem `responsavel`; como o campo
  passa a ser obrigatório, essa fixture precisa passar `responsavel`
  explicitamente (por exemplo, `responsavel=self.user`) em cada
  chamada, preservando o comportamento coberto por esses testes sem
  alterar suas asserções de autorização de módulo/habilitação.
- `apps/accounts/tests/` — não são alterados; regressão relevante
  porque `nivel_acesso_modulo()`/`usuario_admin_escritorio()` (já
  cobertos extensivamente lá) passam a ser consumidos por
  `apps/clientes/views.py`.

### Novos testes

Cobrindo, no mínimo, os 20 cenários automatizados listados no escopo
aprovado deste item (ver "Critérios de aceite" acima para a versão
verificável): listagem por `somente_seus`/`todos`/admin; detalhe/editar/
desativar/reativar próprio e alheio (404 para alheio); inativos com
escopo; criação com `responsavel` forçado para conta limitada e POST
adulterado sem efeito; reatribuição pelo Administrador; rejeição de
usuário inativo como responsável; ausência de `Cliente` sem
`responsavel`; 403 para escalonamento de escopo (`todos` acima do
máximo, `da_equipe` para qualquer usuário); seletor do Administrador
funcional; "Da equipe" sem efeito funcional.

Testes cross-tenant: não incluídos como teste automatizado novo neste
item — o padrão de fixture de `TenantTestCase` já usado em
`apps/clientes/tests/test_autorizacao.py` cria um schema isolado por
classe de teste, sem criar dois tenants na mesma execução; a garantia de
isolamento cross-tenant para a lista de usuários selecionáveis
(`responsavel`) decorre da arquitetura de schema (`django.contrib.auth`
em `TENANT_APPS`), já coberta estruturalmente por
`architecture/multitenancy.md`, e não é reexercitada por um teste
cross-tenant dedicado neste item — ampliar a estrutura de teste para
criar dois tenants na mesma execução ampliaria desnecessariamente o
escopo deste item, conforme "Adicionar testes cross-tenant se... a
estrutura atual permitir fazê-los sem ampliar desnecessariamente o WI"
na instrução original.

### Comandos de validação

```text
python manage.py test apps.clientes.tests.test_escopo
python manage.py test apps.clientes
python manage.py test apps.accounts
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

### Validação manual

Aplicável: SIM.

Cenários previstos:

1. Conta limitada com escopo "Somente os seus" → vê apenas seus
   clientes na listagem.
2. Conta limitada tenta URL direta de um cliente de outro responsável
   (`/clientes/<pk>/`) → 404.
3. Administrador → vê todos os clientes; muda para "Somente os seus"
   (`?escopo=somente_seus`) → vê apenas os próprios.
4. Conta limitada cria cliente → campo "Responsável" aparece preenchido
   com o próprio usuário e não pode ser alterado.
5. Administrador edita um cliente → consegue pesquisar um usuário ativo
   do escritório pelo nome e reatribuir o responsável.

Resultado real:

VALIDAÇÃO MANUAL DO PRODUCT OWNER — APROVADA

- Somente os seus: OK
- Limitado com Todos: OK
- Admin: OK
- Criação limitado: OK
- Reatribuição Admin: OK

Data: 2026-08-18

## Quality gates

- [x] testes alvo executados (`apps.clientes.tests.test_escopo`) — 23
  testes, `OK`
- [x] testes negativos executados (escopo, IDOR, escalonamento, POST
  adulterado) — inclusos nos 23 testes acima
- [x] suíte relevante executada (`apps.clientes`, `apps.accounts`) — 49 +
  86 = 135 testes, `OK`
- [x] `python manage.py check` — "System check identified no issues (0
  silenced)"
- [x] `python manage.py makemigrations --check --dry-run` — "No changes
  detected"
- [x] `git diff --check` — aprovado, sem saída
- [x] `npm run build` (Tailwind) — executado; a regeneração completa
  removeria 100+ classes usadas por outros módulos não relacionados a
  este WI (drift pré-existente de `static/css/output.css` em relação ao
  HEAD atual, não introduzido por este item — ver "Achados fora do
  escopo"); revertida e substituída por um patch manual mínimo (13
  linhas adicionadas, 0 removidas) contendo exatamente as 4 classes
  Tailwind novas usadas pelos templates deste WI
  (`.accent-gray-400`, `.opacity-50`, `.hover\:bg-gray-200:hover`;
  `.py-1\.5` já existia), cada uma verificada individualmente contra o
  formato gerado por classes irmãs já presentes no arquivo
- [x] diff revisado integralmente, manualmente
- [x] resultado comparado com os critérios de aceite deste item

## Atualizações documentais esperadas

`docs/delivery/current-state.md` foi atualizado no fechamento deste
item, após a validação manual do Product Owner: a subseção "Clientes"
passa a refletir que escopo de dados por responsável está aplicado,
distinguindo escopo de leitura (`todos`/`somente_seus`) de autorização
de mutação por responsabilidade — o que antes não refletia. Esta
atualização foi feita no commit documental (H2), separado do commit de
implementação (H1). `docs/delivery/roadmap.md` não foi atualizado por
este item — a regra de progressão módulo a módulo já cobre este caso
sem exigir edição.

## Achados fora do escopo

- **`static/css/output.css` está desatualizado em relação aos templates
  atuais do HEAD, independentemente deste WI.** Evidência: executar
  `npm run build` (o comando de build Tailwind já catalogado em
  `docs/development/quality-gates.md#gate-frontend--tailwind`) nesta
  sessão produziu um diff de 57 inserções e 107 remoções — a maior parte
  das remoções são classes que não aparecem em nenhum template ou
  arquivo `.js` atual (por exemplo, `.grid-cols-7`, `.line-clamp-2`,
  `.resize-none`, `.h-64`, `.h-24`, `.h-11`, `.max-h-\[calc\(100vh-8rem\)\]`,
  `.absolute`, `.right-1`, `.top-1`), sem relação com as alterações
  deste WI. Uma hipótese observada, não confirmada como causa única: o
  arquivo de configuração `tailwind.config.js` define `content` apenas
  sobre `templates/**/*.html`, `apps/**/*.html` e `static/js/**/*.js` —
  não sobre arquivos `.py` — então uma classe usada apenas como atributo
  de widget em um `forms.py` (por exemplo, `resize-none` em
  `apps/clientes/forms.py` deste próprio módulo, ou padrão semelhante em
  outros apps) nunca é reconhecida pelo build do Tailwind, mesmo que
  apareça de fato no HTML renderizado em produção. Impacto: um
  `npm run build` completo, se executado sem cautela em qualquer Work
  Item futuro que precise dele, pode remover silenciosamente estilo
  visual usado por outros módulos não relacionados ao item em execução.
  Nesta sessão, o gate de Tailwind foi satisfeito com um patch manual
  mínimo (ver "Quality gates"), evitando esse efeito colateral, mas o
  desalinhamento em si não foi corrigido. Destino provável: item futuro
  de manutenção de frontend/build, ou ajuste do `content` de
  `tailwind.config.js` para também escanear os arquivos `.py` que
  definem `widgets` com classes Tailwind — decisão fora do escopo deste
  WI de Clientes.

## Evidência de execução

### Estado inicial

Branch: `docs/reorganizacao-harness`

HEAD: `26ba2ec` — "docs: permitir avanço das fases por módulo"

Git status: limpo (working tree e staged), reconfirmado por `git
branch --show-current`, `git log -1 --oneline`, `git status --short`,
`git status -sb` imediatamente antes desta preparação.

### Arquivos alterados

Modificados:

- `apps/clientes/models.py`
- `apps/clientes/forms.py`
- `apps/clientes/views.py`
- `apps/clientes/tests/test_autorizacao.py`
- `templates/clientes/lista.html`
- `templates/clientes/inativos.html`
- `templates/clientes/form.html`
- `templates/configuracoes/permissoes.html`
- `static/css/output.css` (patch manual mínimo, 13 linhas adicionadas,
  0 removidas — ver "Quality gates")

Criados:

- `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
- `apps/clientes/tests/test_escopo.py`
- `docs/delivery/work/WI-0002-escopo-responsabilidade-clientes.md` (este
  arquivo)

Confirmado por `git status --short` ao final da implementação: nenhum
arquivo fora desta lista foi alterado ou criado.

### Testes executados

```text
python manage.py test apps.clientes.tests.test_escopo -v 2
→ 23 testes
→ OK

python manage.py test apps.clientes -v 2
→ 49 testes (26 do WI-0001 + 23 novos)
→ OK

python manage.py test apps.accounts -v 1
→ 86 testes
→ OK

python manage.py test apps.clientes apps.accounts -v 1 --noinput
→ 135 testes
→ OK
```

### Validações executadas

```text
python manage.py check
→ System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
→ No changes detected

git diff --check (após cada etapa relevante)
→ aprovado, sem saída

npm run build
→ executado; diff completo revertido por conter remoções fora de
  escopo (ver "Achados fora do escopo"); substituído por patch manual
  de 4 classes Tailwind, cada uma conferida contra classes irmãs já
  presentes no arquivo antes de ser aceita

Contagem de Cliente.responsavel IS NULL no banco de desenvolvimento
(schema demo, via django_tenants.utils.schema_context)
→ 0 (antes e depois da migration, ver "Evidência do estado atual")
```

### Resultado

Implementação concluída e revisada. Critérios de aceite verificados com
evidência de teste automatizado (ver "Critérios de aceite"). Revisão
técnica independente (Codex) encontrou dois achados e uma implicação de
produto correlata, todos corrigidos antes do commit de implementação —
ver "Correção pós-review" abaixo. Validação manual do Product Owner
**aprovada** em 2026-08-18 (ver "Validação manual"). O item está
`done`.

### Correção pós-review

Review técnico independente (Codex) encontrou dois achados e solicitou
auditoria de uma implicação de produto relacionada, todos corrigidos
nesta mesma sessão, antes de qualquer commit:

1. **`?escopo=` vazio tratado como ausente.** `_resolver_escopo()`
   usava `if not solicitado` (verdadeiro tanto para `None` quanto para
   `""`), permitindo que `?escopo=` (presente, vazio) recebesse
   silenciosamente o escopo padrão em vez de ser negado. Corrigido para
   `if solicitado is None`, distinguindo parâmetro ausente (usa padrão)
   de parâmetro presente e inválido (nega, 403). Teste adicionado:
   `test_escopo_vazio_retorna_403`.
2. **Responsável exibido incorretamente na edição.** `templates/clientes/form.html`
   sempre exibia `usuario_atual` (o editor) no campo somente leitura de
   responsável para conta não administrador, inclusive em `editar` — quando
   o cliente pertencesse a outro responsável, a tela mostrava o próprio
   editor, não o responsável real. Corrigido: `views.py::novo` passa
   `responsavel_exibido = request.user`; `views.py::editar` passa
   `responsavel_exibido = cliente.responsavel`; o template usa
   `responsavel_exibido` em vez de `usuario_atual`. Testes adicionados:
   `test_editar_get_exibe_responsavel_real_do_cliente`,
   `test_novo_get_exibe_o_proprio_usuario_como_responsavel`.
3. **Auditoria solicitada — leitura versus mutação.** Confirmado que
   `editar`/`desativar`/`reativar` usavam `_clientes_no_escopo()`, o
   mesmo `QuerySet` de leitura — quando o escopo efetivo de um usuário
   não administrador era `todos` (seu próprio nível máximo, sem precisar
   de nenhum parâmetro manipulado), essas três rotas carregavam
   **qualquer** cliente do tenant para mutação, não apenas os de sua
   responsabilidade. Isso violava a regra já aprovada do WI de que
   "todos" é alcance de **visualização**, não autorização de **mutação**.
   Corrigido com um `QuerySet` de mutação dedicado (`_clientes_mutaveis`),
   usado exclusivamente por `editar`/`desativar`/`reativar`, restrito a
   Administrador do escritório ou a `Cliente.responsavel ==
   request.user` — independente do parâmetro `escopo` da requisição.
   `lista`/`detalhe`/`inativos` não foram alterados (continuam usando o
   escopo de leitura, corretamente, incluindo `detalhe` de cliente
   alheio quando o nível máximo é `todos`). Testes adicionados em
   `TestClientesEscopoTodos`:
   `test_detalhe_alheio_funciona_com_nivel_todos`,
   `test_editar_alheio_retorna_404_mesmo_com_nivel_todos`,
   `test_desativar_alheio_retorna_404_mesmo_com_nivel_todos`,
   `test_reativar_alheio_retorna_404_mesmo_com_nivel_todos`,
   `test_editar_proprio_funciona_com_nivel_todos` (habilitação
   `clientes_editar` e um cliente alheio inativo adicionados à fixture
   desta classe).

Arquivos alterados neste delta: `apps/clientes/views.py`,
`templates/clientes/form.html`, `apps/clientes/tests/test_escopo.py`,
este próprio Work Item (seções "Escopo de dados", "Autorização sobre
objeto", "Seletor de escopo — mecanismo técnico", "Critérios de
aceite"). Nenhum outro arquivo do WI foi tocado por esta correção.

Testes após a correção:

```text
python manage.py test apps.clientes.tests.test_escopo -v 2 --noinput
→ 31 testes (23 anteriores + 8 novos desta correção)
→ OK

python manage.py test apps.clientes -v 1 --noinput
→ 57 testes (26 do WI-0001 + 31 de test_escopo.py)
→ OK

python manage.py test apps.accounts -v 1 --noinput
→ 86 testes
→ OK

python manage.py check
→ System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
→ No changes detected

git diff --check
→ aprovado, sem saída
```

Self-review desta sessão: limitado ao delta da correção (os três itens
acima) e à regra de leitura versus mutação, conforme instrução da
sessão — não uma reauditoria geral do WI. Diff revisado integralmente
(`git diff apps/clientes/views.py templates/clientes/form.html`), sem
alteração fora do escopo desta correção.

### Commit

Commit de implementação (H1): `07675f7` — "feat(clientes): aplicar
escopo e responsabilidade". Contém exatamente os arquivos listados em
"Arquivos alterados" acima (código, testes, migration e este próprio
Work Item, no estado em que se encontrava até a aprovação técnica e
manual).

Commit documental de encerramento (H2): registrado após este commit
existir — ver `docs/delivery/current-state.md` para a atualização de
estado correspondente; o hash de H2 não é referenciado aqui porque este
arquivo é modificado pelo próprio H2.

## Encerramento

- [x] critérios de aceite verificados;
- [x] testes/validações registrados;
- [x] diff revisado;
- [x] escopo respeitado;
- [x] current-state atualizado — módulo Clientes passa a refletir escopo
  de dados aplicado, distinção leitura/mutação e responsabilidade
  obrigatória;
- [x] roadmap atualizado somente se necessário — não foi necessário,
  não foi alterado: a regra de progressão módulo a módulo já presente em
  `docs/delivery/roadmap.md` já cobre a conclusão da Fase B de Clientes
  sem exigir edição;
- [x] achados laterais registrados — ver "Achados fora do escopo"
  (drift de `static/css/output.css`);
- [x] Git final registrado — commit de implementação (H1) `07675f7`;
  commit documental (H2) registrado em `docs/delivery/current-state.md`,
  não autorreferenciado neste arquivo antes de existir.
