---
title: Estado atual do produto
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual do produto

## Objetivo

Este documento registra o estado observado do HEAD atual do Breno -
LawSystem — o que existe no código e o que o comportamento principal
constatado sustenta. Ele serve para:

- onboarding de pessoas e agentes de IA que entram no projeto;
- planejamento de trabalho futuro, em conjunto com
  [roadmap.md](roadmap.md);
- evitar reconstrução de contexto a cada nova tarefa;
- distinguir implementação de intenção.

Este documento descreve o estado observado, não substitui as
especificações canônicas do produto. Onde este documento e uma
especificação de produto, arquitetura ou segurança divergirem, a
especificação canônica prevalece como alvo, e este documento prevalece
apenas como registro do que existe hoje, conforme a hierarquia de
fontes de [../README.md](../README.md#hierarquia-das-fontes-de-verdade).

## Referência do snapshot

- Branch auditada: `docs/reorganizacao-harness`.
- Commit HEAD auditado: `cd5f7bf` — "docs: simplificar harness de
  desenvolvimento".
- Data da revisão: 2026-08-31.
- Esta revisão é incremental: a leitura completa, arquivo por arquivo,
  descrita abaixo permanece a realizada em `a543c3f`. Entre `ece9ead` e
  `cd5f7bf`, a mudança de código funcional relevante para este
  documento foi a seção Processos, atualizada nesta revisão para
  refletir WI-0005 (`1b3f731` — escopo e responsabilidade), WI-0006
  (`a0cf4de` — participantes e representantes) e WI-0007 (`5bacbb4` —
  apensos); as demais seções deste documento não foram reauditadas
  nesta passagem e podem conter a mesma defasagem que a seção Processos
  tinha antes desta revisão. Auditoria original de `07675f7` a
  `ece9ead` (WI-0004, autorização de módulo de Processos) confirmada
  por `git show
  --stat ece9ead`. As seções "Visão executiva", "Accounts e
  autorização", "Processos" e "Testes" foram atualizadas para refletir
  essa mudança à época.
- Nesta revisão (2026-08-31), apenas a seção "Processos" foi
  reauditada, para incorporar WI-0005/WI-0006/WI-0007 e as decisões
  PDR-0013/PDR-0014. As demais seções deste documento continuam no
  estado da revisão de 2026-08-19 e não foram reconferidas contra o
  HEAD atual.
- `AGENTS.md` não foi usado como prova de estado do produto; no HEAD
  auditado ele é o ponto de entrada operacional rastreado do repositório.
- `docs/history/legacy-plans/` e `docs/history/audits/` foram usados
  apenas como contexto histórico subordinado, sem autoridade sobre o
  estado atual.
- O estado registrado neste documento é provado pela leitura direta,
  arquivo por arquivo, do código no HEAD auditado: `manage.py`,
  `config/urls.py`, `config/asgi.py`, `config/wsgi.py`,
  `config/settings/*.py`, `requirements/*.txt`, `package.json`,
  `tailwind.config.js`, todos os arquivos funcionais
  (`models.py`, `views.py`, `forms.py`, `urls.py`, `admin.py`,
  `signals.py`, `services.py`, `permissoes.py`,
  `permissoes_constants.py`, `escopo.py`, `decorators.py`) de
  `apps/saas_tenants`, `apps/saas_billing`, `apps/accounts`,
  `apps/dashboard`, `apps/clientes`, `apps/processos`, `apps/tarefas`,
  `apps/financeiro`, `apps/agenda`, `apps/chat`, `apps/modelos`,
  `apps/laboratorio` e `apps/configuracoes`; `static/js/main.js`
  (único script global do projeto); todos os templates `.html`/`.js`
  de `templates/components/sidebar.html`, `templates/dashboard/`,
  `templates/clientes/`, `templates/processos/`, `templates/tarefas/`,
  `templates/agenda/`, `templates/financeiro/`, `templates/chat/`,
  `templates/modelos/`, `templates/laboratorio/` e
  `templates/configuracoes/` (31 arquivos); e os três arquivos de
  teste de `apps/accounts/tests/`, lidos integralmente
  (1952 linhas no total).
- [../architecture/overview.md](../architecture/overview.md),
  [../architecture/module-map.md](../architecture/module-map.md),
  [../architecture/multitenancy.md](../architecture/multitenancy.md),
  [../security/overview.md](../security/overview.md),
  [../security/authorization-model.md](../security/authorization-model.md),
  [../security/data-scope.md](../security/data-scope.md) e
  [../security/authorization-matrix.md](../security/authorization-matrix.md)
  não foram usados como prova de estado neste lote — eles são citados
  apenas para comparar o HEAD auditado diretamente com o alvo
  canônico, e suas próprias afirmações de código foram reconferidas
  pela leitura direta acima, não presumidas corretas.

## Convenção de estados

- **Implementado** — existe no código atual e o fluxo principal
  correspondente foi identificado. Isso não significa completo, seguro
  ou final.
- **Parcialmente implementado** — parte material do fluxo existe, mas
  faltam requisitos canônicos relevantes.
- **Planejado** — existe como direção canônica aprovada, mas o fluxo
  principal ainda não está implementado.
- **Não identificado** — nenhuma implementação correspondente foi
  identificada na auditoria.
- **Em aberto** — a própria regra funcional ou arquitetural ainda
  depende de decisão.

## Visão executiva

| Área | Estado | Resumo | Principal diferença para o alvo canônico |
| --- | --- | --- | --- |
| Plataforma SaaS | Parcialmente implementado | `Escritorio`, `Dominio`, `ConfiguracaoVisual`, `Plano` e `Assinatura` existem no schema público; leitura do plano é exibida em `apps.configuracoes` e `apps.dashboard` | Sem interface de produto para Platform Admin nem para gestão de plano além da leitura; na inspeção do HEAD, os models desses dois apps estão registrados apenas no Django Admin (`apps/saas_tenants/admin.py`, `apps/saas_billing/admin.py`), sem `views.py`/`urls.py`/`forms.py` em nenhum dos dois apps |
| Multitenancy | Implementado | Isolamento por schema via `django-tenants`, `TenantMainMiddleware` primeiro na pilha, `SHARED_APPS`/`TENANT_APPS` separados | Sem estratégia de segregação de arquivos por tenant nem testes automatizados de isolamento cross-tenant identificados |
| Accounts / autenticação | Parcialmente implementado | `auth.User` + `PerfilUsuario`; `login_view`/`logout_view` são as próprias views de sessão, sem decorator; views operacionais usam `@login_required`, rotas administrativas de `apps/configuracoes` usam `@requer_admin_escritorio` | Nenhuma rota, view ou template de alteração de senha foi identificado; `templates/configuracoes/index.html` exibe um `<button>` "Alterar senha" sem `href`/formulário/ação associada |
| Autorização | Parcialmente implementado | Kernel dinâmico (`PapelAcesso`, `UsuarioPapel`, `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`, `HabilitacaoUsuario`) implementado em `apps/accounts/permissoes.py`, com casos de teste em `apps/accounts/tests/` (86 testes, executados na implementação do WI-0001, resultado `OK`) | Clientes aplica o kernel de autorização completo no backend (`tem_permissao_modulo()`/`tem_habilitacao()`, WI-0001); Processos aplica `tem_permissao_modulo()` — autorização de módulo, sem habilitação granular por decisão de produto (WI-0004, [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)); os demais módulos operacionais (Tarefas, Agenda, Financeiro, Dashboard, Chat, Modelos, Laboratório) continuam com a lacuna registrada — nenhuma view desses módulos consulta esses helpers |
| Escopo de dados | Parcialmente implementado | Clientes aplica escopo de leitura (`todos`/`somente_seus`) por requisição em `lista`/`detalhe`/`inativos`, com autorização de mutação por responsabilidade (não-admin só edita/desativa/reativa clientes sob sua responsabilidade, mesmo com escopo de leitura `todos`) em `editar`/`desativar`/`reativar` (WI-0002); Processos aplica o mesmo padrão (leitura por `_processos_no_escopo`, mutação por `_processos_mutaveis`), constatado no código (WI-0005, `in_progress`); helpers de equipe em `apps/accounts/escopo.py` continuam não aplicados | Tarefas, Agenda, Financeiro, Dashboard, Chat e Modelos continuam sem nenhum `QuerySet` filtrado por responsável, equipe ou participação |
| [Dashboard](current-state/dashboard.md) | Parcialmente implementado | Agrega dados reais de Clientes, Processos, Tarefas, Agenda e Financeiro, sem mocks | Agregações cobrem o tenant inteiro, sem respeitar escopo nem autorização financeira do usuário que consulta |
| [Clientes](current-state/clientes.md) | Parcialmente implementado | CRUD funcional com `ativo`/`inativos`/`reativar`; autorização de módulo (`tem_permissao_modulo`) aplicada nas sete rotas, com `clientes_criar`/`clientes_editar` (`tem_habilitacao`) aplicadas em `novo`/`editar` (WI-0001); `Cliente.responsavel` obrigatório no schema, preenchido com `request.user` na criação por conta não-admin, selecionável apenas pelo Administrador do escritório; escopo de leitura `todos`/`somente_seus` por requisição em `lista`/`detalhe`/`inativos`; mutação (`editar`/`desativar`/`reativar`) restrita ao Administrador ou a `Cliente.responsavel == request.user`, independente do escopo de leitura; objeto fora do escopo aplicável retorna 404 (WI-0002) | Escopo por equipe ("da equipe") permanece apenas placeholder visual desabilitado, sem regra funcional nem persistência |
| [Processos](current-state/processos.md) | Parcialmente implementado | CRUD, movimentações, apensos (WI-0007); Fase A concluída com autorização binária de módulo (`tem_permissao_modulo`) aplicada nas nove rotas, sem habilitação granular por decisão de produto (WI-0004, commit `ece9ead`, [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)); escopo por `responsavel` e responsabilidade obrigatória constatados no código (WI-0005) | `ParteProcesso` implementa o modelo de três dimensões de PDR-0001/PDR-0011 (WI-0006), já substituído por PDR-0013; equipe não participa do escopo; WI-0005/WI-0006 seguem `in_progress` — ver nota de consistência no detalhe do módulo |
| [Tarefas](current-state/tarefas.md) | Parcialmente implementado | Criação de tarefa existe; na criação, `responsavel` recebe `request.user` sempre (`apps/tarefas/views.py::nova`); `TarefaForm` não expõe campo `responsavel`; status e reatribuição com preservação de `responsavel_original`/`status_original` no `POST` de edição | Delegação direta a outro usuário, prevista por PDR-0002, não está implementada; habilitação `tarefas_atribuir_outros` existe no kernel sem enforcement ou fluxo correspondente; campos `criador`/`atribuidor`/`destinatario_atribuicao`/`data_atribuicao` exigidos por PDR-0002 permanecem ausentes; notificação de conclusão prevista por PDR-0016 ainda não existe; sem escopo aplicado |
| [Agenda](current-state/agenda.md) | Parcialmente implementado | Compromissos manuais e vinculados a processo/cliente, filtros por data/status | Sem validação de integridade cliente-processo; sem escopo por responsável/participante aplicado; lembrete de 15 minutos previsto por PDR-0016 ainda não possui mecanismo de execução |
| [Financeiro](current-state/financeiro.md) | Parcialmente implementado | `LancamentoFinanceiro` e `CustaJudicial` existem; saldo de custas calculado no backend conforme PDR-0005 | Sem modalidade parcelado/recorrente; sem Solicitações nem Honorários como entidades próprias; sem distinção de acesso ao caixa geral |
| [Chat](current-state/chat.md) | Parcialmente implementado | Sala global única por tenant, mensagens funcionais | Conversas individuais e em grupo, previstas na especificação, não existem |
| [Modelos](current-state/modelos.md) | Parcialmente implementado | Cadastro manual, categoria/área do direito e importação de `.pdf`/`.docx` com extração de texto; acervo listado sem filtro por autoria | Sem versionamento ou integração com IA; autorização de módulo não aplicada; nível `somente_seus`/`todos` ainda presente no kernel apesar do novo alvo institucional; `modelos_editar_estilo` sem view correspondente |
| [IA / Laboratório](current-state/inteligencia-artificial.md) | Não identificado | `apps.laboratorio` é um shell visual com um model de placeholder | Nenhuma funcionalidade de IA jurídica implementada; pré-requisitos do PDR-0008 ainda não consolidados |
| [Configurações](current-state/configuracoes.md) | Parcialmente implementado | Perfil pessoal, gestão de usuários/equipes/permissões legadas protegida por `@requer_admin_escritorio` | Administração de `PapelAcesso`/habilitações sem interface; identidade visual sem rota de edição no tenant |
| Arquivos/anexos | Não identificado | Únicos uploads confirmados são avatar de usuário e identidade visual do escritório | Nenhum objeto interno (cliente, processo, tarefa etc.) possui campo de upload; sem estratégia de segregação por tenant |
| Testes | Parcialmente implementado | Casos de teste extensos do kernel em `apps/accounts/tests/`; Clientes cobre autorização, habilitação, escopo, responsabilidade e IDOR; Processos cobre autorização, escopo/responsabilidade, migrations, participantes e apensos, com evidências registradas nos respectivos WIs | Sem testes de autorização/escopo nos demais módulos operacionais e sem isolamento cross-tenant explícito; PDR-0013/PDR-0014 ainda não possuem código nem testes correspondentes |

## Plataforma e arquitetura

Constatações da leitura direta de `manage.py`, `config/urls.py`,
`config/asgi.py`, `config/wsgi.py`, `config/settings/base.py`,
`config/settings/development.py`, `config/settings/production.py`,
`requirements/*.txt`, `package.json` e `tailwind.config.js`:

- Django 5.2 (`requirements/base.txt`: `django>=5.2,<5.3`), aplicação
  única (`manage.py`, `config/`), sem microserviços.
- PostgreSQL via `django_tenants.postgresql_backend`
  (`config/settings/base.py`).
- `django-tenants==3.10.1` (`requirements/base.txt`), primeiro item de
  `SHARED_APPS`; `TenantMainMiddleware` é o primeiro item de
  `MIDDLEWARE`; `DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]`.
- `ROOT_URLCONF = "config.urls"` inclui as rotas de `apps.accounts`,
  `apps.dashboard`, `apps.processos`, `apps.clientes`, `apps.tarefas`,
  `apps.financeiro`, `apps.agenda`, `apps.chat`, `apps.modelos`,
  `apps.laboratorio` e `apps.configuracoes`, além de `admin/`.
- Templates server-side (`django.template.backends.django.DjangoTemplates`),
  sem DRF nem framework SPA — `package.json` declara apenas
  `tailwindcss` como dependência de desenvolvimento, com os scripts
  `build`/`watch` compilando `static/css/input.css` em
  `static/css/output.css`.
- `MEDIA_ROOT`/`MEDIA_URL` e `STATIC_ROOT`/`STATIC_URL` apontam para
  diretórios locais únicos por instalação, sem particionamento por
  tenant.
- `config/settings/production.py` acrescenta `SECURE_BROWSER_XSS_FILTER`,
  `SECURE_CONTENT_TYPE_NOSNIFF` e `X_FRAME_OPTIONS = "DENY"` sobre
  `base.py`; nenhuma configuração de `SECURE_SSL_REDIRECT` ou
  `SESSION_COOKIE_SECURE` foi identificada.
- 12 migrations em `apps/accounts`, com histórico de transição de
  grupos legados (`gerente`/`advogado`) para o papel técnico
  `limitado`, e introdução do kernel dinâmico de permissões e
  habilitações (`0007`–`0011`).
- Frontend build via Tailwind CSS 3 (`npm run build`/`npm run watch`),
  sem `django-compressor`.

### Dependências principais identificadas

Bibliotecas Python declaradas em `requirements/*.txt`, confirmadas
pela leitura direta desses arquivos:

- `django>=5.2,<5.3`;
- `django-tenants==3.10.1`;
- `psycopg2-binary==2.9.12`;
- `pillow==12.2.0`;
- `python-dotenv==1.2.2`;
- `pypdf==6.14.2` e `python-docx==1.2.0` — usadas por
  `apps/modelos/services.py::extrair_texto_documento` para extrair
  texto de arquivos `.pdf`/`.docx` enviados na importação de modelos
  de peça; são bibliotecas de processamento local de arquivo, não
  integrações com serviço externo;
- `django-debug-toolbar` (apenas em `requirements/development.txt`);
- `gunicorn` (apenas em `requirements/production.txt`).

Ferramenta de build de frontend: `tailwindcss` (CLI, via `npm`),
declarada em `package.json` como única dependência.

### Integrações com serviços externos

Não foi identificada integração ativa com serviço externo (API de
IA, storage em nuvem, fila de mensageria, provedor de e-mail,
gateway de pagamento) na leitura direta de `requirements/*.txt`,
`config/settings/*.py` e dos arquivos funcionais de todos os apps
auditados. Nenhuma dependência de Celery, Redis, Django Channels,
RabbitMQ ou Kafka foi encontrada em `requirements/`. O único indício
de intenção de tempo real é um comentário em `apps/chat/models.py`
("Futuramente: implementar WebSocket via Django Channels para
mensagens em tempo real"), que não corresponde a nenhuma dependência
instalada nem a código funcional. Esta seção não afirma que nunca
haverá integração externa — apenas que nenhuma foi identificada na
inspeção realizada.

## Multitenancy

Detalhado em [../architecture/multitenancy.md](../architecture/multitenancy.md).

### Implementado

- Resolução de tenant por domínio, via
  `django_tenants.middleware.main.TenantMainMiddleware`, primeiro
  middleware em `config/settings/base.py`.
- Isolamento por schema PostgreSQL: `Escritorio(TenantMixin)` com
  `auto_create_schema = True`.
- `SHARED_APPS` (`django_tenants`, `apps.saas_tenants`,
  `apps.saas_billing`, apps padrão) separado de `TENANT_APPS`
  (`apps.accounts`, `apps.dashboard`, `apps.clientes`,
  `apps.processos`, `apps.tarefas`, `apps.financeiro`, `apps.agenda`,
  `apps.chat`, `apps.modelos`, `apps.laboratorio`,
  `apps.configuracoes`).
- Nenhuma `ForeignKey` cruzando um model de `TENANT_APPS` com um
  registro de outro schema foi identificada.
- `django.contrib.auth` está listado tanto em `SHARED_APPS` quanto em
  `TENANT_APPS` — `auth.User`/`auth.Group` são sincronizados também no
  schema de cada tenant.

### Lacunas ou limites atuais

- Nenhuma estratégia de segregação de arquivos por tenant identificada
  no código; `MEDIA_ROOT`/`MEDIA_URL` apontam para um diretório local
  único, sem particionamento por schema.
- Nenhum teste automatizado afirmando explicitamente isolamento de
  dados entre schemas de tenants diferentes foi identificado; os
  testes existentes em `apps/accounts/tests/` cobrem o kernel de
  autorização dentro de um schema, não isolamento cross-tenant.
- Nenhum mecanismo de autorização dedicado ao Platform Admin foi
  identificado na inspeção realizada; `apps/saas_tenants/admin.py` e
  `apps/saas_billing/admin.py` registram `Escritorio`, `Dominio`,
  `ConfiguracaoVisual`, `Plano` e `Assinatura` no Django Admin padrão
  (`django.contrib.admin`), e nenhum `views.py`/`urls.py` próprio foi
  encontrado em nenhum dos dois apps.
- Isolamento de schema não resolve, por si, a autorização entre
  usuários do mesmo tenant — essa camada depende do kernel de
  `apps.accounts`, tratado na seção seguinte.

## Accounts e autorização

Resumo, com detalhe completo em
[../security/authorization-model.md](../security/authorization-model.md).

- `auth.User` é o model de usuário padrão do Django;
  `PerfilUsuario` (`OneToOneField`) carrega `nome_completo`, `cargo`
  (descritivo), `avatar` e a flag `is_admin_escritorio`.
- O kernel dinâmico existe e é resolvido por
  `apps/accounts/permissoes.py`: `PapelAcesso`, `UsuarioPapel`,
  `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`,
  `HabilitacaoUsuario`. A leitura direta de
  `_permissao_efetiva_com_contexto()` e
  `_habilitacao_efetiva_com_contexto()` confirma a ordem de
  precedência admin → individual (`PermissaoUsuario`/`HabilitacaoUsuario`)
  → união de papéis ativos (`UsuarioPapel`) → fallback de
  `auth.Group` → negação padrão; múltiplos papéis por usuário são
  agregados pelo maior nível entre os papéis concedentes
  (`_maior_nivel()`).
- `usuario_admin_escritorio()`, em `apps/accounts/decorators.py`,
  verifica exclusivamente `PerfilUsuario.is_admin_escritorio=True`
  combinado com `is_active=True` — o próprio docstring da função no
  código lido afirma "Único caminho: PerfilUsuario.is_admin_escritorio=True
  com is_active=True", sem atalho por `is_superuser` nem por grupo.
  Este ponto diverge das docstrings e comentários de
  `apps/accounts/tests/test_admin_tenant.py` (lidos integralmente
  nesta auditoria), que descrevem um "kernel atual" com três caminhos
  de admissão, incluindo `is_superuser` e ausência de checagem de
  `is_active`; a divergência já está registrada em
  [../security/authorization-model.md](../security/authorization-model.md)
  e não é resolvida por este documento. Resultado de execução dos
  testes não verificado nesta auditoria.
- Fallback legado: quando o usuário não possui nenhum `UsuarioPapel`,
  `tipo_conta_usuario()` resolve por `auth.Group` (`limitado`,
  `financeiro`).
- Administrador do escritório é avaliado antes de qualquer
  `PermissaoUsuario` individual — concede acesso total ao módulo no
  maior nível técnico configurado.
- Enforcement nas views, por módulo: ver
  [authorization-matrix.md#resumo-dos-módulos](../security/authorization-matrix.md#resumo-dos-módulos)
  para o estado consolidado (Clientes — WI-0001/WI-0002 — e Processos —
  WI-0004 — com autorização de módulo aplicada; demais módulos
  operacionais ainda apenas com `@login_required`; Processos sem
  `tem_habilitacao()` por decisão de produto,
  [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)).
  Distinção adicional não coberta pela matriz:
  `apps/accounts/views.py::login_view`/`logout_view` não usam decorator
  de autorização (views de entrada/saída de sessão); em
  `apps/configuracoes/views.py`, `index`/`editar_perfil` usam apenas
  `@login_required`, enquanto `novo_usuario`, `equipes`, `nova_equipe`,
  `editar_equipe`, `equipe_membros`, `remover_membro_equipe`,
  `alternar_gerente_equipe`, `permissoes` e `editar_escritorio` usam
  `@requer_admin_escritorio` — controle binário administrador/não
  administrador, distinto do kernel dinâmico, e não consumido pela
  própria tela `permissoes` que configura esse kernel.
- **Alteração de senha**: nenhuma rota, view ou form de alteração de
  senha foi identificado em `apps/accounts/urls.py`,
  `apps/accounts/views.py`, `apps/accounts/forms.py` ou em
  `templates/auth/` (que contém apenas `login.html`). Uma busca por
  `PasswordChange|password_change|set_password|change_password|senha`
  em `apps`, `config` e `templates` não retornou nenhuma rota ou view
  correspondente. `templates/configuracoes/index.html` contém
  `<button class="btn-secondary text-sm">Alterar senha</button>`, sem
  `id`, `href`, `action` de formulário ou atributo `data-*`; o
  template não possui bloco `<script>` próprio, e o único script
  global do projeto, `static/js/main.js`, só liga handlers a
  elementos com os atributos `sidebar-toggle`, `data-tab`,
  `data-view-toggle` ou `data-dismiss-alert` — nenhum presente nesse
  botão. Registra-se, portanto, que nenhum handler foi identificado
  para esse botão nos arquivos inspecionados, não que seja
  tecnicamente impossível existir um em outro lugar não lido. O mesmo
  template também contém um botão de remoção de usuário (ícone de
  lixeira) igualmente sem `href`/ação associada.
- **Interface e autorização**: `templates/components/sidebar.html`
  lista todos os itens de módulo (Painel, Processos, Laboratório,
  Modelos, Tarefas, Financeiro, Chat, Agenda, Clientes,
  Configurações) como links incondicionais, sem nenhuma tag
  `{% if %}` que os condicione a `tem_permissao_modulo` ou
  equivalente — qualquer usuário autenticado do tenant vê todos os
  itens na sidebar. Em `templates/configuracoes/index.html`, apenas o
  botão "Novo usuário", o card "Administração" e o botão "Editar
  dados do escritório" são condicionados a `usuario_e_admin_escritorio`;
  a listagem completa de usuários do tenant (nome, papel, cargo,
  equipes) é renderizada sem essa condição, para qualquer usuário
  autenticado.

## Escopo de dados

Resumo, com detalhe completo em
[../security/data-scope.md](../security/data-scope.md).

- `apps/accounts/escopo.py` define helpers de consulta de equipes
  (`equipes_do_usuario`, `equipes_gerenciadas_pelo_usuario`,
  `equipes_descendentes`, entre outros) e constantes de escopo. O
  próprio módulo declara, em docstring, que esses helpers "ainda não
  aplicam filtros nos módulos operacionais".
- Apenas `equipe_padrao_para_usuario()` é consumida fora de
  `escopo.py`, e somente para pré-preencher `Processo.equipe` na
  criação — não filtra nenhuma leitura.
- **Clientes (WI-0002)** é o primeiro módulo operacional a aplicar
  escopo de dados: `apps/clientes/views.py` lê
  `nivel_acesso_modulo(request.user, "clientes")` para resolver, por
  requisição, um escopo efetivo de leitura (`todos`/`somente_seus`),
  ajustável pelo parâmetro `?escopo=` sem estado persistente (nunca
  amplia acima do nível máximo autorizado; um valor ausente usa o
  padrão, um valor presente inválido — incluindo string vazia — é
  negado com 403). Distinção aplicada: `"todos"` é escopo de
  **visualização** (`lista`/`detalhe`/`inativos` alcançam qualquer
  cliente autorizado do tenant), não autorização de **mutação** — um
  usuário não administrador, mesmo com nível máximo `todos`, só alcança
  `editar`/`desativar`/`reativar` sobre clientes de sua própria
  responsabilidade (`Cliente.responsavel == request.user`); apenas o
  Administrador do escritório muta qualquer cliente. Um cliente fora do
  escopo aplicável à operação retorna 404 (nunca carregado livremente e
  validado depois). `Cliente.responsavel` é obrigatório no schema desde
  o WI-0002; reatribuição de responsável é restrita ao Administrador do
  escritório, com seleção limitada a usuários ativos do tenant atual.
- Nenhum outro módulo operacional (`apps.processos`, `apps.tarefas`,
  `apps.agenda`, `apps.financeiro`, `apps.dashboard`, `apps.modelos`)
  filtra listagens por `responsavel`, `equipe`, `participantes` ou
  `criado_por`, nem carrega objetos de detalhe/edição/exclusão com
  condição de posse — continuam usando
  `get_object_or_404(Model, pk=pk, ...)`, no máximo com uma condição de
  estado (`ativo=True`, `status=...`).
- O campo `nivel` (nível de acesso técnico atual) é resolvido pelo
  kernel; Clientes agora o lê (`nivel_acesso_modulo`) para compor o
  escopo de leitura, conforme acima — nenhum outro módulo operacional o
  lê para filtrar um `QuerySet`.
- Escopo por equipe ("da equipe") permanece sem nenhuma regra
  funcional em qualquer módulo, incluindo Clientes — existe apenas como
  opção visualmente desabilitada ("Em breve") em
  `templates/clientes/lista.html`/`inativos.html` e em
  `templates/configuracoes/permissoes.html`, sem valor persistido.
- Principal risco intra-tenant já documentado: um usuário autenticado
  do tenant pode, nas rotas de módulos ainda sem escopo aplicado,
  carregar por identificador registros existentes no schema ativo sem
  filtro de responsabilidade, equipe ou escopo — ver
  [../security/overview.md](../security/overview.md#principais-lacunas-constatadas).

## Estado por módulo

O detalhamento por módulo (estado, implementado no HEAD, diferenças
para o alvo canônico, dependências/bloqueios) vive em arquivos
próprios em [current-state/](current-state/), um por módulo, para que
uma tarefa localizada em um módulo carregue apenas o detalhe desse
módulo. A tabela ["Visão executiva"](#visão-executiva) acima resume
todos os módulos e linka para cada detalhe:

- [current-state/dashboard.md](current-state/dashboard.md)
- [current-state/clientes.md](current-state/clientes.md)
- [current-state/processos.md](current-state/processos.md)
- [current-state/tarefas.md](current-state/tarefas.md)
- [current-state/agenda.md](current-state/agenda.md)
- [current-state/financeiro.md](current-state/financeiro.md) (inclui o
  detalhamento por área funcional)
- [current-state/chat.md](current-state/chat.md)
- [current-state/modelos.md](current-state/modelos.md)
- [current-state/inteligencia-artificial.md](current-state/inteligencia-artificial.md)
  (inclui o estado por área de IA, incluindo Modelos e honorários)
- [current-state/configuracoes.md](current-state/configuracoes.md)

## Testes

Os três arquivos de teste de `apps/accounts/tests/` foram lidos
integralmente na auditoria original (`a543c3f`); execução não
verificada naquele lote. A implementação do WI-0001 (commit `da19001`)
acrescentou `apps/clientes/tests/test_autorizacao.py` e executou
`python manage.py test apps.clientes` (26 testes) e `python manage.py
test apps.accounts` (86 testes), ambas com resultado `OK` — evidência
completa registrada em
`docs/delivery/work/WI-0001-autorizacao-backend-clientes.md`. A
implementação do WI-0002 (commit `07675f7`) acrescentou
`apps/clientes/tests/test_escopo.py` (31 testes) e adaptou a fixture
`_cliente()` de `test_autorizacao.py` ao novo schema (`responsavel`
obrigatório), sem alterar nenhuma asserção existente; executou `python
manage.py test apps.clientes` (57 testes: 26 do WI-0001 + 31 do
WI-0002) e `python manage.py test apps.accounts` (86 testes), ambas com
resultado `OK` — evidência completa registrada em
`docs/delivery/work/WI-0002-escopo-responsabilidade-clientes.md`. A
implementação do WI-0004 (commit `ece9ead`)
acrescentou `apps/processos/tests/test_autorizacao.py` (30 testes) e
executou `python manage.py test apps.processos` (30 testes), `python
manage.py test apps.accounts` (86 testes) e `python manage.py test
apps.clientes` (57 testes), todas com resultado `OK` — evidência
completa registrada em
`docs/delivery/work/WI-0004-autorizacao-modulo-processos.md`. As
demais afirmações desta seção sobre `apps/accounts/tests/` continuam
descrevendo o código-fonte lido na auditoria original, sem nova leitura
nesta revisão.

- **Cobertura identificada**: `apps/accounts/tests/` reúne três
  arquivos (`test_admin_tenant.py`, 342 linhas;
  `test_permissoes_kernel.py`, 887 linhas; `test_interacoes_kernel.py`,
  723 linhas; 1952 linhas no total), construídos sobre
  `TenantTestCase` do django-tenants. Os casos de teste presentes
  cobrem a resolução do kernel de permissões e habilitações
  (`permissao_efetiva()`, `habilitacao_efetiva()`, precedência
  admin → individual → papel → grupo legado, múltiplos papéis,
  overrides). `test_interacoes_kernel.py` também contém casos de
  fumaça HTTP (`TestSmokePagesAdmin`, `TestSmokePagesAdvogado`) cuja
  única asserção é a ausência de status HTTP 500 em um conjunto fixo
  de rotas, não a correção do resultado de autorização. Testes não
  executados nesta auditoria.
- **Divergência entre docstrings de teste e código lido**:
  `test_admin_tenant.py` e `test_permissoes_kernel.py` documentam,
  em comentários e docstrings, um "kernel atual (pré-2.1C1B)" no qual
  `usuario_admin_escritorio()` concederia acesso via `is_superuser`
  e sem checar `is_active`, e no qual `permissao_efetiva()` "não
  consulta UsuarioPapel". A leitura direta de
  `apps/accounts/decorators.py::usuario_admin_escritorio` e de
  `apps/accounts/permissoes.py::_permissao_efetiva_com_contexto`
  nesta auditoria não corresponde a essas descrições: o código atual
  verifica exclusivamente `is_admin_escritorio` combinado com
  `is_active`, sem checar `is_superuser`, e já consulta
  `UsuarioPapel`, agregando múltiplos papéis. Vários casos de teste
  desses dois arquivos usam um helper `assertFuturo()` que documenta
  explicitamente essa expectativa de falha sob o "kernel atual"
  descrito no comentário. Esta auditoria não executa os testes e não
  afirma se essas asserções passam ou falham sob o código lido;
  registra apenas que a documentação em comentário desses dois
  arquivos descreve um estado do kernel anterior ao código
  efetivamente lido em `apps/accounts/decorators.py` e
  `apps/accounts/permissoes.py`.
- **Cobertura identificada em Clientes**:
  `apps/clientes/tests/test_autorizacao.py` (26 testes, WI-0001, commit
  `da19001`), sobre o mesmo padrão `TenantTestCase`. Cobre: usuário
  autenticado sem autorização de módulo negado (403) nas sete rotas,
  com ausência de mutação comprovada em `novo`/`editar`/`desativar`/
  `reativar`; usuário com módulo autorizado preservando o comportamento
  HTTP das sete rotas; usuário com módulo mas sem `clientes_criar`
  negado em `novo` (403, sem criar `Cliente`); usuário com módulo mas
  sem `clientes_editar` negado em `editar` (403, sem alterar
  `Cliente`).
  `apps/clientes/tests/test_escopo.py` (31 testes, WI-0002, commit
  `07675f7`) acrescenta: listagem/inativos por `somente_seus`/`todos`/
  Administrador; detalhe/editar/desativar/reativar de cliente próprio
  funcionando e de cliente alheio retornando 404 sem alterar o objeto;
  um usuário não administrador com nível máximo `todos` visualizando
  (`lista`/`detalhe`) qualquer cliente do tenant mas recebendo 404 em
  `editar`/`desativar`/`reativar` de cliente alheio; escalonamento de
  escopo (`?escopo=todos` acima do máximo, `?escopo=` vazio,
  `?escopo=da_equipe`) negado com 403; criação por conta limitada
  forçando `responsavel = request.user` mesmo com `POST` adulterado;
  edição por conta limitada preservando o responsável real e exibindo-o
  corretamente (nunca o editor); reatribuição de responsável pelo
  Administrador, incluindo rejeição de usuário inativo; impossibilidade
  de persistir `Cliente` sem `responsavel` (`IntegrityError` a nível de
  schema). Não cobre isolamento cross-tenant explícito (dois tenants na
  mesma execução) — decisão registrada no próprio WI-0002 para não
  ampliar desnecessariamente o escopo do item, apoiada na garantia
  estrutural de schema-per-tenant já coberta em
  [../architecture/multitenancy.md](../architecture/multitenancy.md).
- **Cobertura identificada em Processos**:
  `apps/processos/tests/test_autorizacao.py` (30 testes, WI-0004),
  sobre o mesmo padrão `TenantTestCase`. Cobre: usuário autenticado sem
  autorização de módulo negado (403) nas nove rotas (`lista`,
  `detalhe`, `arquivados`, `novo`, `editar`, `arquivar`, `reabrir`,
  `adicionar_movimentacao`, `adicionar_parte`), com ausência de
  mutação comprovada em todas as operações de escrita; usuário com
  módulo autorizado (via papel dinâmico, sem nenhuma
  `HabilitacaoPapel`) preservando o comportamento HTTP das nove rotas,
  incluindo criar/editar/adicionar movimentação sem
  `processos_criar`/`processos_editar`/`processos_andamento_adicionar`
  — comportamento esperado nesta versão, conforme
  [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md);
  Administrador do escritório autorizado sem depender de
  `UsuarioPapel`/`PermissaoPapel`. Não cobre escopo de dados,
  habilitação granular nem autorização sobre objeto (IDOR
  intra-tenant) — fora de escopo do WI-0004, por decisão de produto e
  por fase futura, respectivamente.
- **Cobertura parcial identificada**: `apps/clientes` — autorização de
  módulo, das duas habilitações existentes (`clientes_criar`,
  `clientes_editar`), escopo de dados por responsável e autorização
  sobre objeto (IDOR intra-tenant) são testados diretamente sobre as
  views. `apps/processos` — autorização de módulo é testada
  diretamente sobre as nove views auditadas em WI-0004
  (`test_autorizacao.py`); habilitação granular não é testada como
  exigida, por decisão de produto (PDR-0010); escopo de dados por
  responsável e autorização sobre objeto são testados em
  `test_escopo.py` (WI-0005); apensos são testados em
  `test_apensos.py` (WI-0007). Habilitação de responsabilidade
  delegável (PDR-0014) e o modelo simplificado de Partes (PDR-0013)
  ainda não têm código nem teste correspondente. As demais views
  operacionais (Tarefas, Agenda, Financeiro, Dashboard, Chat, Modelos,
  Laboratório) permanecem sem teste de autorização nem de escopo.
- **Não foi identificado teste específico** para: escopo de dados nos
  módulos operacionais além de Clientes e Processos (Tarefas, Agenda,
  Financeiro, Dashboard, Chat, Modelos); autorização sobre objeto
  específico (IDOR intra-tenant) fora de Clientes, Processos e
  `apps/accounts`; isolamento cross-tenant explícito em qualquer
  módulo; integridade cliente-processo em Tarefas/Agenda; regras de
  negócio do Financeiro (modalidades, previsto/realizado) fora do
  cálculo de saldo de custas.
- Uma busca por `find apps -type f \( -name "test_*.py" -o -name
  "tests.py" \)` no HEAD `ece9ead` (após a implementação do WI-0004)
  retornava os três arquivos de `apps/accounts/tests/`, os dois
  arquivos de `apps/clientes/tests/` (`test_autorizacao.py`,
  `test_escopo.py`) e um arquivo de `apps/processos/tests/`
  (`test_autorizacao.py`). No HEAD atual (`cd5f7bf`), `apps/processos/tests/`
  tem sete arquivos: `test_autorizacao.py`, `test_escopo.py`,
  `test_migrations.py`, `test_participantes.py`,
  `test_migrations_participantes.py`, `test_apensos.py` e
  `test_migrations_apensos.py`; `apps/configuracoes/tests/` também contém
  `test_perda_acesso_processos.py`. Os demais apps não foram reauditados
  quanto a arquivos de teste nesta revisão.

## Dívida e divergências conhecidas

| Área | Divergência constatada | Fonte canônica relacionada |
| --- | --- | --- |
| Autorização nas views | Kernel dinâmico implementado e testado (`apps/accounts/tests/`, 86 testes, `OK`); `apps/clientes/views.py` já o consulta, incluindo escopo de dados (WI-0001, commit `da19001`; WI-0002, commit `07675f7`); `apps/processos/views.py` consulta autorização de módulo, sem habilitação granular por decisão de produto (WI-0004, [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)); as demais views operacionais (Tarefas, Agenda, Financeiro, Dashboard, Chat, Modelos, Laboratório) continuam protegidas apenas por `@login_required` | [../security/authorization-model.md](../security/authorization-model.md), [PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md), [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md) |
| Alteração de senha ausente | `templates/configuracoes/index.html` exibe um botão "Alterar senha" sem `href`/ação de formulário; nenhuma rota, view ou form correspondente foi identificado em `apps/accounts` | [configuracoes.md](../product/modules/configuracoes.md) |
| Escopo de dados | Clientes (WI-0002) e Processos (WI-0005) filtram `QuerySet` por responsável; Tarefas, Agenda, Financeiro, Dashboard e Modelos continuam sem filtro; helpers de equipe existem mas não são consumidos por nenhum módulo, incluindo Clientes e Processos | [../security/data-scope.md](../security/data-scope.md) |
| Partes de processo | `ParteProcesso` implementa o modelo de três dimensões de PDR-0001/PDR-0011 (WI-0006); esse modelo foi substituído por [PDR-0013](../product/decisions/PDR-0013-partes-processo-modelo-simplificado.md), que aprova um campo único de papel e advogado em texto livre — o código está mais elaborado que o alvo canônico atual, não menos; Work Item de simplificação pendente | [PDR-0013](../product/decisions/PDR-0013-partes-processo-modelo-simplificado.md), [../architecture/module-map.md](../architecture/module-map.md) |
| Responsabilidade delegável e integrantes de processo | `processos_atribuir_responsavel` e a relação de integrante habilitado (`usuario_processos`) aprovados em PDR-0014 não existem no kernel nem no código; reatribuição de responsável continua exclusiva do Administrador | [PDR-0014](../product/decisions/PDR-0014-responsavel-integrantes-processos.md) |
| Nível de acesso em Modelos | `modelos` permanece em `NIVEIS_POR_MODULO` com `somente_seus`/`todos`, apesar da decisão de 2026-08-31 de tratá-lo como Chat/Gerir (sem nível); nenhuma view lê esse nível para Modelos hoje, então a divergência é apenas de configuração de kernel, não de comportamento observável | [modelos.md](../product/modules/modelos.md), [../security/authorization-matrix.md](../security/authorization-matrix.md) |
| Delegação de tarefas | `Tarefa` não possui `criador`/`atribuidor`/`destinatario_atribuicao`/`data_atribuicao`; sem rota de atribuição a outro usuário; sem status `cancelada` | [PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md), [../security/authorization-matrix.md](../security/authorization-matrix.md) |
| Categoria de custas no financeiro geral | `LancamentoFinanceiro.CATEGORIA_CHOICES` inclui `"custa_judicial"`, apesar de PDR-0003 exigir área própria (já existente como `CustaJudicial`) | [PDR-0003](../product/decisions/PDR-0003-areas-funcionais-financeiro.md), [../architecture/module-map.md](../architecture/module-map.md) |
| Integridade cliente-processo | `cliente`/`processo` são campos independentes em `TarefaForm`/`CompromissoForm`; combinação inconsistente por `POST` não é rejeitada | [clientes.md](../product/modules/clientes.md), [../security/data-scope.md](../security/data-scope.md) |
| Financeiro futuro | Solicitações e Honorários não modelados como entidades próprias; recorrência não implementada | [PDR-0006](../product/decisions/PDR-0006-solicitacoes-financeiras.md), [PDR-0007](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md), [PDR-0015](../product/decisions/PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md), OPEN-001 |
| Hierarquia de equipes | `Equipe.equipe_pai` e `equipes_descendentes()` já existem no código, mas nenhuma view os consome; decisão de produto sobre hierarquia continua em aberto | [equipes.md](../product/modules/equipes.md), [../security/data-scope.md](../security/data-scope.md) |
| Identidade visual | `ConfiguracaoVisual` administrável apenas via Django Admin no schema público, sem rota tenant identificada | [configuracoes.md](../product/modules/configuracoes.md), [../security/authorization-matrix.md](../security/authorization-matrix.md) |
| Documentação de teste desatualizada | Docstrings de `test_admin_tenant.py`/`test_permissoes_kernel.py` descrevem um kernel anterior ("não consulta UsuarioPapel", `is_superuser` concede admin) que não corresponde ao código atual de `apps/accounts/permissoes.py`/`decorators.py` | [../security/authorization-model.md](../security/authorization-model.md) |

## Decisões em aberto que afetam o estado

- **OPEN-001** — periodicidades financeiras da primeira versão. Afeta a
  modelagem de recorrência e parcelamento no Financeiro, hoje não
  implementada.
Nenhum outro ponto em aberto explícito foi identificado nos documentos
canônicos além de OPEN-001.

## Referências

- [current-state/](current-state/) — detalhe por módulo
- [../product/](../product/)
- [../architecture/](../architecture/)
- [../security/](../security/)
- [roadmap.md](roadmap.md)
