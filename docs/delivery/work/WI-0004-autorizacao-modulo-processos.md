---
title: WI-0004 — Autorização do módulo Processos
status: canonical
owner: delivery
last_reviewed: 2026-08-19
---

# WI-0004 — Autorização do módulo Processos

## Estado

done

## Fase do roadmap

Fase: Fase A — Consolidar autorização nas operações

Objetivo relacionado: aplicar autorização de módulo nas views
operacionais, conforme
[roadmap.md](../roadmap.md#fase-a--consolidar-autorização-nas-operações),
na fatia definida por
[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md):
autorização binária por módulo `processos` nesta versão, sem
habilitações granulares e sem escopo de dados. Para Processos, essa
política específica satisfaz a Fase A; as habilitações preservadas no
kernel são evolução futura e não requisito pendente desta fase.

## Objetivo

Aplicar autorização backend do módulo `processos`
(`tem_permissao_modulo(request.user, "processos")`) em todas as nove
operações atualmente existentes de `apps/processos/views.py`, sem
aplicar as habilitações granulares já existentes no kernel
(`processos_criar`, `processos_editar`,
`processos_andamento_adicionar`) e sem implementar escopo de dados,
conforme [PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md).

## Resultado observável pelo Product Owner

### Ao concluir este WI

Usuário com módulo Processos habilitado:

- acessa lista;
- acessa detalhe;
- cria processo;
- edita;
- consulta arquivados;
- arquiva;
- reabre;
- adiciona movimentação;
- adiciona parte.

Usuário sem módulo Processos habilitado:

- não acessa nenhuma dessas operações;
- tentativa direta pela URL é negada;
- `POST` manual para operação protegida é negado.

### Ainda não estará coberto

- `Somente os seus`;
- `Todos`;
- filtragem de QuerySets por escopo;
- autorização por responsabilidade;
- responsável obrigatório;
- reatribuição automática ao Administrador do escritório;
- migration de `Processo`;
- regras de cliente no formulário além do comportamento já existente;
- equipe como base de escopo;
- `Da equipe`;
- remodelagem de `ParteProcesso` (PDR-0001);
- participantes conforme PDR-0001;
- IA;
- Laboratório;
- checagem de `processos_criar`/`processos_editar`/
  `processos_andamento_adicionar` — por decisão de produto (PDR-0010),
  não por lacuna de implementação.

## Contexto e motivação

[current-state.md#processos](../current-state.md#processos) e
[authorization-matrix.md#processos](../../security/authorization-matrix.md#processos)
registram que as nove views de `apps/processos/views.py` usam
exclusivamente `@login_required`, sem consultar o kernel de
autorização já aplicado a Clientes desde o
[WI-0001](WI-0001-autorizacao-backend-clientes.md). Este item é a
primeira unidade de trabalho de Fase A para Processos, seguindo o
mesmo padrão de enforcement de módulo já validado em Clientes, mas
restrito à camada de módulo, conforme a decisão de produto formalizada
em
[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md).

## Evidência do estado atual

Reconfirmada por leitura direta do HEAD (commit `86cf65d`) nesta
execução:

- Comportamento existente: as nove views de `apps/processos/views.py`
  (`lista`, `detalhe`, `novo`, `editar`, `arquivados`, `arquivar`,
  `reabrir`, `adicionar_movimentacao`, `adicionar_parte`) usam
  exclusivamente `@login_required`. Nenhuma chamada a
  `tem_permissao_modulo()` ou `tem_habilitacao()` foi encontrada neste
  arquivo.
- Lacuna constatada:
  [authorization-matrix.md#processos](../../security/authorization-matrix.md#processos)
  classifica a autorização de módulo de todas as nove operações como
  "Lacuna constatada" (célula "Aut. módulo"/"Estado constatado").
- Cobertura de teste ausente: nenhum arquivo de teste existe em
  `apps/processos/` (`find apps -type f \( -name "test_*.py" -o -name
  "tests.py" \)` não retorna nenhum arquivo em `apps/processos`).
- Operação planejada:
  [roadmap.md](../roadmap.md#fase-a--consolidar-autorização-nas-operações)
  define, como pré-requisito de saída da Fase A, que operações
  sensíveis consultem o kernel adequado; este item cobre a camada de
  módulo para Processos, política suficiente para sua Fase A conforme
  PDR-0010. Habilitações granulares permanecem apenas como evolução
  futura possível; escopo e responsabilidade seguem para o WI-0005, na
  Fase B.
- `tem_permissao_modulo()` (`apps/accounts/permissoes.py`) já resolve
  `usuario_admin_escritorio()` internamente antes de qualquer
  `PermissaoUsuario`/`PermissaoPapel`, concedendo acesso total ao
  módulo no maior nível técnico configurado — reconfirmado por leitura
  direta de `_permissao_efetiva_com_contexto()`.
- `MODULO_PROCESSOS = "processos"` já existe em
  `apps/accounts/permissoes_constants.py`, junto das três habilitações
  já existentes (`HAB_PROCESSOS_CRIAR`, `HAB_PROCESSOS_EDITAR`,
  `HAB_PROCESSOS_ANDAMENTO_ADICIONAR`), que este item não consome.

## Resultado esperado

Todas as nove rotas existentes de Processos passam a negar acesso no
backend (`raise PermissionDenied`, antes de qualquer leitura ou
mutação) a um usuário autenticado sem autorização de módulo
`processos`. Nenhuma mutação ocorre quando a autorização é negada. Um
usuário autorizado ao módulo continua alcançando as nove rotas
normalmente, incluindo criar/editar/adicionar movimentação, mesmo sem
`processos_criar`/`processos_editar`/`processos_andamento_adicionar` —
comportamento esperado nesta versão, não falha. Este resultado não
implica escopo de dados por responsável, que permanece pendente para a
Fase B, conforme PDR-0010 e "Fora de escopo" abaixo. Habilitação
granular permanece apenas como evolução futura possível e não bloqueia
a conclusão da Fase A de Processos.

## Fontes canônicas

- [../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [../../security/overview.md](../../security/overview.md)
- [../../security/authorization-model.md](../../security/authorization-model.md)
- [../../security/data-scope.md](../../security/data-scope.md)
- [../../security/authorization-matrix.md](../../security/authorization-matrix.md#processos)
- [../../product/modules/processos.md](../../product/modules/processos.md)
- [../../product/open-decisions.md](../../product/open-decisions.md)
- [../current-state.md](../current-state.md)
- [../roadmap.md](../roadmap.md)
- [WI-0001-autorizacao-backend-clientes.md](WI-0001-autorizacao-backend-clientes.md)
  (padrão de referência de Camada 1)

## Arquivos do HEAD a auditar antes da implementação

- `apps/processos/views.py`
- `apps/processos/urls.py`
- `apps/processos/models.py`
- `apps/processos/forms.py`
- `apps/accounts/permissoes.py`
- `apps/accounts/permissoes_constants.py`
- `apps/accounts/decorators.py`
- `apps/clientes/views.py` (padrão já aplicado, Camada 1)
- `apps/clientes/tests/test_autorizacao.py` (padrão de teste de
  referência)

A evidência acima foi reconfirmada no HEAD nesta preparação; nenhuma
divergência foi encontrada em relação ao que este item presumia.

## Escopo permitido

### Pode alterar

- `apps/processos/views.py` — adicionar exclusivamente a verificação
  de autorização de módulo (`tem_permissao_modulo`) descrita em
  "Regras funcionais e técnicas", no início de cada uma das nove
  views, antes de qualquer leitura ou mutação. Nenhuma outra mudança de
  comportamento é autorizada neste arquivo.
- `docs/delivery/current-state.md` — apenas ao final da implementação,
  e apenas na seção referente a Processos/Autorização, refletindo que
  as views agora consultam `tem_permissao_modulo()`.

### Pode criar

- `apps/processos/tests/__init__.py`
- `apps/processos/tests/test_autorizacao.py`

### Migrations

Proibidas. Este Work Item não altera schema. Se a implementação
concluir que uma migration é necessária, a implementação deve parar e
registrar achado fora do escopo em vez de criá-la.

### Documentação

- Este próprio Work Item, incluindo sua seção de evidência de execução
  e encerramento.
- `docs/delivery/current-state.md`, apenas ao final e apenas se o
  estado material tiver mudado (esperado, ver acima).

## Fora de escopo

> qualquer alteração útil, mas não necessária para satisfazer os
> critérios deste item, permanece fora do escopo até ser explicitamente
> incorporada.

- `processos_criar`, `processos_editar`,
  `processos_andamento_adicionar` — por decisão de produto
  ([PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)),
  não devem ser consultadas pelas views de Processos nesta versão.
  Consumi-las seria implementar em conflito com a decisão de produto
  vigente, não uma melhoria antecipada.
- `apps/accounts/permissoes.py`, `apps/accounts/permissoes_constants.py`,
  `apps/accounts/decorators.py` e `apps/accounts/escopo.py` são fontes
  a auditar, não alvo de alteração.
- `apps/processos/models.py`, `apps/processos/forms.py`,
  `apps/processos/urls.py` e `templates/processos/` não devem ser
  alterados por este item.
- `config/` não deve ser alterado por este item.
- Escopo de dados por `Processo.responsavel`, por equipe, `nivel`
  (`somente_seus`/`todos`) tratado como filtro de `QuerySet`,
  autorização sobre objeto (IDOR intra-tenant) e responsabilidade
  obrigatória pertencem a Work Item futuro, conforme PDR-0010 — não a
  este item. Após este item, `get_object_or_404(Processo, pk=pk, ...)`
  continua carregando qualquer processo do tenant autorizado ao
  módulo, sem condição de posse — este item não resolve IDOR
  intra-tenant e não deve ser reportado como tendo resolvido.
- Nenhuma habilitação nova para o módulo `processos` pode ser criada
  por este item.
- `nivel` (`somente_seus`/`todos`) não deve ser lido, filtrado ou
  reinterpretado como autorização de ação por este item.
- Módulo Clientes, `ParteProcesso`/PDR-0001, IA/Laboratório — fora de
  escopo, conforme PDR-0010 e mandato desta execução.

## Regras funcionais e técnicas

### Camada única — autorização de módulo (nove rotas)

Cada uma das nove views de `apps/processos/views.py` deve, além de
`@login_required`, negar acesso com `raise PermissionDenied` quando
`tem_permissao_modulo(request.user, "processos")` for falso, **antes**
de qualquer leitura ou mutação (`get_object_or_404`, criação, `.save()`):

- `lista`
- `detalhe`
- `novo`
- `editar`
- `arquivados`
- `arquivar`
- `reabrir`
- `adicionar_movimentacao`
- `adicionar_parte`

Nenhuma camada de habilitação (`tem_habilitacao`) é adicionada neste
item — diferença deliberada em relação ao padrão do
[WI-0001](WI-0001-autorizacao-backend-clientes.md), que aplicou
Camada 1 e Camada 2 para Clientes. Aqui, apenas Camada 1, por
[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md).

### `nivel` (nível de acesso técnico atual)

`NIVEIS_POR_MODULO["processos"]` (`somente_seus`, `todos`) não é lido,
filtrado ou usado como condição de autorização por este item, pelo
mesmo motivo já registrado no WI-0001 para Clientes: escopo de dados
pertence a fase/decisão futura.

### Administrador do escritório

`tem_permissao_modulo()` já avalia `usuario_admin_escritorio()`
internamente, antes de qualquer `PermissaoUsuario`/`PermissaoPapel`,
concedendo acesso total ao módulo no maior nível configurado. A
implementação deve chamar apenas `tem_permissao_modulo()` nas views de
Processos e não deve reproduzir uma checagem manual e paralela de
`is_admin_escritorio` dentro de `apps/processos/views.py`.

### Resposta de negação

Mesma convenção já adotada em `apps/clientes/views.py` (WI-0001):
`raise PermissionDenied`, resultando na página padrão de erro 403 do
Django (nenhum `handler403` customizado nem template `403.html` foi
encontrado no HEAD). A implementação não inventa texto, redirect ou UX
de produto para a página de erro. Este item não é bloqueado pela
ausência de uma página 403 customizada — apenas exige que:

- a negação ocorra no backend;
- nenhuma mutação seja executada quando negado;
- nenhum acesso ao comportamento protegido ocorra quando negado.

## Segurança e autorização

- Backend como autoridade: as verificações de módulo devem ocorrer nas
  views de `apps/processos/views.py`, antes de qualquer leitura ou
  mutação de `Processo`/`MovimentacaoProcessual`/`ParteProcesso`,
  independentemente do que a interface exiba.
- Este item não aplica escopo de dados: um usuário autorizado ao
  módulo `processos` continuará, após este item, alcançando qualquer
  processo do tenant por `pk`, não apenas os de sua responsabilidade —
  consistente com o estado já existente hoje e com a direção futura
  registrada em PDR-0010.
- Nenhuma resposta deste item amplia o escopo que o usuário já teria
  diretamente.

## Decisões abertas e bloqueios

Nenhuma decisão em aberto (`OPEN-001`, `OPEN-002`) afeta este item —
ambas pertencem exclusivamente ao módulo Financeiro. Nenhum bloqueio
foi identificado para o escopo delimitado deste item: a autorização de
módulo está suficientemente definida pelo kernel constatado, e
[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
resolve a ambiguidade sobre habilitação granular nesta versão.

## Dependências

- Depende apenas do kernel de autorização já implementado em
  `apps/accounts/permissoes.py` (`tem_permissao_modulo()`), que este
  item não altera.
- Depende da formalização de
  [PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md),
  concluída antes deste item nesta mesma execução.
- Não pode ser executado em paralelo com outro Work Item que também
  altere `apps/processos/views.py`.

## Critérios de aceite

- [x] usuário sem módulo `processos` não acessa `lista` (403) —
      `TestProcessosAutorizacaoModuloNegado.test_lista_negada`;
- [x] usuário sem módulo `processos` não acessa `detalhe` (403) —
      `test_detalhe_negado`;
- [x] usuário sem módulo `processos` não acessa `arquivados` (403) —
      `test_arquivados_negado`;
- [x] usuário sem módulo `processos` não cria processo (`novo`, GET e
      POST negados, nenhum `Processo` criado) — `test_novo_get_negado`,
      `test_novo_post_negado_nao_cria_processo`;
- [x] usuário sem módulo `processos` não edita (`editar`, GET e POST
      negados, nenhum valor alterado) — `test_editar_get_negado`,
      `test_editar_post_negado_preserva_valores`;
- [x] usuário sem módulo `processos` não arquiva nem reabre (`arquivar`/
      `reabrir`, GET e POST negados, `status` inalterado) —
      `test_arquivar_get_negado`, `test_arquivar_post_negado_nao_altera_status`,
      `test_reabrir_get_negado`, `test_reabrir_post_negado_nao_altera_status`;
- [x] usuário sem módulo `processos` não adiciona movimentação (GET e
      POST negados, nenhuma `MovimentacaoProcessual` criada) —
      `test_adicionar_movimentacao_get_negado`,
      `test_adicionar_movimentacao_post_negado_nao_cria`;
- [x] usuário sem módulo `processos` não adiciona parte (GET e POST
      negados, nenhuma `ParteProcesso` criada) —
      `test_adicionar_parte_get_negado`,
      `test_adicionar_parte_post_negado_nao_cria`;
- [x] usuário com módulo `processos` habilitado continua alcançando as
      nove rotas normalmente, incluindo criar/editar/adicionar
      movimentação sem `processos_criar`/`processos_editar`/
      `processos_andamento_adicionar` —
      `TestProcessosAutorizacaoModuloConcedido` (11 testes, nenhuma
      `HabilitacaoPapel` concedida no fixture);
- [x] Administrador do escritório continua autorizado a todas as
      operações, sem depender de `UsuarioPapel`/`PermissaoPapel` —
      `TestProcessosAutorizacaoAdministrador` (4 testes);
- [x] negação ocorre no backend antes de qualquer leitura ou mutação —
      `raise PermissionDenied` é a primeira instrução após
      `@login_required` em cada uma das nove views (confirmado por
      leitura direta de `apps/processos/views.py` nesta execução);
- [x] nenhuma habilitação nova foi criada —
      `apps/accounts/permissoes_constants.py` não foi alterado (ausente
      de `git status --short` desta execução);
- [x] `nivel` não foi lido nem reinterpretado como autorização de ação —
      `nivel_acesso_modulo`/`NIVEIS_POR_MODULO` não aparecem em
      `apps/processos/views.py`;
- [x] nenhuma migration foi criada — `python manage.py makemigrations
      --check --dry-run` → "No changes detected" (exit 0);
- [x] nenhum arquivo fora do escopo permitido foi modificado — `git
      status --short`/`git diff --stat` desta execução contêm apenas
      `apps/processos/views.py`, `apps/processos/tests/__init__.py`,
      `apps/processos/tests/test_autorizacao.py` e a documentação
      explicitamente autorizada (ver "Evidência de execução");
- [x] `docs/delivery/current-state.md` foi atualizado ao final, na
      seção de Processos/Autorização;
- [x] evidência de Git foi registrada na seção "Evidência de execução"
      deste item.

## Testes esperados

### Existentes a considerar

- `apps/accounts/tests/test_permissoes_kernel.py` e
  `apps/accounts/tests/test_interacoes_kernel.py` cobrem
  `permissao_efetiva()`/`tem_permissao_modulo()`, que este item passa a
  consumir em `apps/processos/views.py` — não precisam ser alterados,
  mas a suíte de `apps.accounts` deve ser executada como regressão.
- `apps/clientes/tests/test_autorizacao.py` é o padrão de referência
  de fixtures e estrutura de teste (Camada 1) reaproveitado por este
  item, adaptado para `apps/processos` sem a Camada 2 de habilitação.

### Novos testes

Testes automatizados novos para o módulo Processos, cobrindo apenas o
enforcement de módulo — não escopo, não habilitação.

**Autorização do módulo** — usuário autenticado sem acesso ao módulo
`processos` (`tem_permissao_modulo` falso) não acessa/executa:

- listagem (`lista`);
- detalhe (`detalhe`);
- arquivados (`arquivados`);
- criação (`novo`, GET e POST);
- edição (`editar`, GET e POST);
- arquivar (`arquivar`, GET e POST);
- reabrir (`reabrir`, GET e POST);
- adicionar movimentação (GET e POST);
- adicionar parte (GET e POST).

**Regressão mínima** — usuário com módulo `processos` autorizado (via
papel dinâmico, sem nenhuma habilitação concedida) continua alcançando
as nove rotas, incluindo criar/editar/adicionar movimentação —
provando que módulo autorizado é suficiente nesta versão, conforme
PDR-0010.

**Administrador** — usuário com `is_admin_escritorio=True`, sem
`UsuarioPapel`/`PermissaoPapel`, continua autorizado às operações
principais.

**Não testar como resolvido neste item**:

- processo fora do escopo por `responsavel`;
- escopo por equipe;
- `somente_seus`/`todos` como filtro aplicado;
- negação por ausência de `processos_criar`/`processos_editar`/
  `processos_andamento_adicionar` (o comportamento correto nesta
  versão é justamente NÃO negar por esse motivo);
- IDOR intra-tenant final;
- isolamento cross-tenant completo.

### Comandos de validação

```text
python manage.py test apps.processos
python manage.py test apps.accounts
python manage.py test apps.clientes
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

### Validação manual

Aplicável: NÃO

Este item altera exclusivamente autorização backend, sem mudança de
template, rota nova ou fluxo de interface. A UI de Processos já exibe
incondicionalmente todos os botões de ação (mesmo padrão documentado
para Clientes no WI-0001) — nenhum elemento visual muda em consequência
deste item. A cobertura automatizada (GET/POST diretos às nove rotas,
autorizado/negado/admin) já exercita o comportamento observável
relevante deste item sem necessidade de navegação manual adicional.

## Quality gates

- [x] testes alvo executados (`apps.processos.tests.test_autorizacao` —
      30 testes, `OK`)
- [x] testes negativos executados (módulo — `TestProcessosAutorizacaoModuloNegado`,
      15 testes, `OK`)
- [x] suíte relevante executada (`apps.processos` — 30 testes, `OK`;
      `apps.accounts` — 86 testes, `OK`)
- [x] regressão de `apps.clientes` executada (FK `Processo.cliente` →
      `Cliente`; nenhuma alteração feita em `apps/clientes` — 57
      testes, `OK`, sem regressão)
- [x] `python manage.py check` → "System check identified no issues (0
      silenced)."
- [x] `python manage.py makemigrations --check --dry-run` → "No changes
      detected"
- [x] `git diff --check` → sem saída, aprovado
- [x] diff revisado integralmente, manualmente (`git diff -- apps/processos/views.py`
      confirma exatamente a checagem de módulo adicionada, nenhuma
      outra alteração de comportamento)
- [x] resultado comparado com os critérios de aceite deste item

## Revisão independente

O review independente completo encontrou inicialmente quatro findings,
todos exclusivamente documentais; nenhum finding funcional, de teste,
autorização, migration ou escopo de código foi identificado. Os quatro
findings documentais foram corrigidos no delta aprovado.

O delta-review independente final resultou **APROVADO**. Foram
aprovados: implementação, testes, autorização binária do módulo,
PDR-0010, atualizações de roadmap e matriz de autorização, ausência de
migration e escopo do diff. A validação manual não foi necessária,
conforme a seção "Validação manual" deste próprio Work Item.

## Atualizações documentais esperadas

`docs/delivery/current-state.md` deve ser atualizado ao final da
implementação, na tabela "Visão executiva" (linha Processos/
Autorização) e na subseção "Processos" de "Estado por módulo",
refletindo que as nove views agora consultam `tem_permissao_modulo()`,
sem habilitação granular nem escopo — estado material distinto do
registrado hoje ("Não aplicado nas views"). Após a decisão do Product
Owner de que a política binária do PDR-0010 satisfaz a Fase A de
Processos, `docs/delivery/roadmap.md` também deve explicitar essa
exceção à regra geral e o avanço vertical para a Fase B. Escopo e
responsabilidade permanecem pendentes para o WI-0005; habilitações
granulares não são pendência bloqueante da Fase A.

## Achados fora do escopo

Nenhum achado funcional fora do escopo foi identificado. Os quatro
findings exclusivamente documentais do review independente foram
corrigidos dentro do delta documental autorizado e aprovados no
delta-review final; não originaram implementação lateral.

## Evidência de execução

### Estado inicial

Branch: `docs/reorganizacao-harness`
HEAD: `86cf65d` — "fix(clientes): corrigir atomicidade da migration"
Git status: limpo no início desta preparação (working tree clean); os
arquivos documentais desta mesma execução (fechamento do WI-0003,
PDR-0010 e documentos canônicos relacionados) foram criados/alterados
antes deste ponto, na mesma sessão de trabalho, e estão descritos nos
commits/staging desta execução, não neste WI.

### Arquivos alterados

Modificados:

- `apps/processos/views.py` — checagem de `tem_permissao_modulo` nas
  nove views.
- `docs/delivery/current-state.md` — seções "Visão executiva",
  "Accounts e autorização", "Processos" e "Testes", conforme
  "Atualizações documentais esperadas".
- `docs/delivery/roadmap.md` — política específica de Fase A para
  Processos e avanço vertical para a Fase B.
- `docs/product/decisions/README.md` — índice do PDR-0010.
- `docs/product/modules/processos.md` — política canônica de
  autorização, escopo e responsabilidade.
- `docs/security/authorization-matrix.md` — estado constatado e alvo
  aprovado de Processos.

Novos:

- `apps/processos/tests/__init__.py`
- `apps/processos/tests/test_autorizacao.py`
- `docs/delivery/work/WI-0004-autorizacao-modulo-processos.md` — este
  contrato de execução e seu fechamento.
- `docs/product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md`

O fechamento do WI-0003 ocorreu separadamente no commit `c731509` e
não integra o H1 deste Work Item.

### Testes executados

| Comando | Executado? | Resultado |
| --- | --- | --- |
| `python manage.py test apps.processos.tests.test_autorizacao -v 2` | sim | `OK` — 30 testes |
| `python manage.py test apps.processos --noinput` | sim | `OK` — 30 testes |
| `python manage.py test apps.accounts --noinput` | sim | `OK` — 86 testes |
| `python manage.py test apps.clientes --noinput` | sim | `OK` — 57 testes |

### Validações executadas

| Gate | Comando | Executado? | Resultado |
| --- | --- | --- | --- |
| Django check | `python manage.py check` | sim | "System check identified no issues (0 silenced)." |
| Consistência de migrations | `python manage.py makemigrations --check --dry-run` | sim | "No changes detected", exit 0 |
| Formatação de diff | `git diff --check` | sim | sem saída, exit 0 |
| Revisão de diff funcional | `git diff -- apps/processos/views.py` | sim | apenas a checagem de módulo adicionada nas nove views, mais os três imports necessários; nenhuma outra alteração de comportamento |
| Verificação de escopo | `git status --short` / `git diff --stat` | sim | somente os arquivos listados em "Arquivos alterados" |
| Gate de documentação (links, newline final, trailing whitespace, NUL) | verificação direta dos arquivos `.md` alterados/criados nesta execução | sim | sem link quebrado introduzido por esta execução, newline final presente em todos, sem trailing whitespace, sem linha em branco com espaços, sem caractere NUL |

### Resultado

Autorização de módulo aplicada com sucesso às nove rotas de
`apps/processos/views.py`, conforme
[PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md):
usuário sem módulo `processos` negado (403) em todas as operações, sem
mutação; usuário com módulo autorizado (mesmo sem nenhuma habilitação
granular) preserva o comportamento das nove rotas; Administrador do
escritório autorizado independentemente do kernel de papéis dinâmicos.
Nenhuma migration foi necessária. Nenhuma regressão identificada em
`apps.accounts` (86 testes) nem em `apps.clientes` (57 testes).

### Commit

H1: `ece9eadeb25acd4452a5fd86b0bdc73705a348f4` —
"feat(processos): aplicar autorização do módulo". O commit contém a
implementação, os testes e as fontes canônicas aprovadas que definem a
política aplicada. O fechamento documental é registrado em commit
posterior, sem antecipar nem registrar aqui o hash do próprio H2.

## Encerramento

- [x] critérios de aceite verificados;
- [x] testes/validações registrados;
- [x] diff revisado;
- [x] escopo respeitado;
- [x] current-state atualizado quando aplicável;
- [x] roadmap atualizado somente se necessário — ajustado no delta
      documental posterior para explicitar que a política binária do
      PDR-0010 satisfaz a Fase A de Processos;
- [x] achados laterais registrados;
- [x] review independente completo registrado — quatro findings
      exclusivamente documentais, todos corrigidos;
- [x] delta-review independente final registrado — **APROVADO**;
- [x] validação manual registrada — não aplicável;
- [x] Git final registrado — H1
      `ece9eadeb25acd4452a5fd86b0bdc73705a348f4`, branch
      `docs/reorganizacao-harness`; HEAD inicial e arquivos alterados
      registrados em "Evidência de execução".

Este Work Item está `done`: implementação, testes, autorização,
PDR-0010, roadmap/matriz, migrations e escopo do diff foram aprovados;
os quatro findings documentais do review completo foram corrigidos e o
delta-review final foi aprovado. A Fase A de Processos está concluída.
Escopo e responsabilidade permanecem para o WI-0005, ainda não
implementado; equipe não participa desse escopo.
