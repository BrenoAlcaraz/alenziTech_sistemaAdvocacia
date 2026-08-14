---
title: Arquitetura multi-tenant
status: canonical
owner: architecture
last_reviewed: 2026-08-13
---

# Arquitetura multi-tenant

## Objetivo

Descrever como os escritórios (tenants) do Breno - LawSystem são
isolados, como o contexto do tenant é selecionado durante uma
requisição, e quais limites arquiteturais precisam ser preservados para
manter esse isolamento. Este documento distingue isolamento entre
schemas (tratado aqui como princípio arquitetural) de autorização entre
usuários do mesmo schema (mencionada onde relevante, mas aprofundada em
documentação de segurança futura, em `docs/security/`, ainda não
criada).

## Modelo de tenancy

Confirmado em `config/settings/base.py` e em `apps/saas_tenants/models.py`:

- A biblioteca `django-tenants` está instalada
  (`requirements/base.txt`: `django-tenants==3.10.1`) e `django_tenants`
  é o primeiro item de `SHARED_APPS`, em `config/settings/base.py`.
- O modelo de tenancy é schema por tenant: em `apps/saas_tenants/models.py`,
  `Escritorio(TenantMixin)` define `auto_create_schema = True`, o que
  instrui o django-tenants a criar um schema PostgreSQL novo
  automaticamente ao salvar um `Escritorio`.
- `TENANT_MODEL = "saas_tenants.Escritorio"` e
  `TENANT_DOMAIN_MODEL = "saas_tenants.Dominio"`, em
  `config/settings/base.py`.
- Em `apps/saas_tenants/models.py`, `Dominio(DomainMixin)` associa um
  domínio de acesso a um `Escritorio`.
- `SHARED_APPS`, em `config/settings/base.py`, reúne os apps
  compartilhados: `django_tenants`, apps padrão do Django,
  `apps.saas_tenants`, `apps.saas_billing`.
- `TENANT_APPS`, no mesmo arquivo, reúne os apps de negócio de cada
  escritório: `apps.accounts`, `apps.dashboard`, `apps.clientes`,
  `apps.processos`, `apps.tarefas`, `apps.financeiro`, `apps.agenda`,
  `apps.chat`, `apps.modelos`, `apps.laboratorio`, `apps.configuracoes`.
- `django_tenants.middleware.main.TenantMainMiddleware` é o primeiro
  item de `MIDDLEWARE`, em `config/settings/base.py`.
- `DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]`, em
  `config/settings/base.py`.
- `DATABASES["default"]["ENGINE"]` é configurado como
  `"django_tenants.postgresql_backend"` em `config/settings/base.py` —
  o backend específico do django-tenants, exigido para o roteamento de
  schema funcionar.
- A estratégia de resolução de tenant é por domínio: `Dominio` associa
  um valor de domínio (por exemplo, `demo.localhost`) a um `Escritorio`,
  conforme os exemplos de uso registrados em `README.md`
  (`localhost` → schema `public`; `demo.localhost` → schema `demo`).
  Este documento cita `README.md` apenas como ilustração operacional,
  não como fonte de comportamento de produção.

Nenhum nome de classe, model ou comportamento interno do django-tenants
além do exposto por `TenantMixin`, `DomainMixin` e pelas settings acima
foi inventado neste documento.

## Schema público

Confirmado como compartilhado, via `SHARED_APPS`:

- `apps.saas_tenants`: `Escritorio` (tenant), `Dominio` (domínio),
  `ConfiguracaoVisual` (personalização white label — `OneToOneField`
  para `Escritorio`, portanto residente no schema público junto com o
  tenant que ela personaliza).
- `apps.saas_billing`: `Plano`, `Assinatura` (`OneToOneField` para
  `Escritorio`).

Nenhum dado operacional do escritório (clientes, processos, tarefas,
financeiro, agenda, chat, modelos, configurações) está em
`SHARED_APPS`. Todos esses domínios estão em `TENANT_APPS`, no mesmo
arquivo.

## Schemas dos escritórios

Confirmado como pertencente a `TENANT_APPS`, em
`config/settings/base.py`, portanto replicado em cada schema de
tenant:

