---
title: WI-0005 — Escopo e responsabilidade em Processos
status: canonical
owner: delivery
last_reviewed: 2026-08-19
---

# WI-0005 — Escopo e responsabilidade em Processos

## Estado

in_progress

## Fase do roadmap

Fase: Fase B — Aplicar escopo de dados nas entidades críticas

Objetivo relacionado: aplicar a decisão de produto PDR-0010 à entidade
`Processo`, com escopo de leitura, posse como fronteira de mutação,
responsável obrigatório e transferência segura ao Administrador.

## Objetivo

Implementar `somente_seus` e `todos` em Processos sem confundir leitura
com autorização de mutação; tornar `Processo.responsavel` obrigatório;
permitir reatribuição explícita por Administrador; e cobrir, no fluxo de
produto realmente existente, a perda de acesso efetivo ao módulo.

## Resultado observável pelo Product Owner

### Ao concluir este WI

- usuário `somente_seus` vê apenas processos sob sua responsabilidade;
- usuário `todos` pode ver todos os processos, mas altera apenas os seus;
- o Administrador vê, altera e reatribui qualquer processo;
- criação sempre produz processo com responsável elegível;
- a tela oferece um filtro temporário de escopo em ativos e arquivados;
- perda de acesso efetivo por configuração transfere definitivamente os
  processos do usuário ao Administrador;
- clientes ativos do tenant continuam disponíveis no formulário de
  processo, independentemente do módulo/escopo de Clientes.

### Ainda não estará coberto

- `Da equipe`, qualquer filtragem ou autorização baseada em equipe;
- habilitações granulares de Processos;
- participantes/remodelagem de partes conforme PDR-0001;
- exclusão de processos;
- criação de fluxos de produto inexistentes para inativar ou excluir
  usuários;
- IA, Laboratório e WI-0006/WI-0007.

## Contexto e motivação

O WI-0004 aplicou a autorização binária do módulo às nove rotas de
Processos. O risco remanescente é ALTO: o HEAD permite leitura e mutação
intra-tenant por `pk` sem fronteira de responsabilidade, e o responsável
ainda é anulável. PDR-0010 define esta fatia vertical como a evolução
seguinte, mantendo backend como autoridade e equipe integralmente fora
do escopo.

## Evidência do estado atual

Auditoria do HEAD `d8837d08d418707ae9ff2227ece3cdee03a10b7e`:

- as nove views consultam `tem_permissao_modulo()`, evidência do WI-0004;
- listas, detalhe e mutações carregam processos sem filtro por
  responsabilidade;
- `Processo.responsavel` usa `SET_NULL`, `null=True`, `blank=True`;
- criação atribui sempre `request.user`; edição não expõe responsável;
- `ProcessoForm.cliente` já consulta clientes ativos do schema atual e
  rejeita cliente inativo no POST sem consultar autorização de Clientes;
- o único fluxo de produto encontrado que altera acesso efetivo é a tela
  `configuracoes:permissoes`, que atualiza `PermissaoPapel`;
- não existe fluxo de produto para inativação ou exclusão de usuário;
- no schema `demo` existem 10 processos: nenhum com responsável nulo e
  dois com responsável atualmente inelegível ao módulo; existe um único
  Administrador ativo elegível para receber a transferência;
- a migration de Clientes que combinou exclusão e `ALTER TABLE` sofreu o
  incidente PostgreSQL de eventos de trigger pendentes; Processos não
  exige exclusão de linhas e não deve copiar esse desenho cegamente.

## Resultado esperado

QuerySets de leitura respeitam o escopo efetivo solicitado em `?escopo=`;
QuerySets de mutação limitam não-administradores ao próprio responsável e
respondem 404 para objetos alheios. O Administrador pode selecionar apenas
usuários ativos e efetivamente autorizados ao módulo. A perda de acesso
provocada pelo fluxo de configuração transfere todos os processos ao
Administrador na mesma transação. Migrations preservam todos os processos,
normalizam responsáveis nulos ou inelegíveis e só então aplicam `NOT NULL`
e `PROTECT`, falhando explicitamente se uma transferência necessária não
tiver Administrador ativo elegível.

## Fontes canônicas

