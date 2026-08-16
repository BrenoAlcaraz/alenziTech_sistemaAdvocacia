---
title: WI-0001 — Autorização backend de Clientes
status: canonical
owner: delivery
last_reviewed: 2026-08-16
---

# WI-0001 — Autorização backend de Clientes

## Estado

done

## Fase do roadmap

Fase: Fase A — Consolidar autorização nas operações

Objetivo relacionado: aplicar autorização de módulo nas views operacionais
e aplicar as habilitações já existentes no kernel, conforme
[roadmap.md](../roadmap.md#fase-a--consolidar-autorização-nas-operações).

## Objetivo

Aplicar enforcement de autorização backend ao módulo Clientes usando o
kernel já existente (`apps/accounts/permissoes.py`), sem implementar
escopo de dados. Toda operação backend existente de Clientes deve exigir
autorização do módulo `clientes` resolvida por `tem_permissao_modulo()`,
além de autenticação; as operações que já possuem uma habilitação
correspondente no kernel atual (`clientes_criar`, `clientes_editar`)
devem também exigir essa habilitação via `tem_habilitacao()`.

## Contexto e motivação

[current-state.md](../current-state.md#accounts-e-autorização) e
[../security/overview.md](../../security/overview.md#principais-lacunas-constatadas)
registram que o kernel dinâmico de permissões e habilitações existe e é
coberto por testes extensivos em `apps/accounts/tests/`, mas nenhuma
view operacional fora de `apps/accounts`/`apps/configuracoes` o
consulta. `apps/clientes/views.py` é um dos módulos citados
explicitamente nessa lacuna. Este item é a primeira unidade de trabalho
da Fase A, conforme
[roadmap.md](../roadmap.md#próxima-unidade-de-trabalho): "a próxima
unidade de trabalho deve pertencer à Fase A — Consolidar autorização
nas operações".

## Evidência do estado atual

- Comportamento existente: as sete views de
  `apps/clientes/views.py` (`lista`, `detalhe`, `novo`, `editar`,
  `desativar`, `inativos`, `reativar`) usam exclusivamente
  `@login_required`. Nenhuma chamada a `tem_permissao_modulo()` ou
  `tem_habilitacao()` foi encontrada neste arquivo, reconfirmado pela
  leitura direta do HEAD nesta preparação.
- Lacuna constatada: [../security/authorization-matrix.md](../../security/authorization-matrix.md#clientes)
  classifica todas as sete operações de Clientes como "Lacuna
  constatada" — autorização de módulo esperada, mas não aplicada.
- Cobertura de teste ausente: nenhum arquivo de teste existe em
  `apps/clientes/` (`find apps -type f \( -name "test_*.py" -o -name
  "tests.py" \)` retorna apenas os três arquivos de
  `apps/accounts/tests/`).
- Operação planejada: [roadmap.md](../roadmap.md#fase-a--consolidar-autorização-nas-operações)
  define, como pré-requisito de saída da Fase A, que "operações
  sensíveis (criar, editar, arquivar, excluir, marcar como pago,
  reatribuir, adicionar participante) consultam o kernel adequado".

## Resultado esperado

Todas as sete rotas existentes de Clientes passam a negar acesso no
backend a um usuário autenticado sem autorização de módulo `clientes`;
criação e edição passam também a negar acesso a um usuário com módulo
autorizado mas sem a habilitação `clientes_criar`/`clientes_editar`
correspondente. Nenhuma mutação ocorre quando a autorização é negada.
Este resultado não implica que a autorização de Clientes esteja
completa — escopo de dados por responsável permanece pendente, ver
"Fora de escopo".

## Fontes canônicas

- [../../security/overview.md](../../security/overview.md)
- [../../security/authorization-model.md](../../security/authorization-model.md)
- [../../security/data-scope.md](../../security/data-scope.md)
- [../../security/authorization-matrix.md](../../security/authorization-matrix.md#clientes)
- [../../product/modules/clientes.md](../../product/modules/clientes.md)
- [../../product/open-decisions.md](../../product/open-decisions.md)
- [../../architecture/overview.md](../../architecture/overview.md)
- [../../architecture/multitenancy.md](../../architecture/multitenancy.md)
- [../current-state.md](../current-state.md)
- [../roadmap.md](../roadmap.md)

## Arquivos do HEAD a auditar antes da implementação

- `apps/clientes/models.py`
- `apps/clientes/views.py`
- `apps/clientes/forms.py`
- `apps/clientes/urls.py`
- `apps/clientes/admin.py`
- `apps/accounts/models.py`
- `apps/accounts/permissoes.py`
- `apps/accounts/permissoes_constants.py`
- `apps/accounts/decorators.py`
- `apps/accounts/escopo.py`
- `templates/clientes/lista.html`
- `templates/clientes/detalhe.html`
- `templates/clientes/form.html`
- `templates/clientes/inativos.html`
- `apps/accounts/tests/test_permissoes_kernel.py`
- `apps/accounts/tests/test_interacoes_kernel.py`
- `apps/accounts/tests/test_admin_tenant.py`

A evidência acima foi reconfirmada no HEAD nesta preparação do item; a
implementação futura deve reconfirmá-la novamente antes de alterar
qualquer arquivo, conforme o protocolo de work items.

## Escopo permitido

### Pode alterar

- `apps/clientes/views.py` — adicionar as verificações de autorização
  de módulo e habilitação descritas em "Regras funcionais e técnicas".
  Nenhuma outra mudança de comportamento é autorizada neste arquivo.
- `docs/delivery/current-state.md` — apenas ao final da implementação,
  e apenas se o estado material tiver mudado (ver "Atualizações
  documentais esperadas").

### Pode criar

- `apps/clientes/tests/__init__.py`
- `apps/clientes/tests/test_autorizacao.py`

Esta estrutura (`apps/clientes/tests/`) não existe hoje —
`apps/clientes/` não possui nenhum arquivo de teste, conforme "Evidência
do estado atual". Se, no momento da implementação, o HEAD já tiver
adotado um padrão diferente (por exemplo, `apps/clientes/tests.py`), a
implementação deve seguir o padrão real do repositório naquele momento
e registrar a divergência em vez de impor esta estrutura.

### Migrations

Proibidas. Este Work Item não altera schema. Se a implementação
concluir que uma migration é necessária para cumprir este item, a
implementação deve parar e registrar achado fora do escopo em vez de
criar a migration.

### Documentação

- `docs/delivery/current-state.md`, somente ao final e somente se o
  estado material tiver mudado.

Nenhuma outra documentação pode ser alterada por este item, incluindo
`docs/delivery/roadmap.md`, `docs/delivery/work/README.md`,
`docs/delivery/work/template.md`, PDRs, ADRs, e qualquer arquivo de
instrução de agente ou de configuração do repositório fora de
`docs/delivery/`.

## Fora de escopo

> qualquer alteração útil, mas não necessária para satisfazer os
> critérios deste item, permanece fora do escopo até ser explicitamente
> incorporada.

- `apps/accounts/permissoes.py`, `apps/accounts/models.py`,
  `apps/accounts/permissoes_constants.py`, `apps/accounts/decorators.py`
  e `apps/accounts/escopo.py` são fontes a auditar, não alvo de
  alteração. Se a implementação concluir que o kernel precisa mudar
  para cumprir este item, a implementação deve parar e registrar um
  achado fora do escopo em vez de ampliar o item.
- `apps/clientes/models.py`, `apps/clientes/forms.py`,
  `apps/clientes/urls.py` e `templates/clientes/` não devem ser
  alterados por este item — ver "Templates / UI e camada de
  apresentação".
- `config/` não deve ser alterado por este item.
- Escopo de dados por `Cliente.responsavel`, por equipe, `nivel`
  (`somente_seus`/`todos`) tratado como filtro de `QuerySet`,
  autorização sobre objeto (IDOR intra-tenant) e qualquer proteção
  equivalente pertencem à **Fase B — Aplicar escopo de dados**, não a
  este item. A conclusão deste WI melhora a autorização de
  módulo/habilitação de Clientes, mas **não torna a autorização de
  Clientes completa** enquanto o escopo por objeto não for aplicado:
  `get_object_or_404(Cliente, pk=pk, ...)` continuará, após este item,
  carregando qualquer cliente ativo (ou inativo, em `reativar`) do
  tenant, sem condição de posse — este item não resolve IDOR
  intra-tenant e não deve ser reportado como tendo resolvido.
- Nenhuma habilitação nova para o módulo `clientes` — para visualizar,
  desativar, reativar, excluir ou qualquer outra ação não coberta hoje
  por `ITENS_POR_MODULO["clientes"]` — pode ser criada por este item —
  ver "Desativar, reativar e listar inativos" em "Regras funcionais e
  técnicas".
- `nivel` (`somente_seus`/`todos`) não deve ser lido, filtrado ou
  reinterpretado como autorização de ação por este item.

## Regras funcionais e técnicas

### Camada 1 — autorização de módulo (todas as sete rotas)

Cada uma das sete views de `apps/clientes/views.py` deve, além de
`@login_required`, negar acesso quando
`tem_permissao_modulo(request.user, "clientes")` for falso:

- `lista`
- `detalhe`
- `novo`
- `editar`
- `desativar`
- `inativos`
- `reativar`

O simples fato de estar autenticado não é suficiente, conforme
[../../security/overview.md](../../security/overview.md#princípios-canônicos)
("backend como autoridade").

### Camada 2 — habilitação funcional (apenas onde já existe no kernel)

- `novo` deve negar acesso quando
  `tem_habilitacao(request.user, "clientes", "clientes_criar")` for
  falso, além da autorização de módulo da Camada 1.
- `editar` deve negar acesso quando
  `tem_habilitacao(request.user, "clientes", "clientes_editar")` for
  falso, além da autorização de módulo da Camada 1.

Nenhuma outra operação de Clientes recebe checagem de habilitação neste
item — ver a subseção seguinte.

### Desativar, reativar e listar inativos

[../../security/authorization-matrix.md](../../security/authorization-matrix.md#clientes)
classifica "Desativar", "Listar inativos" e "Reativar" com
"Habilitação: Sem habilitação específica no kernel atual" e observação
"Candidata a habilitação futura" — a matriz não vincula essas operações
a `clientes_editar` nem a nenhuma outra habilitação existente. Este
Work Item, portanto:

- exige apenas a autorização de módulo (Camada 1) para `desativar`,
  `inativos` e `reativar`;
- não associa essas operações a `clientes_editar` por analogia;
- não cria uma habilitação nova para elas;
- não declara que qualquer usuário com acesso ao módulo `clientes`
  poderá, permanentemente, desativar e reativar clientes — apenas que,
  ao final deste item, essas operações passam a exigir pelo menos
  autorização de módulo, o que hoje elas não exigem. A autorização de
  ação específica para desativar/reativar permanece uma lacuna a tratar
  em Work Item futuro da Fase A, conforme "Achados fora do escopo".

### `nivel` (nível de acesso técnico atual)

`NIVEIS_POR_MODULO["clientes"]` (`somente_seus`, `todos`) não é lido,
filtrado ou usado como condição de autorização por este item. A
implementação não deve chamar `nivel_acesso_modulo()` para decidir
liberar ou negar uma operação de Clientes. Este item reconhece que
`nivel` será relevante para o escopo de dados em fase posterior, sem
decidir sua implementação aqui, conforme
[../../security/data-scope.md](../../security/data-scope.md#escopo-constatado-no-código).

### Administrador do escritório

`tem_permissao_modulo()` e `tem_habilitacao()` já avaliam
`usuario_admin_escritorio()` internamente, antes de qualquer
`PermissaoUsuario`/`PermissaoPapel`, concedendo acesso total ao módulo
no maior nível configurado, conforme
[../../security/authorization-model.md](../../security/authorization-model.md#precedência-constatada).
A implementação deve chamar apenas `tem_permissao_modulo()`/
`tem_habilitacao()` nas views de Clientes e não deve reproduzir uma
checagem manual e paralela de `is_admin_escritorio` ou de
`usuario_admin_escritorio()` dentro de `apps/clientes/views.py`. Este
item não trata administrador do escritório como acesso irrestrito
canônico a todo objeto jurídico — o bypass constatado é apenas de
autorização de módulo/habilitação, não de escopo de objeto (Fase B).

### Resposta de negação

Nenhuma convenção de projeto foi encontrada em
`apps/accounts/decorators.py` (ou em qualquer outro arquivo do HEAD)
para resposta HTTP de negação de autorização de módulo/habilitação
fora do decorator `@requer_admin_escritorio`, que usa `raise
PermissionDenied` para um usuário autenticado sem privilégio
administrativo. Não foi encontrado `handler403` customizado em
`config/urls.py`, nem um template `403.html` em `templates/`. A
implementação deve adotar uma resposta HTTP de negação consistente e
testável em todas as sete views (por exemplo, `raise PermissionDenied`,
reaproveitando o padrão já observado em
`apps/accounts/decorators.py::requer_admin_escritorio`, que resulta na
view padrão de erro 403 do Django), sem inventar texto, redirect ou UX
de produto para a página de erro. Este item não é bloqueado pela
ausência de uma página 403 customizada — apenas exige que:

- a negação ocorra no backend;
- nenhuma mutação seja executada quando negado;
- nenhum acesso ao comportamento protegido ocorra quando negado.

## Segurança e autorização

- Backend como autoridade: as verificações desta Camada 1/Camada 2
  devem ocorrer nas views de `apps/clientes/views.py`, antes de
  qualquer leitura ou mutação de `Cliente`, independentemente do que a
  interface exiba.
- Este item não aplica escopo de dados — ver "Fora de escopo". Um
  usuário autorizado ao módulo `clientes` (e, quando aplicável, à
  habilitação) continuará, após este item, alcançando qualquer cliente
  do tenant por `pk`, não apenas os de sua responsabilidade.
- Nenhuma resposta deste item amplia o escopo que o usuário já teria
  diretamente, conforme
  [../../security/overview.md](../../security/overview.md#princípios-canônicos).

## Decisões abertas e bloqueios

Nenhuma decisão em aberto (`OPEN-001`, `OPEN-002`) afeta este item —
ambas pertencem exclusivamente ao módulo Financeiro, conforme
[../../product/open-decisions.md](../../product/open-decisions.md).
Nenhum bloqueio foi identificado para o escopo delimitado deste item:
a autorização de módulo está suficientemente definida pelo kernel
constatado, e `clientes_criar`/`clientes_editar` têm semântica
suficiente para a parte incluída (criação e edição). O tratamento de
desativar/reativar/listar inativos como "somente autorização de
módulo" não depende de nenhuma decisão em aberto — é a consequência
direta de a matriz canônica não vincular essas operações a nenhuma
habilitação existente.

## Dependências

- Depende apenas do kernel de autorização já implementado em
  `apps/accounts/permissoes.py` (`tem_permissao_modulo()`,
  `tem_habilitacao()`), que este item não altera.
- Não depende de nenhum outro Work Item, por ser o primeiro item criado
  no repositório.
- Não pode ser executado em paralelo com outro Work Item que também
  altere `apps/clientes/views.py`, para evitar conflito de escopo no
  mesmo arquivo.

## Critérios de aceite

- [x] toda rota backend existente de Clientes (`lista`, `detalhe`,
  `novo`, `editar`, `desativar`, `inativos`, `reativar`) exige
  autorização do módulo `clientes` via `tem_permissao_modulo()` —
  confirmado em `apps/clientes/views.py` (commit `da19001`) e por
  `TestClientesAutorizacaoModuloNegado`/`...ModuloConcedido` em
  `apps/clientes/tests/test_autorizacao.py`;
- [x] criação (`novo`) exige a habilitação existente `clientes_criar`
  via `tem_habilitacao()` — confirmado em `views.py::novo` e por
  `TestClientesAutorizacaoHabilitacaoCriarAusente`;
- [x] edição (`editar`) exige a habilitação existente `clientes_editar`
  via `tem_habilitacao()` — confirmado em `views.py::editar` e por
  `TestClientesAutorizacaoHabilitacaoEditarAusente`;
- [x] nenhuma habilitação nova foi criada — `apps/accounts/permissoes_constants.py`
  não foi alterado; apenas `HAB_CLIENTES_CRIAR`/`HAB_CLIENTES_EDITAR`,
  já existentes, foram consumidas;
- [x] `nivel` não foi lido nem reinterpretado como autorização de ação
  — `nivel_acesso_modulo()` não é chamado em `apps/clientes/views.py`;
- [x] negação ocorre no backend antes de qualquer leitura ou mutação de
  `Cliente` — `raise PermissionDenied` é a primeira instrução após
  `@login_required` em cada view, antes de `get_object_or_404`/`.save()`;
- [x] operações negadas não alteram nenhum registro de `Cliente` —
  comprovado por `Cliente.objects.count()`/`refresh_from_db()` nos
  testes negativos de módulo e de habilitação;
- [x] um usuário autorizado (módulo + habilitação, quando aplicável)
  continua alcançando os sete fluxos existentes normalmente —
  comprovado por `TestClientesAutorizacaoModuloConcedido` (11 testes);
- [x] testes negativos do enforcement de módulo existem para as sete
  rotas — `TestClientesAutorizacaoModuloNegado` (11 testes);
- [x] testes negativos do enforcement de habilitação existem para
  `novo` e `editar` — `TestClientesAutorizacaoHabilitacaoCriarAusente`/
  `...EditarAusente` (4 testes);
- [x] escopo de dados (por `responsavel`, IDOR intra-tenant) não foi
  tratado como resolvido por este item — preservado como lacuna em
  "Fora de escopo" deste WI e em `current-state.md`; achado adicional
  registrado em "Achados fora do escopo";
- [x] nenhuma migration foi criada — `python manage.py makemigrations
  --check --dry-run` → "No changes detected";
- [x] nenhum arquivo fora do escopo permitido foi modificado — commit
  `da19001` contém exatamente `apps/clientes/views.py`,
  `apps/clientes/tests/__init__.py`,
  `apps/clientes/tests/test_autorizacao.py`; esta etapa de encerramento
  altera apenas `docs/delivery/current-state.md` e este próprio WI;
- [x] `docs/delivery/current-state.md` foi atualizado ao final se, e
  somente se, o estado material descrito nele tiver mudado — atualizado
  nesta etapa, pois as views de Clientes passaram a consultar o kernel
  de autorização;
- [x] evidência de Git final foi registrada na seção "Evidência de
  execução" deste item.

## Testes esperados

### Existentes a considerar

- `apps/accounts/tests/test_permissoes_kernel.py` e
  `apps/accounts/tests/test_interacoes_kernel.py` cobrem
  `permissao_efetiva()`/`habilitacao_efetiva()` e os helpers
  `tem_permissao_modulo()`/`tem_habilitacao()` que este item passa a
  consumir em `apps/clientes/views.py` — não precisam ser alterados,
  mas a suíte relevante de `apps.accounts` deve ser executada como
  regressão, pois uma view nova consumidora do kernel pode expor uma
  regressão não coberta antes.
- `apps/accounts/tests/test_admin_tenant.py` cobre a resolução de
  administrador do escritório (`usuario_admin_escritorio()`,
  `requer_admin_escritorio` e `tipo_conta_usuario()`), caminho que
  `tem_permissao_modulo()`/`tem_habilitacao()` já avaliam internamente
  antes deste item existir. A leitura integral deste arquivo nesta
  preparação confirma uma divergência: vários testes marcados
  `assertFuturo`/`FALHA_ESPERADA` (por exemplo,
  `test_superuser_sem_flag_nao_e_tenant_admin`,
  `test_usuario_inativo_com_flag_nao_e_tenant_admin`,
  `test_grupo_admin_sem_flag_nao_e_tenant_admin` e seus equivalentes em
  `TestRequerAdminEscritorio`) trazem comentários descrevendo um
  "kernel atual (pré-2.1C1B)" no qual `is_superuser`, o Group
  `administrador_escritorio` ou `is_admin_escritorio=True` sem checar
  `is_active` concederiam acesso de administrador. Isso não corresponde
  ao código efetivamente lido em
  `apps/accounts/decorators.py::usuario_admin_escritorio`, que já
  verifica exclusivamente `is_admin_escritorio=True` combinado com
  `is_active=True`, sem checar `is_superuser` nem Group. A comparação
  direta entre cada teste e esse código sugere que a maioria dos casos
  marcados `FALHA_ESPERADA` neste arquivo já não falharia sob o kernel
  atual — mas esta preparação não executa os testes e não afirma
  resultado de execução. A implementação futura deve tratar qualquer
  falha inesperada em `apps.accounts` como regressão real a investigar,
  não presumir que ela é "esperada" apenas porque um comentário do
  arquivo assim descreve.
- Os três arquivos usam `django_tenants.test.cases.TenantTestCase`
  com helpers próprios (`_user`, `_set_admin_flag`, `_new_papel`,
  `_assign_papel`, `_pp`, `_hp`) para criar `User`, `PerfilUsuario`,
  `PapelAcesso`, `UsuarioPapel`, `PermissaoPapel` e `HabilitacaoPapel`
  em teste — a implementação futura deve seguir o mesmo padrão de
  fixtures ao escrever `apps/clientes/tests/test_autorizacao.py`, em
  vez de inventar uma convenção nova.

### Novos testes

Testes automatizados novos para o módulo Clientes, cobrindo apenas o
enforcement do módulo e das duas habilitações existentes — não a suíte
completa do kernel.

**Autorização do módulo** — usuário autenticado sem acesso ao módulo
`clientes` (`tem_permissao_modulo` falso) não acessa/executa:

- listagem de clientes ativos (`lista`);
- detalhe de cliente (`detalhe`);
- criação (`novo`);
- edição (`editar`);
- desativação (`desativar`);
- listagem de inativos (`inativos`);
- reativação (`reativar`).

**Habilitação `clientes_criar`**:

- usuário com módulo `clientes`, mas sem `clientes_criar`, não cria
  cliente;
- usuário com módulo `clientes` e `clientes_criar` alcança o fluxo
  permitido de criação.

**Habilitação `clientes_editar`**:

- usuário com módulo `clientes`, mas sem `clientes_editar`, não edita
  cliente;
- usuário com módulo `clientes` e `clientes_editar` alcança o fluxo
  permitido de edição.

**Regressão mínima**:

- um usuário autorizado (módulo, e habilitação quando aplicável)
  continua alcançando os fluxos existentes de todas as sete rotas;
- uma tentativa negada não altera o objeto `Cliente` envolvido (por
  exemplo, `desativar`/`reativar` negados não mudam `Cliente.ativo`);
- a autorização é decidida no backend — um teste que envia `POST`
  diretamente à view, sem depender de a interface ocultar o botão,
  deve confirmar a negação.

**Não testar como resolvido neste item** (não incluir como critério de
sucesso de nenhum teste novo):

- cliente fora do escopo por `responsavel`;
- escopo por equipe;
- `somente_seus`/`todos` como filtro aplicado;
- IDOR intra-tenant final (um usuário autorizado ao módulo alcançando
  um cliente de outro responsável continua sendo o comportamento atual
  esperado até a Fase B, não uma falha deste item);
- isolamento cross-tenant completo.

### Comandos de validação

Confirmados como os comandos de teste do projeto pela leitura direta
dos três arquivos de `apps/accounts/tests/` (todos usam
`django_tenants.test.cases.TenantTestCase`, reconhecida pelo test
runner padrão do Django) e pela ausência de qualquer configuração de
`pytest` no repositório:

```text
python manage.py test apps.clientes
python manage.py test apps.accounts
```

A implementação futura deve executar, nesta ordem:

1. os testes novos deste item (`apps.clientes.tests.test_autorizacao`);
2. a suíte relevante de Clientes (`python manage.py test
   apps.clientes`);
3. os testes do kernel de Accounts relevantes para regressão (`python
   manage.py test apps.accounts`);
4. a suíte mais ampla do projeto apenas se algo além de
   `apps.clientes`/`apps.accounts` for tocado — não esperado pelo
   escopo deste item.

Nenhum teste foi executado neste lote de preparação. Não é permitido
registrar "testes passam" sem evidência de execução real.

## Quality gates

- [x] testes alvo executados (`apps.clientes.tests.test_autorizacao`)
- [x] testes negativos executados (módulo e habilitação)
- [x] suíte relevante executada (`apps.clientes`, `apps.accounts`)
- [x] `git diff --check`
- [x] `git status --short`
- [x] `git diff --name-status`
- [x] diff revisado integralmente, manualmente
- [x] resultado comparado com os critérios de aceite deste item

### Resultados registrados

```text
python manage.py test apps.clientes -v 2
→ 26 testes
→ OK

python manage.py test apps.accounts -v 2
→ 86 testes
→ OK

python manage.py check
→ System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
→ No changes detected

git diff --check (working tree e staged, em cada etapa)
→ aprovado, sem saída
```

## Templates / UI e camada de apresentação

Templates ficam fora de escopo neste item. Não é exigido, para
conclusão deste WI:

- esconder o botão "Novo cliente" (`templates/clientes/lista.html`);
- esconder "Editar" ou "Desativar" (`templates/clientes/detalhe.html`);
- esconder "Reativar" (`templates/clientes/inativos.html`);
- condicionar a sidebar (`templates/components/sidebar.html`) à
  autorização do módulo `clientes`;
- qualquer mensagem visual específica de acesso negado.

O backend é a autoridade de segurança; a UI pode ser alinhada
posteriormente, em item futuro, depois que o padrão de enforcement
backend estiver validado. Nesta leitura, `templates/clientes/lista.html`,
`templates/clientes/detalhe.html`, `templates/clientes/form.html` e
`templates/clientes/inativos.html` foram auditados apenas para
documentar o estado atual (todos os botões de ação são renderizados
incondicionalmente para qualquer usuário autenticado), não para
alteração neste item.

## Atualizações documentais esperadas

`docs/delivery/current-state.md` deve ser atualizado ao final da
implementação **somente se** o estado material mudar — por exemplo, se
a linha "Clientes" da tabela "Visão executiva" e a subseção "Clientes"
de "Estado por módulo" passarem a refletir que as views agora consultam
`tem_permissao_modulo()`/`tem_habilitacao()`, o que hoje elas não
fazem. Um ajuste cosmético não justifica, por si, essa atualização.
`docs/delivery/roadmap.md` não deve ser atualizado por este item — a
Fase A não se encerra com um único módulo autorizado.

## Achados fora do escopo

- **Desativar/reativar/listar inativos sem autorização de ação
  específica.** Evidência:
  [../../security/authorization-matrix.md](../../security/authorization-matrix.md#clientes)
  classifica essas três operações como "Candidata a habilitação
  futura", sem decisão aprovada. Impacto: após este item, qualquer
  usuário com acesso ao módulo `clientes` poderá desativar/reativar
  qualquer cliente do tenant, sem distinção de ação mais fina. Destino
  provável: novo Work Item da Fase A, condicionado a uma decisão
  explícita sobre criar (ou não) uma habilitação dedicada — não deve
  ser decidido silenciosamente dentro de um Work Item de execução.
- **Ausência de escopo de dados em Clientes.** Evidência:
  [../../security/data-scope.md](../../security/data-scope.md#aplicação-por-módulo)
  confirma que `Cliente.responsavel` existe no model, mas nenhuma view
  o usa como filtro. Impacto: um usuário autorizado ao módulo
  `clientes` continua alcançando qualquer cliente do tenant por `pk`,
  mesmo após este item. Destino provável: Fase B — Aplicar escopo de
  dados.
- **Busca de Clientes é apenas visual.** Evidência:
  `templates/clientes/lista.html` inclui
  `components/search_bar.html` com o comentário
  "Barra de busca visual — sem lógica real nesta fase"; `lista` não lê
  nenhum parâmetro de busca da URL. Impacto: nenhum, para autorização —
  registrado apenas como achado lateral já documentado em
  [current-state.md](../current-state.md#clientes). Destino provável:
  fora do escopo de segurança; eventual Work Item de produto/UX, não
  desta Fase.
- **Botões de ação sem condicionamento de permissão.** Evidência:
  "Novo cliente", "Editar", "Desativar" e "Reativar" são renderizados
  incondicionalmente em `templates/clientes/lista.html`,
  `templates/clientes/detalhe.html` e `templates/clientes/inativos.html`,
  independentemente de `tem_permissao_modulo`/`tem_habilitacao`.
  Impacto: um usuário sem autorização, após este item, ainda verá os
  botões, mas a ação backend será negada ao submeter o formulário
  correspondente — não é uma falha de segurança (backend já nega), mas
  é uma divergência entre interface e autorização real. Destino
  provável: item de UI em fase/rodada posterior, explicitamente fora
  deste WI conforme "Templates / UI e camada de apresentação".
- **Aba "Documentos" com contador fixo.** Evidência:
  `templates/clientes/detalhe.html` exibe "Documentos (2)" como texto
  fixo, sem relação com nenhum `QuerySet`, consistente com a ausência
  de `FileField` em `Cliente` já registrada em
  [current-state.md](../current-state.md#clientes). Impacto: nenhum
  para autorização deste item. Destino provável: infraestrutura de
  arquivos, fora do escopo de qualquer fase de autorização.
- **Escopo por responsável não restringe `lista`/`detalhe`/`editar`,
  mesmo com `nivel=somente_seus` configurado.** Evidência: teste manual
  do Product Owner antes do commit de implementação, com um usuário
  configurado com módulo `clientes` ativo e `nivel=somente_seus`,
  confirmou que `lista`, `detalhe` e `editar` continuam alcançando
  clientes de outros responsáveis — consistente com a leitura de
  código já registrada acima ("Ausência de escopo de dados em
  Clientes") e em
  [../../security/data-scope.md](../../security/data-scope.md#aplicação-por-módulo):
  `nivel` é resolvido pelo kernel, mas nenhuma view de Clientes o lê
  para filtrar `QuerySet`, conforme a regra deste item em "`nivel`
  (nível de acesso técnico atual)". Impacto: nenhum além do já
  registrado — não é regressão nem requisito não cumprido deste item.
  Classificação: fora do escopo do WI-0001; Fase B — escopo de dados;
  não é tratado como bug deste WI. Nota lateral: as equipes usadas
  nesse teste manual (algumas inativas) foram criadas pelo Product
  Owner para investigação exploratória; equipes não participam
  atualmente do escopo de Clientes, e a relação entre escopo
  individual e escopo por equipe permanece fora deste WI, sem
  requisito novo derivado daqui.
- **Tela "Permissões" não expõe habilitações
  (`HabilitacaoPapel`/`HabilitacaoUsuario`), incluindo
  `clientes_criar`/`clientes_editar`.** Evidência: leitura direta de
  `apps/configuracoes/views.py::permissoes` confirma que a view lê e
  grava exclusivamente `PermissaoPapel` por `tipo_conta` legado
  (`limitado`/`financeiro`) — `ativo` e `nivel` por módulo — sem
  nenhuma referência a `HabilitacaoPapel`/`HabilitacaoUsuario` em
  `apps/configuracoes` (busca por `Habilitacao` no diretório do app não
  retorna nenhum arquivo). Impacto: agora que este item aplica
  `tem_habilitacao()` em `novo`/`editar` de Clientes, um Administrador
  do escritório não possui, na interface de produto atual, nenhuma
  tela para conceder ou revogar `clientes_criar`/`clientes_editar` a um
  papel ou usuário. Hoje não existe interface de produto nem interface
  no Django Admin para conceder ou revogar essas habilitações —
  `PapelAcesso`, `UsuarioPapel`, `PermissaoPapel`, `PermissaoUsuario`,
  `HabilitacaoPapel` e `HabilitacaoUsuario` não estão registrados em
  nenhum `admin.py` do projeto. Alterações exigem um mecanismo técnico
  direto, como ORM/shell, migration de dados ou acesso direto ao banco.
  Não é falha de segurança (o backend nega por padrão na ausência de
  concessão), mas é uma lacuna operacional que só se torna visível
  depois deste item. Destino provável: item futuro de
  Configurações, relacionado à lacuna de administração de
  `PapelAcesso`/habilitações já registrada em
  [current-state.md](../current-state.md#configurações); nenhum Work
  Item específico é definido por este registro.

## Evidência de execução

Este Work Item foi preparado em um lote e implementado em lote(s)
posteriores. Esta seção preserva, distintamente, a evidência de
preparação (histórica, não sobrescrita) e a evidência real de
execução/implementação.

### Preparação (histórico)

Branch: `docs/reorganizacao-harness`

HEAD registrado na preparação: `5be0395` — "docs: definir protocolo de
work items"

Commit anterior: `68b0551` — "docs: registrar estado atual e roadmap de
entrega"

Git status no início desta preparação: um arquivo não rastreado, já
presente no diretório de trabalho antes do início desta preparação, sem
relação com o escopo deste item, e nenhum arquivo em staging.

Arquivos alterados neste lote de preparação: nenhum — o lote criou
apenas `docs/delivery/work/WI-0001-autorizacao-backend-clientes.md`.

Testes executados neste lote de preparação: nenhum.

Validações executadas neste lote de preparação: apenas leitura —
`git status --short`, `git diff --stat`, `git diff --stat --cached`,
`find docs/delivery/work -maxdepth 1 -type f`, e checagens de conteúdo
do arquivo criado (front matter, seção "Estado", habilitações citadas,
tratamento de `nivel`, tratamento de escopo, proibição de migrations,
ausência de referências indevidas, ausência de decisões em aberto não
sustentadas pelas fontes lidas).

Resultado deste lote: Work Item criado e pronto para execução futura
(`ready`). Nenhuma implementação de código, teste, migration ou
template ocorreu neste lote.

> A subseção acima é a evidência de preparação do item, distinta da
> evidência de execução/implementação real registrada abaixo.

### Execução (implementação)

Branch: `docs/reorganizacao-harness`.

HEAD inicial da execução: `ff0cf88` — "docs: concluir reorganizacao
documental" — reconfirmado por preflight de Git (`git branch
--show-current`, `git log -1 --oneline`, `git status --short`, `git
status -sb`) imediatamente antes de iniciar a Camada 1, com working
tree limpo. Distinto do HEAD registrado na preparação (`5be0395`);
entre `5be0395` e `ff0cf88` houve apenas commits `docs:` de
reorganização documental, sem alteração de código funcional.

Commit de implementação: `da19001` — "feat(clientes): aplicar
autorização de módulo e habilitação nas views".

Arquivos do commit de implementação:

- `apps/clientes/views.py` (modificado);
- `apps/clientes/tests/__init__.py` (novo);
- `apps/clientes/tests/test_autorizacao.py` (novo).

Documentação de fechamento atualizada nesta etapa (ainda não
commitada):

- `docs/delivery/current-state.md`;
- `docs/delivery/work/WI-0001-autorizacao-backend-clientes.md` (este
  arquivo).

Testes executados na implementação:

- `python manage.py test apps.clientes.tests.test_autorizacao` — Camada
  1 e Camada 2, em lotes sucessivos — `OK`;
- `python manage.py test apps.clientes` — 26 testes — `OK`;
- `python manage.py test apps.accounts` — 86 testes — `OK`;
- `python manage.py check` — "System check identified no issues (0
  silenced)";
- `python manage.py makemigrations --check --dry-run` — "No changes
  detected";
- `git diff --check` (working tree e staged, em cada etapa) — sem
  saída, aprovado.

Estado do Git nesta etapa: o commit documental de encerramento (que
conterá esta atualização do WI e de `current-state.md`) ainda não
existe nesta etapa de preparação — seu hash não é registrado aqui
porque só é conhecido depois que o commit for criado.

### Commit

Commit de implementação: `da19001` — "feat(clientes): aplicar
autorização de módulo e habilitação nas views" (ver "Execução
(implementação)" acima).

Commit documental de encerramento: ainda não executado nesta etapa.

## Encerramento

- [x] critérios de aceite verificados;
- [x] testes/validações registrados;
- [x] diff revisado;
- [x] escopo respeitado;
- [x] current-state atualizado quando aplicável;
- [x] roadmap atualizado somente se necessário — não foi necessário,
  não foi alterado;
- [x] achados laterais registrados;
- [x] Git final registrado.