- `apps.accounts`: `PerfilUsuario` (`OneToOneField` para `auth.User`),
  `Equipe`, `MembroEquipe`, e o mecanismo de papéis e permissões
  (`PapelAcesso`, `UsuarioPapel`, `PermissaoPapel`, `PermissaoUsuario`,
  `HabilitacaoPapel`, `HabilitacaoUsuario`).
- `apps.clientes`: `Cliente`.
- `apps.processos`: `Processo`, `MovimentacaoProcessual`,
  `ParteProcesso`.
- `apps.tarefas`: `Tarefa`.
- `apps.agenda`: `Compromisso`.
- `apps.financeiro`: `LancamentoFinanceiro`, `CustaJudicial`.
- `apps.chat`: `Conversa`, `Mensagem`.
- `apps.modelos`: `ModeloPeca`, `EstiloEscritorio`.
- `apps.configuracoes`: `ConfiguracaoEscritorio`.
- `apps.dashboard`: sem model próprio — apresenta dados agregados dos
  módulos acima.
- `apps.laboratorio`: `CasoLaboratorio`, estrutura reservada para a
  futura IA jurídica.

Um ponto relevante confirmado no código: `django.contrib.auth` também
está listado em `TENANT_APPS`, em `config/settings/base.py`, além de já
estar em `SHARED_APPS`. Isso significa que as tabelas de `auth.User` e
`auth.Group` são sincronizadas também no schema de cada tenant pelo
mecanismo do django-tenants — não se deve presumir que todos os dados
de autenticação residem exclusivamente no schema público.
`AUTH_USER_MODEL` não é sobrescrito em nenhum arquivo de settings lido,
o que já é evidência suficiente para afirmar que o model de usuário
usado é o padrão do Django (`auth.User`).

## Seleção do tenant

Fluxo confirmado pela configuração lida:

1. A requisição chega com um domínio (por exemplo, o `Host` HTTP).
2. `TenantMainMiddleware`, primeiro middleware da lista em
   `config/settings/base.py`, resolve o tenant a partir desse domínio,
   usando o relacionamento definido por `TENANT_DOMAIN_MODEL`
   (`Dominio` → `Escritorio`).
3. O middleware ativa o schema PostgreSQL correspondente ao
   `Escritorio` resolvido — mecanismo padrão do django-tenants, baseado
   no `search_path` do PostgreSQL.
4. A requisição é processada normalmente pelo restante do pipeline
   (demais middlewares, roteamento por `config/urls.py`, view, models).
5. O contexto de schema é encerrado ou restaurado ao final da
   requisição pelo próprio middleware do django-tenants — este
   documento não descreve detalhes internos além do que a biblioteca e
   as settings lidas sustentam.

`config/urls.py` é um único `ROOT_URLCONF`, configurado em
`config/settings/base.py`, compartilhado entre schema público e
schemas de tenant. Não há `PUBLIC_SCHEMA_URLCONF` separado configurado.
Na prática, isso é atenuado pelo fato de os apps de negócio estarem em
`TENANT_APPS`, mas é uma configuração implícita, não uma separação
explícita de rotas por tipo de schema.

## Isolamento entre escritórios

