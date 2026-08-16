---
title: Estado atual do produto
status: canonical
owner: delivery
last_reviewed: 2026-08-16
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
- Commit HEAD auditado: `da19001` — "feat(clientes): aplicar
  autorização de módulo e habilitação nas views".
- Data da revisão: 2026-08-16.
- Esta revisão é incremental: a leitura completa, arquivo por arquivo,
  descrita abaixo permanece a realizada em `a543c3f`. Entre `a543c3f` e
  `da19001`, a única mudança de código funcional foi a implementação do
  WI-0001 (`apps/clientes/views.py` e a criação de
  `apps/clientes/tests/`), confirmada por `git diff a543c3f da19001`;
  as seções "Visão executiva", "Accounts e autorização", "Clientes" e
  "Testes" foram atualizadas para refletir essa mudança — as demais
  seções continuam válidas sem nova leitura nesta revisão.
- `AGENTS.md` não foi usado como fonte para este documento, apenas
  observado como arquivo não rastreado presente no diretório de
  trabalho.
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
| Autorização | Parcialmente implementado | Kernel dinâmico (`PapelAcesso`, `UsuarioPapel`, `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`, `HabilitacaoUsuario`) implementado em `apps/accounts/permissoes.py`, com casos de teste em `apps/accounts/tests/` (86 testes, executados na implementação do WI-0001, resultado `OK`) | Clientes já aplica o kernel de autorização no backend (`tem_permissao_modulo()`/`tem_habilitacao()`, WI-0001); os demais módulos operacionais (Processos, Tarefas, Agenda, Financeiro, Dashboard, Chat, Modelos, Laboratório) continuam com a lacuna registrada — nenhuma view fora de Clientes/`apps/accounts`/`apps/configuracoes` consulta esses helpers |
| Escopo de dados | Não identificado | Helpers de equipe existem em `apps/accounts/escopo.py`, mas o próprio módulo declara que ainda não filtram nada | Nenhum módulo operacional filtra `QuerySet` por responsável, equipe ou participação |
| Dashboard | Parcialmente implementado | Agrega dados reais de Clientes, Processos, Tarefas, Agenda e Financeiro, sem mocks | Agregações cobrem o tenant inteiro, sem respeitar escopo nem autorização financeira do usuário que consulta |
| Clientes | Parcialmente implementado | CRUD funcional com `ativo`/`inativos`/`reativar`; vínculo `responsavel` preenchido na criação; autorização de módulo (`tem_permissao_modulo`) aplicada nas sete rotas, com `clientes_criar`/`clientes_editar` (`tem_habilitacao`) aplicadas em `novo`/`editar` (WI-0001) | Escopo de dados por `Cliente.responsavel`/equipe/`nivel` ainda não aplicado em listagem, detalhe ou carregamento por `pk` — autorização sobre objeto/IDOR intra-tenant não resolvida |
| Processos | Parcialmente implementado | CRUD, movimentações, `ParteProcesso` (campo único `tipo`), `equipe` na criação | `ParteProcesso` não implementa as três dimensões de PDR-0001 (vínculo, posição estrutural, qualificação processual); sem escopo aplicado |
| Tarefas | Parcialmente implementado | Criação de tarefa existe; na criação, `responsavel` recebe `request.user` sempre (`apps/tarefas/views.py::nova`); `TarefaForm` não expõe campo `responsavel`; status e reatribuição com preservação de `responsavel_original`/`status_original` no `POST` de edição | Delegação direta a outro usuário, prevista por PDR-0002, não está implementada; habilitação `tarefas_atribuir_outros` existe no kernel sem enforcement ou fluxo correspondente; campos `criador`/`atribuidor`/`destinatario_atribuicao`/`data_atribuicao` exigidos por PDR-0002 permanecem ausentes; sem escopo aplicado |
| Agenda | Parcialmente implementado | Compromissos manuais e vinculados a processo/cliente, filtros por data/status | Sem validação de integridade cliente-processo; sem escopo por responsável/participante aplicado |
| Financeiro | Parcialmente implementado | `LancamentoFinanceiro` e `CustaJudicial` existem; saldo de custas calculado no backend conforme PDR-0005 | Sem modalidade parcelado/recorrente; sem Solicitações nem Honorários como entidades próprias; sem distinção de acesso ao caixa geral |
| Chat | Parcialmente implementado | Sala global única por tenant, mensagens funcionais | Conversas individuais e em grupo, previstas na especificação, não existem |
| Modelos | Parcialmente implementado | Cadastro manual e importação de `.pdf`/`.docx` com extração de texto | Sem versionamento, categorias ou integração com IA; `modelos_editar_estilo` sem view correspondente |
| IA / Laboratório | Não identificado | `apps.laboratorio` é um shell visual com um model de placeholder | Nenhuma funcionalidade de IA jurídica implementada; pré-requisitos do PDR-0008 ainda não consolidados |
| Configurações | Parcialmente implementado | Perfil pessoal, gestão de usuários/equipes/permissões legadas protegida por `@requer_admin_escritorio` | Administração de `PapelAcesso`/habilitações sem interface; identidade visual sem rota de edição no tenant |
| Arquivos/anexos | Não identificado | Únicos uploads confirmados são avatar de usuário e identidade visual do escritório | Nenhum objeto interno (cliente, processo, tarefa etc.) possui campo de upload; sem estratégia de segregação por tenant |
| Testes | Parcialmente implementado | Casos de teste extensos do kernel de permissões em `apps/accounts/tests/` (1952 linhas, 3 arquivos); execução não verificada nesta auditoria | Sem testes de escopo, de autorização por objeto ou de isolamento cross-tenant fora de `apps/accounts` |

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
- Enforcement nas views: `apps/clientes/views.py` agora consulta
  `tem_permissao_modulo(user, "clientes")` nas sete rotas (`lista`,
  `detalhe`, `novo`, `editar`, `desativar`, `inativos`, `reativar`) e
  `tem_habilitacao()` em `novo` (`clientes_criar`) e `editar`
  (`clientes_editar`), negando com `raise PermissionDenied` antes de
  qualquer leitura ou mutação, conforme WI-0001 (commit `da19001`).
  Fora de `apps/clientes`, `tem_permissao_modulo()`/`tem_habilitacao()`
  continuam ausentes de `apps/processos`, `apps/tarefas`,
  `apps/agenda`, `apps/financeiro`, `apps/dashboard`, `apps/chat`,
  `apps/modelos`, `apps/laboratorio` e `apps/configuracoes` — presentes
  apenas em `apps/accounts/permissoes.py`, em `apps/clientes/views.py`
  e em `apps/configuracoes/views.py::permissoes` (tela que configura o
  kernel, sem consumi-lo para proteger a própria tela). Classificação
  exata das views lidas: `apps/accounts/views.py::login_view`/
  `logout_view` não usam nenhum decorator de autorização (são as
  próprias views de entrada/saída de sessão); as views operacionais de
  `apps/clientes` usam `@login_required` combinado com
  `tem_permissao_modulo()`/`tem_habilitacao()`; as demais views
  operacionais (`apps/processos`, `apps/tarefas`, `apps/agenda`,
  `apps/financeiro`, `apps/dashboard`, `apps/chat`, `apps/modelos` e
  `apps/laboratorio`) usam exclusivamente `@login_required`; em
  `apps/configuracoes/views.py`, `index` e `editar_perfil` usam
  `@login_required`, enquanto `novo_usuario`, `equipes`,
  `nova_equipe`, `editar_equipe`, `equipe_membros`,
  `remover_membro_equipe`, `alternar_gerente_equipe`, `permissoes` e
  `editar_escritorio` usam `@requer_admin_escritorio`, um controle
  binário administrador/não administrador, distinto do kernel
  dinâmico.
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
- Nenhum módulo operacional (`apps.clientes`, `apps.processos`,
  `apps.tarefas`, `apps.agenda`, `apps.financeiro`, `apps.dashboard`,
  `apps.modelos`) filtra listagens por `responsavel`, `equipe`,
  `participantes` ou `criado_por`.