- [PDR-0010](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [Processos](../../product/modules/processos.md)
- [Modelo de autorização](../../security/authorization-model.md)
- [Escopo de dados](../../security/data-scope.md)
- [Matriz de autorização](../../security/authorization-matrix.md#processos)
- [Visão geral de segurança](../../security/overview.md)
- [Estado atual](../current-state.md)
- [Roadmap](../roadmap.md)
- [WI-0002](WI-0002-escopo-responsabilidade-clientes.md)
- [WI-0004](WI-0004-autorizacao-modulo-processos.md)

## Arquivos do HEAD a auditar antes da implementação

- `apps/processos/models.py`, `forms.py`, `views.py`, `urls.py`;
- `apps/processos/templates/processos/*.html`;
- `apps/processos/tests/test_autorizacao.py` e migrations existentes;
- `apps/accounts/permissoes.py`, `decorators.py`, models e migrations;
- `apps/configuracoes/views.py` e URLs;
- implementação e migrations análogas de Clientes;
- configuração de `django-tenants` e infraestrutura de testes.

## Escopo permitido

### Pode alterar

- `apps/processos/models.py`, `forms.py`, `views.py`;
- templates existentes de Processos necessários à UX de escopo,
  responsabilidade e ocultação de ações;
- testes existentes de Processos;
- `apps/configuracoes/views.py`, exclusivamente para tornar atômica a
  transferência causada por perda de acesso no fluxo real de permissões.

### Pode criar

- `apps/processos/services.py`;
- migrations de dados e schema de Processos;
- testes de escopo, responsabilidade, serviço, formulário e migration;
- testes de Configurações para o fluxo real de perda de acesso.

### Migrations

Obrigatórias. Devem separar a normalização de dados do `ALTER TABLE`,
preservar todas as linhas e ser validadas em PostgreSQL/django-tenants,
incluindo rollback de schema e mais de um schema de tenant quando a
infraestrutura o permitir com segurança.

### Documentação

- este Work Item e sua evidência de execução;
- `docs/delivery/current-state.md` somente após aprovação/revisão quando
  o novo estado puder ser tratado como entregue.

## Fora de escopo

> qualquer alteração útil, mas não necessária para satisfazer os
> critérios deste item, permanece fora do escopo até ser explicitamente
> incorporada.

- WI-0006 e WI-0007;
- equipes e `da_equipe`, inclusive testes ou UX relacionados;
- habilitações granulares `processos_*`;
- exclusão de processos;
- remodelagem de `ParteProcesso`, participantes ou PDR-0001;
- novos fluxos de gestão/inativação/exclusão de usuários;
- resolver decisões abertas alheias ao módulo;
- refatorações laterais de Clientes ou do kernel de autorização.

## Regras funcionais e técnicas

- `?escopo=` é por requisição, não persiste preferência.
- Ausência do parâmetro usa o nível máximo; valor presente vazio,
  inválido ou acima do máximo retorna 403.
- `somente_seus` filtra ativos, arquivados e detalhe por responsável.
- `todos` amplia apenas leitura; não amplia mutação de não-admin.
- editar, arquivar, reabrir, adicionar movimentação e adicionar parte em
  processo alheio retornam 404 sem mudança.
- Administrador ativo pode ler/mutar todos e reatribuir a responsável
  elegível; não-admin cria obrigatoriamente para si e não reatribui.
- Responsável elegível é usuário ativo do tenant com acesso efetivo a
  `processos` segundo `tem_permissao_modulo()`; Administrador ativo é
  elegível pelo próprio kernel.
- Perda de acesso no fluxo real de configuração transfere todos os
  processos ao Administrador antes de concluir a transação; ganho futuro
  de acesso não devolve processos automaticamente.
- Como inexiste fluxo de produto de inativação/exclusão, este item não
  inventa um. `PROTECT` impede exclusão do responsável enquanto houver
  processos.
- Cliente selecionável é qualquer `Cliente.ativo=True` do tenant atual;
  cliente inativo enviado em POST é inválido.
- A migration trata responsável nulo e responsável inelegível, exige um
  único Administrador ativo quando transferência for necessária e não
  exclui processo algum.

## Segurança e autorização

- A autorização binária do WI-0004 permanece como primeira barreira.
- Leitura e mutação usam QuerySets distintos; a interface apenas reflete
  a decisão, nunca a substitui.
- Objetos fora da fronteira de posse retornam 404 para reduzir enumeração
  intra-tenant.
- O isolamento entre tenants continua provido pelo schema atual; nenhuma
  consulta usa `schema_context` para atravessar tenants em runtime.
- Mudanças de permissão e transferência são atômicas para não deixar
  processo com responsável sem acesso.

## Decisões abertas e bloqueios

Nenhuma decisão aberta afeta este item. Equipe foi explicitamente excluída
por PDR-0010. A ausência de fluxo de produto de inativação/exclusão é
registrada como limite constatado, não como bloqueio.

## Dependências

- WI-0004 concluído;
- kernel efetivo de `apps/accounts/permissoes.py`;
- Administrador único por tenant conforme modelo vigente;
- PostgreSQL e `django-tenants` para validação da migration.

## Critérios de aceite

- [x] `somente_seus` limita ativos, arquivados e detalhe ao responsável;
- [x] `todos` lê todos, mas não-admin recebe 404 nas cinco mutações alheias;
- [x] Admin lê/muta todos e reatribui apenas a usuário elegível;
- [x] criação força o próprio usuário para não-admin;
- [x] seletor visual respeita nível máximo e não persiste estado;
- [x] UI oculta ações que o backend recusaria;
- [x] responsável é obrigatório e protegido contra exclusão;
- [x] migration preserva linhas e normaliza nulos/inelegíveis;
- [x] perda de acesso pelo fluxo real transfere de modo atômico;
- [x] cliente ativo independe do módulo Clientes e inativo é rejeitado;
- [x] regressão de autorização binária do WI-0004 permanece verde;
- [x] nenhuma semântica de equipe é implementada.

## Testes esperados

### Existentes a considerar

- `apps/processos/tests/test_autorizacao.py`;
- suítes `apps/accounts`, `apps/clientes` e `apps/configuracoes` quando
  alterada;
- `manage.py check` e detecção de migrations pendentes.

### Novos testes

- matriz de leitura para `somente_seus`, `todos` e Admin;
- cinco mutações alheias com 404 e prova de ausência de mudança;
- criação/edição e elegibilidade do responsável;
- filtro temporário e parâmetros inválidos;
- cliente ativo sem permissão de Clientes e rejeição de inativo;
- transferência por perda de acesso, atomicidade e não retorno automático;
- integridade `NOT NULL`/`PROTECT`;
- migration com dados preexistentes, preservação, falha segura e rollback.

### Comandos de validação

- `.venv\\Scripts\\python.exe manage.py test apps.processos`
- `.venv\\Scripts\\python.exe manage.py test apps.configuracoes`
- `.venv\\Scripts\\python.exe manage.py test apps.accounts apps.clientes`
- `.venv\\Scripts\\python.exe manage.py check`
- `.venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run`
- `git diff --check`

### Validação manual

Aplicável: SIM

Cenários previstos:

1. `somente_seus`: ativos, arquivados e detalhe alheio;
2. `todos`: leitura ampla e mutações alheias por URL/POST;
3. Admin: leitura, mutação e reatribuição;
4. criação não-admin com tentativa de forjar responsável;
5. filtro temporário em ativos e arquivados;
6. perda e posterior ganho de acesso, sem devolução automática;
7. seleção de cliente ativo sem acesso ao módulo Clientes;
8. rejeição de cliente inativo;
9. migration em PostgreSQL com dados preexistentes e mais de um schema.

Resultado real (preencher durante a execução, não antes):

- pendente de execução/aprovação do Product Owner; o roteiro não será
  executado por este agente.

## Quality gates

- [x] testes alvo executados
- [x] testes negativos executados, quando aplicável
- [x] suíte relevante executada, quando exigida pelo item
- [x] `git diff --check`
- [x] diff revisado integralmente
- [x] links e documentação referenciados verificados

## Atualizações documentais esperadas

Registrar neste WI arquivos, comandos e resultados reais. Atualizar
`current-state.md` somente após revisão/aprovação, não nesta preparação.

## Achados fora do escopo

- Não existe fluxo de produto para inativação ou exclusão de usuário; não
  será criado por este item.

## Evidência de execução

### Estado inicial

Branch: `docs/reorganizacao-harness`

HEAD: `d8837d08d418707ae9ff2227ece3cdee03a10b7e`

Git status: limpo; `origin/docs/reorganizacao-harness` sincronizada após
`git fetch origin`.

### Arquivos alterados

- `apps/configuracoes/views.py`
- `apps/configuracoes/tests/__init__.py`
- `apps/configuracoes/tests/test_perda_acesso_processos.py`
- `apps/processos/forms.py`
- `apps/processos/migrations/0005_normalizar_responsavel.py`
- `apps/processos/migrations/0006_responsavel_obrigatorio.py`
- `apps/processos/models.py`
- `apps/processos/services.py`
- `apps/processos/tests/test_autorizacao.py`
- `apps/processos/tests/test_escopo.py`
- `apps/processos/tests/test_migrations.py`
- `apps/processos/views.py`
- `templates/processos/arquivados.html`
- `templates/processos/detalhe.html`
- `templates/processos/form.html`
- `templates/processos/lista.html`
- `docs/delivery/work/WI-0005-escopo-responsabilidade-processos.md`

### Testes executados

- `.venv\\Scripts\\python.exe manage.py test
  apps.processos.tests.test_autorizacao --verbosity 2` — 30 testes; uma
  falha inicial esperada revelou que o fixture Admin ainda não enviava o
  novo responsável obrigatório; fixture adaptado e regressão reexecutada.
- `.venv\\Scripts\\python.exe manage.py test apps.processos.tests.test_escopo
  apps.configuracoes.tests.test_perda_acesso_processos --verbosity 2` —
  12/12 testes verdes.
- `.venv\\Scripts\\python.exe manage.py test apps.processos
  apps.configuracoes apps.accounts apps.clientes --verbosity 1` — 185/185
  testes verdes.
- `.venv\\Scripts\\python.exe manage.py test apps.processos --verbosity 1`
  após os reforços finais — 43/43 testes verdes.
- Primeira execução combinada da correção, com 12 testes: os 10 testes de
  `TestProcessosSomenteSeus` passaram e os dois testes de migration expuseram
  que a transação externa de `TenantTestCase` mantinha eventos de FK pendentes
  até o `ALTER TABLE`. O harness do teste de migration foi ajustado para o
  isolamento transacional real entre migrations; nenhum código funcional nem
  migration foi alterado por esse diagnóstico.
- Correção dos findings do review: `.venv\\Scripts\\python.exe manage.py
  test apps.processos.tests.test_escopo.TestProcessosSomenteSeus
  apps.processos.tests.test_migrations --verbosity 1 --noinput` — 12/12
  testes verdes; inclui as cinco mutações alheias para `somente_seus` e
  os dois cenários históricos de migration.
- `.venv\\Scripts\\python.exe manage.py test
  apps.processos.tests.test_migrations --verbosity 1 --noinput` — 2/2
  testes verdes em execução isolada repetida.
- Regressões separadas após a correção: `apps.processos` — 50/50;
  `apps.accounts` — 86/86; `apps.clientes` — 57/57;
  `apps.configuracoes` — 2/2.

### Validações executadas

- `.venv\\Scripts\\python.exe manage.py check` — sem issues.
- `.venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run` —
  nenhuma mudança pendente.
- `git diff --check` — sem erros.
- PostgreSQL/schema `demo`: 10/10 processos preservados; dois responsáveis
  inelegíveis transferidos; zero nulos/inelegíveis após migration;
  `responsavel_id IS NULLABLE = NO`.
- Rollback `processos 0004` no `demo`: 10/10 processos preservados e coluna
  novamente anulável; migrations 0005/0006 reaplicadas com sucesso.
- Schema descartável `wi0005_migration_tmp`: três linhas preexistentes
  (Admin, inelegível e nulo) preservadas e normalizadas para o Admin; `NOT
  NULL` aplicado.
- Schema descartável `wi0005_migration_fail_tmp`: sem Admin, a migration
  falhou explicitamente antes do `ALTER`, preservou a linha e o nulo, e não
  gravou 0005 em `django_migrations`.
- Os dois schemas descartáveis foram removidos definitivamente após a
  validação; o schema `demo` permaneceu no estado final 0006.
- Teste automatizado `apps/processos/tests/test_migrations.py`, em PostgreSQL
  com `django-tenants`: schema descartável
  `wi0005_processos_migrations`; estado histórico real em
  `processos.0004_rename_departamento_equipe`; aplicação até
  `processos.0006_responsavel_obrigatorio`; responsável válido preservado;
  nulo e inelegível transferidos ao único Admin; três processos preservados;
  `NOT NULL` comprovado no catálogo do PostgreSQL; rollback a 0004 e
  reaplicação até 0006 concluídos; falha sem Admin preservou dado e não
  registrou `processos.0005_normalizar_responsavel`; recuperação posterior
  concluída após criação de Admin. O lifecycle de `TenantTestCase` remove o
  schema ao encerrar a classe.

### Resultado

Implementação e gates automatizados concluídos, pronta para revisão. O WI
permanece `in_progress` porque a validação manual do PO não foi executada e
nenhum commit foi autorizado.

### Commit

Não haverá commit nesta execução, por mandato expresso.

Git final: 17 arquivos do WI em staging explícito; working tree sem
alterações fora do staging; nenhum commit e nenhum push.

## Encerramento

- [x] critérios de aceite verificados;
- [x] testes/validações registrados;
- [x] diff revisado;
- [x] escopo respeitado;
- [ ] current-state atualizado quando aplicável;
- [x] roadmap atualizado somente se necessário;
- [x] achados laterais registrados;
- [x] Git final registrado.