Como princípio canônico, sustentado pela direção de
[docs/product/vision.md](../product/vision.md) ("preservar isolamento
entre escritórios") e pela arquitetura de schema constatada:

- Dados operacionais de um tenant não podem aparecer em outro — o
  isolamento físico por schema PostgreSQL é o mecanismo que sustenta
  essa garantia, já que cada schema contém seu próprio conjunto de
  tabelas para os apps de `TENANT_APPS`.
- Relações entre entidades de tenants diferentes são inválidas — não
  há, no código lido, nenhuma `ForeignKey` cruzando um model de
  `TENANT_APPS` com um registro de outro schema; isso é uma
  consequência estrutural do isolamento por schema, não uma validação
  aplicada explicitamente em código de negócio.
- Usuários de um escritório não administram outro — consistente com
  [docs/product/modules/configuracoes.md](../product/modules/configuracoes.md)
  ("um usuário de um tenant não pode ser administrado a partir de outro
  tenant").
- Identificadores previsíveis não concedem acesso — direção canônica
  registrada de forma consistente em várias especificações de módulo
  lidas (por exemplo,
  [docs/product/modules/chat.md](../product/modules/chat.md): "conhecer
  o identificador de uma conversa ou de um arquivo não concede acesso a
  ele"). O isolamento de schema, por si, impede que um ID de outro
  tenant aponte para um registro real dentro do schema ativo — mas essa
  garantia não substitui a necessidade de autorização entre usuários do
  mesmo schema, tratada na seção seguinte.
- Tarefas assíncronas futuras devem carregar contexto explícito do
  tenant — não há tarefas assíncronas confirmadas no código hoje (ver
  "Riscos arquiteturais"), mas este princípio é registrado como
  requisito para qualquer implementação futura desse tipo.
- Comandos e scripts devem selecionar conscientemente public ou tenant
  — nenhum comando de gestão customizado foi encontrado em
  `apps/*/management/commands/`; os comandos de migração usados são os
  do próprio django-tenants (`migrate_schemas`), que já operam sobre
  essa distinção.
- Arquivos devem preservar informação suficiente para verificar tenant
  e autorização — ver "Arquivos e anexos" abaixo, onde este ponto é
  registrado como não confirmado no código.

### Isolamento de schema versus autorização intra-tenant

O isolamento entre schemas, constatado no código, impede que um usuário
de um tenant alcance dados de outro tenant. Ele não resolve, por si só,
a autorização entre usuários do mesmo tenant — por exemplo, se um
usuário comum pode ou não acessar um cliente ou processo específico
dentro do próprio escritório. Essa segunda camada depende do mecanismo
de papéis, permissões e habilitações modelado em `apps/accounts`
(`PapelAcesso`, `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`,
`HabilitacaoUsuario`, e os helpers `tem_permissao_modulo()` e
`tem_habilitacao()` em `apps/accounts/permissoes.py`). A leitura de
`apps/clientes/views.py` e `apps/processos/views.py` mostra o uso do
decorator `@login_required`, sem chamada confirmada a esses helpers
nessas views. Este documento não afirma que a autorização intra-tenant
já está aplicada de forma sistemática; essa aplicação é registrada como
evolução planejada em
[PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md) (Rodada
2.1 — Permissões e integridade). A matriz técnica definitiva de papéis
e permissões está em
[docs/security/authorization-matrix.md](../security/authorization-matrix.md).

## Migrations

- O mecanismo confirmado é o padrão de migrations do Django, aplicado
  por schema através dos comandos do django-tenants
  (`migrate_schemas --shared` para `SHARED_APPS`, `migrate_schemas`
  para `TENANT_APPS`), conforme documentado operacionalmente em
  `README.md`.
- A separação entre migrations de `SHARED_APPS` e `TENANT_APPS` é
  automática, decorrente de cada app estar listado em uma das duas
  listas — não há mecanismo customizado adicional encontrado no código.
- Nenhum comando de gestão customizado relacionado a migrations foi
  encontrado em `apps/*/management/commands/`.
- [PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md) fixa,
  como direção canônica, que "migrations relevantes produzidas em
  qualquer rodada exigem auditoria e revisão antes de aplicação" — este
  documento não executa nem avalia migrations, apenas registra essa
  exigência.
- Risco: executar uma migration ou comando de gestão apontando para o
  schema incorreto (por exemplo, aplicar uma alteração de app de tenant
  apenas ao schema público, ou vice-versa) é um risco estrutural do
  modelo de schema por tenant, mitigado apenas pelo uso disciplinado dos
  comandos do django-tenants.
- Compatibilidade entre schemas: como cada schema de tenant compartilha
  a mesma definição de app (mesmos `TENANT_APPS`), uma migration de
  tenant é aplicada de forma idêntica a todos os schemas de tenant
  existentes: não há, no código lido, mecanismo de divergência de
  schema por tenant individual.

## Administração da plataforma

Distinção mantida, conforme
[docs/governance/terminology-policy.md](../governance/terminology-policy.md)
e confirmada estruturalmente pela separação de schema:

- **Platform Admin**: operador administrativo da plataforma SaaS, fora
  do escopo de um tenant específico. Atuaria sobre os dados do schema
  público (`apps.saas_tenants`, `apps.saas_billing`). Nenhum papel,
  view ou decorator específico de "Platform Admin" foi encontrado no
  código lido — a administração do schema público hoje é acessível via
  Django Admin padrão (`django.contrib.admin`, presente em
  `SHARED_APPS`), sem um mecanismo de autorização dedicado confirmado
  além do superusuário Django.
- **Administrador do escritório**: autoridade administrativa máxima
  dentro de um tenant, modelada pelo campo
  `PerfilUsuario.is_admin_escritorio`, em `apps/accounts/models.py`, e
  verificada pela função `usuario_admin_escritorio()`, em
  `apps/accounts/decorators.py`, usada pelo decorator
  `requer_admin_escritorio`, no mesmo arquivo.
- Estas duas autoridades são conceitos distintos e não devem ser
  confundidas, conforme
  [docs/governance/terminology-policy.md](../governance/terminology-policy.md).
  Este documento não atribui ao Platform Admin acesso irrestrito a
  dados jurídicos operacionais de um tenant: nenhuma decisão explícita
  desse tipo foi encontrada nas fontes canônicas lidas, e o isolamento
  de schema, por padrão, não concede esse acesso automaticamente — um
  acesso administrativo cross-tenant, se vier a existir, exigiria
  mecanismo próprio, hoje não confirmado no código.

## Arquivos e anexos

Não há, no código lido, uma estratégia consolidada de segregação de
arquivos por tenant. Ponto em aberto:

- **Organização de caminhos**: `MEDIA_ROOT`/`MEDIA_URL`, em
  `config/settings/base.py`, apontam para um único diretório local por
  instalação Django, sem particionamento visível por schema ou tenant
  no código lido. Os campos de upload encontrados usam caminhos fixos,
  não parametrizados por tenant — por exemplo,
  `ImageField(upload_to="avatares/")` em `PerfilUsuario`, em
  `apps/accounts/models.py`, e `upload_to="logos/"`,
  `upload_to="favicons/"`, `upload_to="backgrounds/"` em
  `ConfiguracaoVisual`, em `apps/saas_tenants/models.py`.
- **Separação física ou lógica por tenant**: não confirmada no código.
- **Validação de acesso a arquivo**: não confirmada como implementada
  para os campos de upload encontrados.
- **Prevenção contra IDOR** em arquivos: não confirmada.
- **Limpeza, retenção, storage de produção**: nenhuma dependência de
  armazenamento em nuvem foi encontrada em `requirements/`; nenhuma
  política de retenção ou limpeza de arquivos foi encontrada no código.

Este documento não inventa bucket, provedor ou estratégia de storage
para resolver esse ponto em aberto.

## Riscos arquiteturais

Riscos sustentados pelo código ou pelas fontes lidas:

- Consulta fora do contexto do tenant: mitigada estruturalmente pelo
  isolamento de schema, mas nenhuma consulta de negócio lida usa
  explicitamente `tenant_context()` ou equivalente do django-tenants
  para acessar múltiplos schemas deliberadamente — o que é esperado,
  dado que os apps de negócio operam sempre dentro do schema já
  ativado pelo middleware.
- Execução de comando no schema errado: risco estrutural do modelo de
  schema por tenant, discutido em "Migrations" acima.
- Vazamento de arquivo entre tenants: risco não descartado, dado que
  `MEDIA_ROOT` não está confirmado como particionado por tenant (ver
  "Arquivos e anexos").
- Cache sem chave de tenant: risco futuro. Nenhuma configuração de
  cache (`CACHES`) foi encontrada em
  `config/settings/base.py`, `development.py` ou `production.py`; o
  Django usa, portanto, o backend de cache local em memória por padrão
  quando não configurado. Nenhum uso de cache foi identificado no
  código de negócio lido.
- Tarefa assíncrona sem tenant explícito: risco futuro, não aplicável
  hoje. Nenhuma dependência de Celery, Redis, Channels, Kafka ou
  RabbitMQ foi encontrada em `requirements/base.txt`,
  `requirements/development.txt` ou `requirements/production.txt`. O
  único indício relacionado é um comentário em
  `apps/chat/models.py` sobre uma futura implementação de WebSocket via
  Django Channels — uma intenção registrada em comentário de código,
  não uma implementação existente.
- Integração externa sem segregação: não aplicável hoje — nenhuma
  integração com API externa foi encontrada no código lido.
- Confusão entre Platform Admin e Administrador do escritório: risco
  relevante, já que nenhum mecanismo de autorização dedicado ao
  Platform Admin foi confirmado no código além do superusuário padrão
  do Django Admin — ver "Administração da plataforma".

Não é afirmado neste documento que exista cache ou fila de
processamento assíncrono em uso; ambos são tratados apenas como riscos
a considerar caso venham a ser introduzidos.

## Critérios arquiteturais

- Toda requisição autenticada por domínio resolve o schema correspondente
  ao tenant correto, via `TenantMainMiddleware`.
- Uma operação tenant-scoped não deve consultar outro schema fora de um
  uso deliberado e explícito de troca de contexto do django-tenants.
- Vínculos que cruzariam tenants devem ser rejeitados — hoje isso é
  garantido estruturalmente pela ausência de `ForeignKey` entre schemas
  distintos, não por uma validação de aplicação explícita observada no
  código.
- O schema público não deve armazenar dados jurídicos operacionais do
  escritório sem uma decisão explícita — hoje isso é respeitado: nenhum
  model de `SHARED_APPS` contém dados de clientes, processos, tarefas,
  financeiro, agenda, chat ou modelos.
- Migrations devem ser executadas no contexto correto (schema público
  via `migrate_schemas --shared`, schemas de tenant via
  `migrate_schemas`), conforme documentado em `README.md`.
- Arquivos deveriam exigir validação de tenant e autorização antes de
  acesso — não confirmado como implementado hoje; registrado como
  ponto em aberto.
- Testes automatizados devem cobrir isolamento entre tenants. Testes
  automatizados já existem em `apps/accounts/tests/`
  (`test_admin_tenant.py`, `test_interacoes_kernel.py`,
  `test_permissoes_kernel.py`), construídos sobre `TenantTestCase` do
  django-tenants e cobrindo extensivamente a lógica de autorização e o
  kernel de permissões dentro de um schema de tenant. Nenhum teste
  afirmando explicitamente o isolamento de dados entre schemas de
  tenants diferentes foi identificado na inspeção realizada; a criação
  desse tipo de teste, se necessária, não faz parte deste lote.

## Pontos em aberto

- Estratégia de segregação de arquivos e anexos por tenant.
- Backups e restauração por tenant individual — não encontrados no
  código ou nas fontes lidas.
- Observabilidade (logs, métricas, tracing) com contexto de tenant —
  não encontrada no código lido.
- Domínio customizado por escritório além do mecanismo padrão de
  `Dominio` — não detalhado nas fontes lidas.
- Tarefas assíncronas com contexto de tenant, caso venham a ser
  introduzidas no futuro.
- Cache com chave de tenant, caso um backend de cache venha a ser
  configurado no futuro.
- Administração emergencial (acesso excepcional do Platform Admin a um
  tenant específico) — sem decisão encontrada nas fontes canônicas.
- Exportação ou exclusão completa de um tenant — não encontrada no
  código nem nas fontes lidas.
- Hardening de produção: `requirements/production.txt` acrescenta
  apenas `gunicorn` sobre `requirements/base.txt`; configurações como
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` ou
  `CSRF_COOKIE_SECURE` não foram encontradas em
  `config/settings/production.py` no momento desta leitura.

## Referências

- [overview.md](overview.md)
- [module-map.md](module-map.md)
- [docs/product/vision.md](../product/vision.md)
- [docs/product/scope.md](../product/scope.md)
- [docs/governance/terminology-policy.md](../governance/terminology-policy.md)
- [PDR-0008 — IA após o núcleo funcional](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
- [PDR-0009 — Sequência revisada da Fase 2](../product/decisions/PDR-0009-sequencia-fase-2.md)