- Objetos de detalhe/edição/exclusão são carregados por
  `get_object_or_404(Model, pk=pk, ...)`, no máximo com uma condição
  de estado (`ativo=True`, `status=...`), nunca uma condição de posse.
- O campo `nivel` (nível de acesso técnico atual) é resolvido pelo
  kernel, mas não é lido por nenhuma view operacional para filtrar um
  `QuerySet`.
- Principal risco intra-tenant já documentado: um usuário autenticado
  do tenant pode, nas rotas inspecionadas, carregar por identificador
  registros existentes no schema ativo sem filtro de responsabilidade,
  equipe ou escopo — ver
  [../security/overview.md](../security/overview.md#principais-lacunas-constatadas).

## Estado por módulo

### Dashboard

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

`apps/dashboard/views.py::painel` agrega dados reais de
`apps.clientes.Cliente`, `apps.processos.Processo`,
`apps.tarefas.Tarefa`, `apps.agenda.Compromisso` e
`apps.financeiro.LancamentoFinanceiro`, sem mocks. Lê
`request.tenant.assinatura.plano.nome` para exibição, sem escrita. Não
possui `models.py` próprio.

#### Diferenças para o alvo canônico

[dashboard.md](../product/modules/dashboard.md) exige que cada
indicador respeite autorização e escopo do usuário que consulta;
`painel` calcula todos os contadores e totais (incluindo financeiros)
sobre o tenant inteiro, sem filtro por usuário.

#### Dependências ou bloqueios

Depende de escopo aplicado primeiro em Clientes, Processos, Tarefas,
Agenda e Financeiro, conforme a ordem de dependência de
[PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md).

### Clientes

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

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
operações no kernel atual. `Cliente.responsavel` é preenchido com
`request.user` na criação. `templates/clientes/lista.html` e
`templates/processos/lista.html` incluem o mesmo componente de busca
(`components/search_bar.html`), marcado no próprio template como
"Barra de busca visual — sem lógica real nesta fase"; nem
`clientes/views.py::lista` nem `processos/views.py::lista` leem um
parâmetro de busca da URL, confirmando que a busca é apenas visual.
Cobertura de teste: `apps/clientes/tests/test_autorizacao.py` (26
testes) — ver "Testes".

#### Diferenças para o alvo canônico

[clientes.md](../product/modules/clientes.md) exige que um usuário com
atuação restrita não alcance clientes fora de seu escopo — isso
permanece uma lacuna após o WI-0001: o `nivel`
(`somente_seus`/`todos`) não é lido nem aplicado a nenhum `QuerySet`;
`Cliente.responsavel` não limita listagem, detalhe ou carregamento por
`pk`; `lista` continua filtrando apenas por `ativo=True`, e
`detalhe`/`editar`/`desativar`/`reativar` continuam carregando o
objeto por `get_object_or_404` sem condição de posse — autorização
sobre objeto/IDOR intra-tenant não está resolvida.
`desativar`/`reativar`/`inativos` não possuem habilitação específica
no kernel atual (candidatas a habilitação futura, ver
[../security/authorization-matrix.md](../security/authorization-matrix.md#clientes)).
`templates/clientes/detalhe.html` exibe uma aba "Documentos" com um
contador fixo `(2)` no rótulo da aba, sem relação com nenhum
`QuerySet` ou model — ao abrir a aba, o conteúdo é sempre um estado
vazio ("Nenhum documento anexado."), consistente com a ausência de
`FileField` em `Cliente` já registrada em "Escopo de dados".

#### Dependências ou bloqueios

Fase A (autorização de módulo/habilitação) aplicada em Clientes via
WI-0001; os demais módulos da Fase A permanecem pendentes. Fase B
(escopo de dados) do roadmap permanece pendente para Clientes; nenhum
PDR específico de Clientes está em aberto.

### Processos

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

`apps/processos/views.py` implementa `lista`, `detalhe`, `novo`,
`editar`, `arquivados`, `arquivar`, `reabrir`,
`adicionar_movimentacao`, `adicionar_parte`. `MovimentacaoProcessual`
registra andamentos com autor. `ParteProcesso` existe com um único
campo `tipo` (`autor`, `reu`, `terceiro`, `advogado_contrario`).
`Processo.equipe` é pré-preenchido via `equipe_padrao_para_usuario()`
quando o usuário pertence a exatamente uma equipe ativa.

#### Diferenças para o alvo canônico

[PDR-0001](../product/decisions/PDR-0001-participantes-processuais.md)
exige três dimensões separadas (vínculo com o escritório, posição
estrutural, qualificação processual) e suporte a múltiplos clientes
representados, múltiplas pessoas por polo, Ministério Público e
autoridades registradas separadamente; `ParteProcesso.tipo` não
sustenta essas dimensões. Escopo por responsável/equipe não é
aplicado em nenhuma rota.

#### Dependências ou bloqueios

[PDR-0001](../product/decisions/PDR-0001-participantes-processuais.md)
(modelagem de participantes, Fase C do roadmap); Fase A e B para
autorização e escopo.

### Tarefas

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

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

#### Diferenças para o alvo canônico

[PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md)
exige campos separados de criador, atribuidor, destinatário da
atribuição e data da atribuição, além de delegação direta a outro
usuário — nenhum desses campos existe em `Tarefa`, que possui apenas
`responsavel`. A habilitação `tarefas_atribuir_outros` existe no
kernel, mas não há rota ou campo que a consuma. O status `cancelada`
previsto em PDR-0002 não existe (`Tarefa.STATUS_CHOICES` é `a_fazer`,
`em_andamento`, `concluida`); em seu lugar existe `excluir` (exclusão
física).

#### Dependências ou bloqueios

[PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md)
(Fase C do roadmap, modelagem de dados); Fase A e B para autorização e
escopo.

### Agenda

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

`apps/agenda/views.py` implementa `index`, `form_compromisso`,
`editar`, `concluir`, `cancelar`, `reabrir`, `excluir`, com filtros de
listagem por data/status (`hoje`, `proximos_7`, `vencidos`, `todos`).
`Compromisso` possui `responsavel`, `participantes` (M2M),
vínculo opcional com `processo` e `cliente`.

#### Diferenças para o alvo canônico

[agenda.md](../product/modules/agenda.md) exige escopo por
responsável ou participante — não aplicado. `cliente` e `processo` são
campos independentes em `CompromissoForm`; uma combinação inconsistente
enviada por `POST` não é rejeitada pelo servidor, apenas preenchida
automaticamente quando um dos dois está vazio.

#### Dependências ou bloqueios

Fase A e B do roadmap; integridade cliente-processo tratada na Fase C.

### Financeiro

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

`apps/financeiro/views.py` implementa listagem, criação, edição,
marcação de pago, cancelamento, reabertura e exclusão de
`LancamentoFinanceiro`, além de listagem e criação de `CustaJudicial`.
O saldo de custas por cliente é calculado no backend
(`créditos depositados − custas pagas pelo escritório`), conforme
exigido por
[PDR-0005](../product/decisions/PDR-0005-custas-por-cliente.md).

#### Diferenças para o alvo canônico

Ver a tabela "Financeiro — estado interno" abaixo para o detalhamento
por área funcional.

#### Dependências ou bloqueios

[OPEN-001](../product/open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão),
[OPEN-002](../product/open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras),
Fase A e B para autorização/escopo, Fase D para consolidação.

### Chat

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

`apps/chat/views.py` implementa `lista`, `detalhe`, `global_sala`. A
única sala existente é `Conversa.TIPO_GLOBAL`, obtida por
`get_or_create`, compartilhada por todo o tenant. `lista`/`detalhe`
sempre redirecionam para ela — o `pk` recebido por `detalhe` não é
usado para carregar uma conversa específica. Envio de mensagem
funcional, com validação de conteúdo não vazio.

#### Diferenças para o alvo canônico

[chat.md](../product/modules/chat.md) prevê conversas individuais e em
grupo — nenhuma das duas existe no código; não há view de criação de
conversa além da sala global.

#### Dependências ou bloqueios

Fase E do roadmap (funcionalidades colaborativas e de apoio).

### Modelos

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

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

#### Diferenças para o alvo canônico

[modelos.md](../product/modules/modelos.md) prevê integração futura
com IA (condicionada ao PDR-0008), categorização e versionamento —
nenhum desses pontos está implementado. A habilitação
`modelos_editar_estilo` existe no kernel sem rota correspondente para
`EstiloEscritorio`. Não há filtro de escopo por `criado_por`.

#### Dependências ou bloqueios

[PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
para a integração futura com IA; Fase A e B para autorização/escopo.

### Inteligência Artificial / Laboratório

#### Estado

Não identificado.

#### Implementado no HEAD

`apps/laboratorio/views.py::index` apenas renderiza
`templates/laboratorio/index.html`, protegido por `@login_required`,
sem passar nenhum form ou dado de `CasoLaboratorio` ao contexto. O
template exibe um formulário HTML estático (campos sem submissão
real ao model) cujo botão de envio é `<button type="button" ...
disabled>Gerar peça com IA</button>`, explicitamente desabilitado, e
não existe nenhuma view de criação para `CasoLaboratorio` em
`apps/laboratorio/urls.py` (única rota: `laboratorio/` → `index`).
`CasoLaboratorio` é um model de placeholder, com um valor de
`STATUS_CHOICES` (`"processando"`) comentado no código como
"reservado para IA futura". Nenhuma integração com provedor de IA foi
identificada.

#### Diferenças para o alvo canônico

[inteligencia-artificial.md](../product/modules/inteligencia-artificial.md)
e
[PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
descrevem IA jurídica (contexto de processo, busca em documentos,
resumo, geração e edição de peças) e Assistente/Laboratório como
interface planejada — nenhum desses comportamentos existe além do
shell visual. As habilitações `processos_usar_ia` e
`processos_usar_laboratorio` existem no kernel sob o módulo
`processos`, sem nenhuma view que as consulte.

#### Dependências ou bloqueios

[PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
— pré-requisitos (autorização aplicada, escopo aplicado, acesso seguro
a documentos, dados processuais estruturados, histórico e
rastreabilidade, módulos centrais estáveis) ainda não consolidados.

### Configurações

#### Estado

Parcialmente implementado.

#### Implementado no HEAD

`apps/configuracoes/views.py` implementa `index`, `editar_perfil`
(`@login_required`, opera sobre `request.user`) e as rotas
administrativas `novo_usuario`, `equipes`, `nova_equipe`,
`editar_equipe`, `equipe_membros`, `remover_membro_equipe`,
`alternar_gerente_equipe`, `permissoes`, `editar_escritorio`, todas
protegidas por `@requer_admin_escritorio`. A tela `permissoes`
configura `PermissaoPapel` apenas pelo caminho legado de `tipo_conta`
(`limitado`/`financeiro`), não por `PapelAcesso`/`UsuarioPapel`.

#### Diferenças para o alvo canônico

[configuracoes.md](../product/modules/configuracoes.md) lista
"papéis de acesso" e "habilitações" no escopo funcional — nenhuma
rota foi identificada para administrar `PapelAcesso` ou
`HabilitacaoPapel`/`HabilitacaoUsuario` diretamente. Edição de
identidade visual (`ConfiguracaoVisual`) não possui rota tenant
identificada; permanece administrável apenas via Django Admin no
schema público.

#### Dependências ou bloqueios

Fase A do roadmap (a tela que configura autorização deveria, ela
mesma, refletir o kernel dinâmico que administra).

## Financeiro — estado interno

| Área funcional | Estado | Implementação identificada | Diferença principal |
| --- | --- | --- | --- |
| Financeiro geral | Parcialmente implementado | `LancamentoFinanceiro` com `CATEGORIA_CHOICES`, `status`, `data_pagamento`; indicadores de previsto/realizado calculados na view | Sem campo de modalidade (único/parcelado/recorrente); `CATEGORIA_CHOICES` inclui `"custa_judicial"` como categoria comum, apesar de PDR-0003 exigir área própria |
| Custas judiciais | Parcialmente implementado | `CustaJudicial` existe; saldo por cliente calculado corretamente no backend, conforme PDR-0005 | Sem filtro de escopo na listagem; sem rota de edição/transição de estado identificada (sem exigência canônica correspondente) |
| Solicitações | Não identificado | Nenhum model, view ou rota para solicitação de pagamento/reembolso | Bloqueado por [OPEN-002](../product/open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras) quanto ao fluxo final; modelagem inteira pendente |
| Honorários | Não identificado | Nenhum model `Honorario`; `LancamentoFinanceiro.CATEGORIA_CHOICES` inclui `"honorario"`/`"exito"` como categorias, sem os campos de valor estimado/efetivo exigidos por PDR-0007 | Modelagem de Honorário como entidade própria pendente |
| Recorrência | Não identificado | Nenhum campo de quantidade de parcelas, periodicidade, data final ou vínculo de origem entre ocorrências | Bloqueado por [OPEN-001](../product/open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão) |
| Billing SaaS | Parcialmente implementado | `Plano`/`Assinatura` existem em `saas_billing`; leitura (sem escrita) do nome do plano em `apps.configuracoes` e `apps.dashboard` | Sem interface de gestão de plano além da leitura; nenhuma sincronização automática assinatura → lançamento, conforme PDR-0003 (preservado deliberadamente, não é lacuna) |

Pontos preservados sem resolução: OPEN-001, OPEN-002, billing mantido
separado do financeiro do tenant por decisão de
[PDR-0003](../product/decisions/PDR-0003-areas-funcionais-financeiro.md),
e nenhuma sincronização automática entre assinatura SaaS e lançamento
financeiro do tenant.

## IA

- **Laboratório (interface)** — existe como shell visual
  (`apps.laboratorio`), sem lógica de IA. Não deve ser tratado como IA
  implementada.
- **IA jurídica (funcionalidade)** — não identificada no código. Os
  pré-requisitos de
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
  não estão consolidados (autorização e escopo ainda não aplicados nas
  views operacionais).
- **Modelos** — cadastro e importação manuais funcionam sem depender
  de IA, conforme exigido por
  [modelos.md](../product/modules/modelos.md); a integração futura com
  IA não está implementada.
- **Sugestão de honorários por IA** — não implementada; depende do
  model `Honorario` (ainda não existente) e dos pré-requisitos de
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md),
  conforme [PDR-0007](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md).

## Testes

Os três arquivos de teste de `apps/accounts/tests/` foram lidos
integralmente na auditoria original (`a543c3f`); execução não
verificada naquele lote. A implementação do WI-0001 (commit `da19001`)
acrescentou `apps/clientes/tests/test_autorizacao.py` e executou
`python manage.py test apps.clientes` (26 testes) e `python manage.py
test apps.accounts` (86 testes), ambas com resultado `OK` — evidência
completa registrada em
`docs/delivery/work/WI-0001-autorizacao-backend-clientes.md`. As demais
afirmações desta seção sobre `apps/accounts/tests/` continuam
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
  `Cliente`). Não cobre escopo de dados (`responsavel`/equipe/`nivel`)
  nem autorização sobre objeto/IDOR intra-tenant — ver "Diferenças para
  o alvo canônico" na subseção Clientes.
- **Cobertura parcial identificada**: `apps/clientes` — autorização de
  módulo e das duas habilitações existentes (`clientes_criar`,
  `clientes_editar`) é testada diretamente sobre as views, mas escopo
  de dados, autorização sobre objeto e as demais views operacionais
  (Processos, Tarefas, Agenda, Financeiro, Dashboard, Chat, Modelos,
  Laboratório) permanecem sem teste de autorização.
- **Não foi identificado teste específico** para: escopo de dados nos
  módulos operacionais (Clientes, Processos, Tarefas, Agenda,
  Financeiro, Dashboard, Chat, Modelos); autorização sobre objeto
  específico (IDOR intra-tenant) fora de `apps/accounts`; isolamento
  cross-tenant explícito; integridade cliente-processo em
  Tarefas/Agenda; regras de negócio do Financeiro (modalidades,
  previsto/realizado) fora do cálculo de saldo de custas.
- Uma busca por `find apps -type f \( -name "test_*.py" -o -name
  "tests.py" \)` no HEAD auditado (`da19001`) retorna os três arquivos
  de `apps/accounts/tests/` e `apps/clientes/tests/test_autorizacao.py`
  — nenhum outro app do repositório possui arquivo de teste.

## Dívida e divergências conhecidas

| Área | Divergência constatada | Fonte canônica relacionada |
| --- | --- | --- |
| Autorização nas views | Kernel dinâmico implementado e testado (`apps/accounts/tests/`, 86 testes, `OK`); `apps/clientes/views.py` já o consulta (WI-0001, commit `da19001`), mas as demais views operacionais (Processos, Tarefas, Agenda, Financeiro, Dashboard, Chat, Modelos, Laboratório) continuam protegidas apenas por `@login_required` | [../security/authorization-model.md](../security/authorization-model.md), [PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md) |
| Alteração de senha ausente | `templates/configuracoes/index.html` exibe um botão "Alterar senha" sem `href`/ação de formulário; nenhuma rota, view ou form correspondente foi identificado em `apps/accounts` | [configuracoes.md](../product/modules/configuracoes.md) |
| Escopo de dados | Helpers de equipe existem, mas nenhum módulo operacional filtra `QuerySet` por responsável, equipe ou participação | [../security/data-scope.md](../security/data-scope.md) |
| Participantes processuais | `ParteProcesso.tipo` (campo único) não implementa as três dimensões exigidas | [PDR-0001](../product/decisions/PDR-0001-participantes-processuais.md), [../architecture/module-map.md](../architecture/module-map.md) |
| Delegação de tarefas | `Tarefa` não possui `criador`/`atribuidor`/`destinatario_atribuicao`/`data_atribuicao`; sem rota de atribuição a outro usuário; sem status `cancelada` | [PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md), [../security/authorization-matrix.md](../security/authorization-matrix.md) |
| Categoria de custas no financeiro geral | `LancamentoFinanceiro.CATEGORIA_CHOICES` inclui `"custa_judicial"`, apesar de PDR-0003 exigir área própria (já existente como `CustaJudicial`) | [PDR-0003](../product/decisions/PDR-0003-areas-funcionais-financeiro.md), [../architecture/module-map.md](../architecture/module-map.md) |
| Integridade cliente-processo | `cliente`/`processo` são campos independentes em `TarefaForm`/`CompromissoForm`; combinação inconsistente por `POST` não é rejeitada | [clientes.md](../product/modules/clientes.md), [../security/data-scope.md](../security/data-scope.md) |
| Financeiro futuro | Solicitações e Honorários não modelados como entidades próprias; recorrência não implementada | [PDR-0006](../product/decisions/PDR-0006-solicitacoes-financeiras.md), [PDR-0007](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md), OPEN-001, OPEN-002 |
| Hierarquia de equipes | `Equipe.equipe_pai` e `equipes_descendentes()` já existem no código, mas nenhuma view os consome; decisão de produto sobre hierarquia continua em aberto | [equipes.md](../product/modules/equipes.md), [../security/data-scope.md](../security/data-scope.md) |
| Identidade visual | `ConfiguracaoVisual` administrável apenas via Django Admin no schema público, sem rota tenant identificada | [configuracoes.md](../product/modules/configuracoes.md), [../security/authorization-matrix.md](../security/authorization-matrix.md) |
| Documentação de teste desatualizada | Docstrings de `test_admin_tenant.py`/`test_permissoes_kernel.py` descrevem um kernel anterior ("não consulta UsuarioPapel", `is_superuser` concede admin) que não corresponde ao código atual de `apps/accounts/permissoes.py`/`decorators.py` | [../security/authorization-model.md](../security/authorization-model.md) |

## Decisões em aberto que afetam o estado

- **OPEN-001** — periodicidades financeiras da primeira versão. Afeta a
  modelagem de recorrência e parcelamento no Financeiro, hoje não
  implementada.
- **OPEN-002** — etapas de aprovação das solicitações financeiras.
  Afeta a modelagem de Solicitações, hoje inexistente no código.

Nenhum outro ponto em aberto explícito foi identificado nos documentos
canônicos além destes dois.

## Referências

- [../product/](../product/)
- [../architecture/](../architecture/)
- [../security/](../security/)
- [roadmap.md](roadmap.md)
