---
title: Visão geral da arquitetura
status: canonical
owner: architecture
last_reviewed: 2026-08-13
---

# Visão geral da arquitetura

## Objetivo

Este documento descreve o estilo arquitetural do Breno - LawSystem, seus
componentes principais, as fronteiras da plataforma e as dependências
estruturais entre elas. Ele distingue explicitamente três categorias de
afirmação, para que nenhuma leitura confunda o que já existe com o que
ainda está planejado:

- **arquitetura constatada no código** — sustentada pela leitura direta
  de `config/settings/base.py`, `config/urls.py`, `config/asgi.py`,
  `config/wsgi.py`, `requirements/`, `package.json` e dos apps em
  `apps/`;
- **direção arquitetural canônica** — sustentada por
  [docs/product/vision.md](../product/vision.md),
  [docs/product/scope.md](../product/scope.md) e pelo
  [índice de decisões](../governance/decision-index.md);
- **evolução planejada** — sustentada por PDRs aceitos e pelo escopo do
  produto, ainda sem implementação correspondente confirmada no código.

Onde código e documentação divergem, a divergência é registrada
explicitamente na seção "Estado, direção e evolução" ou nas seções
correspondentes, e não é resolvida silenciosamente por este documento,
conforme a [Regra de conflito](../README.md#regra-de-conflito).

## Estilo arquitetural

Constatado no código:

- Uma única aplicação Django (`manage.py`, `config/`), não um conjunto
  de serviços independentes.
- Linguagem Python; `requirements/base.txt` fixa `django>=5.2,<5.3` e
  `django-tenants==3.10.1`. O repositório não possui um arquivo de pin
  de versão de Python (como `.python-version` ou `pyproject.toml`) nem
  qualquer outra fonte atual que fixe uma versão mínima de Python.
- PostgreSQL como banco de dados, via `DATABASES["default"]["ENGINE"]`
  configurado como `"django_tenants.postgresql_backend"` em
  `config/settings/base.py`. O repositório não fixa atualmente uma
  versão específica de PostgreSQL em nenhum arquivo.
- Renderização por templates no servidor: em `config/settings/base.py`,
  `TEMPLATES` usa `django.template.backends.django.DjangoTemplates`,
  com `DIRS = [BASE_DIR / "templates"]` e `APP_DIRS = True`. Não há app
  de API REST instalado
  (nenhuma dependência de DRF ou equivalente em `requirements/`) nem
  framework de frontend SPA — `package.json` declara apenas
  `tailwindcss` como dependência de desenvolvimento, com scripts `build`
  e `watch` que compilam `static/css/input.css` em
  `static/css/output.css`.
- `django-tenants` está em `SHARED_APPS`, em `config/settings/base.py`,
  e `TENANT_MODEL` / `TENANT_DOMAIN_MODEL` apontam para
  `saas_tenants.Escritorio` e `saas_tenants.Dominio`, confirmando o uso
  de django-tenants como mecanismo de multi-tenancy.
- Isolamento por schema: `apps/saas_tenants/models.py` define
  `Escritorio(TenantMixin)` com `auto_create_schema = True`, o que é o
  mecanismo de criação de schema por tenant do django-tenants.

Direção arquitetural canônica, consistente com o constatado:

- [docs/README.md](../README.md#arquitetura-atual-resumida) e
  [docs/product/vision.md](../product/vision.md) descrevem o produto
  como "monólito modular Django" e afirmam explicitamente que não há
  microserviços independentes na arquitetura atual.
- [docs/governance/terminology-policy.md](../governance/terminology-policy.md)
  fixa "Monólito modular" como termo canônico do estilo arquitetural e
  determina que módulo/app Django não deve ser chamado de microserviço.

Este documento adota a mesma distinção: monólito modular não é
microserviços. Os apps Django (`apps/accounts`, `apps/clientes`,
`apps/processos`, entre outros) representam módulos internos de uma
única aplicação, não serviços independentes. `config/wsgi.py` e
`config/asgi.py` expõem, cada um, uma única aplicação Django
(`get_wsgi_application()` / `get_asgi_application()`), sem roteamento
para processos ou serviços separados. O sistema constitui uma única
aplicação e unidade de implantação Django. A implantação pode utilizar
um ou vários workers ou processos, sem transformar os apps internos em
serviços independentes. Fronteiras modulares (separação em apps) têm o
objetivo de reduzir acoplamento entre domínios funcionais, mas não
implicam isolamento de processo, de deploy ou de runtime.

## Camadas conceituais

### Plataforma SaaS compartilhada

Confirmado em `SHARED_APPS`, em `config/settings/base.py`:
`apps.saas_tenants` e `apps.saas_billing`, executados no schema público.

- `apps/saas_tenants/models.py`: `Escritorio` (tenant), `Dominio`
  (domínio de acesso), `ConfiguracaoVisual` (personalização white
  label, com `OneToOneField` para `Escritorio`).
- `apps/saas_billing/models.py`: `Plano` e `Assinatura` (`OneToOneField`
  para `Escritorio`).

Esta camada corresponde à "plataforma SaaS compartilhada" descrita em
[docs/product/vision.md](../product/vision.md), que fixa tenants,
planos e assinaturas no schema público.

### Operação do escritório

Confirmado em `TENANT_APPS`, em `config/settings/base.py`:
`apps.accounts`, `apps.dashboard`, `apps.clientes`, `apps.processos`,
`apps.tarefas`, `apps.financeiro`, `apps.agenda`, `apps.chat`,
`apps.modelos`, `apps.laboratorio`, `apps.configuracoes`.

Estes apps correspondem aos domínios de "operação do escritório"
descritos em [docs/product/vision.md](../product/vision.md) — contas e
acesso, clientes, processos, tarefas, agenda, financeiro, painel, chat,
modelos, configurações, e um módulo estrutural (`laboratorio`) para a
futura interface de IA jurídica, conforme
[module-map.md](module-map.md) detalha módulo a módulo.

### Interface

- Templates em `templates/`, organizados por módulo (`templates/agenda`,
  `templates/auth`, `templates/base`, `templates/chat`,
  `templates/clientes`, `templates/components`,
  `templates/configuracoes`, `templates/dashboard`,
  `templates/financeiro`, `templates/laboratorio`, `templates/modelos`,
  `templates/processos`, `templates/tarefas`).
- Arquivos estáticos em `static/css`, `static/img`, `static/js`.
- Pipeline de CSS via Tailwind CSS 3, confirmado em `package.json`
  (`tailwindcss: ^3.4.19`) e `tailwind.config.js`, compilado por
  `npm run build` / `npm run watch`, sem `django-compressor` ou
  ferramenta de bundling de JavaScript adicional confirmada.
- Um `context_processor`
  (`apps.saas_tenants.context_processors.tenant_config`) injeta o
  tenant atual e sua configuração visual em todos os templates,
  registrado em `TEMPLATES` em `config/settings/base.py`.

### Persistência

- PostgreSQL, acessado via `django_tenants.postgresql_backend`.
- Schema público (dados de `SHARED_APPS`) e schemas de tenant (dados de
  `TENANT_APPS`), conforme detalhado em
  [multitenancy.md](multitenancy.md).
- Migrations Django padrão, aplicadas por schema via os comandos do
  django-tenants (`migrate_schemas`), sem comandos de gestão
  customizados encontrados em `apps/*/management/commands/`.
- Arquivos de mídia: `MEDIA_ROOT` e `MEDIA_URL`, em
  `config/settings/base.py`, apontam para um diretório local; nenhuma
  biblioteca de storage em nuvem foi encontrada em `requirements/`. A
  estratégia de segregação de arquivos por tenant não foi identificada
  na inspeção realizada — ver [multitenancy.md](multitenancy.md).

## Fluxo de uma requisição

1. A requisição chega ao Django através do servidor configurado em
   `config/wsgi.py` (ou `config/asgi.py`).
2. O domínio da requisição identifica o tenant. Isso é conceitualmente
   sustentado por `TENANT_DOMAIN_MODEL = "saas_tenants.Dominio"`, em
   `config/settings/base.py`, que associa domínios a um `Escritorio`.
3. `django_tenants.middleware.main.TenantMainMiddleware`, primeiro item
   de `MIDDLEWARE` em `config/settings/base.py`, resolve o tenant a
   partir do domínio e encaminha o contexto da requisição para o schema
   público ou para o schema do tenant correspondente.
4. `config/urls.py`, `ROOT_URLCONF` único, roteia a requisição para a
   view do app correspondente.
5. Autorização e escopo de dados deveriam ser aplicados no backend, na
   view ou em uma camada equivalente. Isso é a expectativa canônica
   registrada em todas as especificações funcionais de módulo (por
   exemplo, [docs/product/modules/clientes.md](../product/modules/clientes.md)
   e [docs/product/modules/processos.md](../product/modules/processos.md)).
   Não é uma afirmação de que toda view já aplica essa verificação: a
   leitura de `apps/clientes/views.py` e `apps/processos/views.py`
   mostra o uso do decorator `@login_required` do Django, sem chamadas
   confirmadas a `apps.accounts.permissoes.tem_permissao_modulo()` ou
   `tem_habilitacao()` nessas views. Esses helpers existem em
   `apps/accounts/permissoes.py`, mas sua aplicação sistemática às views
   dos módulos operacionais não está confirmada no código lido.
6. A regra de negócio acessa os models do schema já ativado pelo
   middleware — por exemplo, `apps.clientes.models.Cliente` ou
   `apps.processos.models.Processo`.
7. A resposta é renderizada por um template Django ou devolvida como
   redirecionamento (padrão Post/Redirect/Get, conforme
   [docs/history/phase-1/encerramento-fase-1.md](../history/phase-1/encerramento-fase-1.md),
   citado aqui apenas como contexto histórico, não como fonte canônica).

Este fluxo diferencia três coisas que não devem ser confundidas: o
isolamento de schema por tenant (constatado no código, via
`TenantMainMiddleware`), a autorização interna dentro do tenant (parte
dela modelada em `apps/accounts` — `PapelAcesso`, `PermissaoPapel`,
`HabilitacaoPapel`, entre outros —, mas não confirmada como aplicada em
todas as views), e a expectativa canônica de que o backend seja a
autoridade de segurança, registrada de forma consistente em
[docs/product/vision.md](../product/vision.md) e em todas as
especificações de módulo lidas para este lote.

## Princípios arquiteturais

- Monólito modular Django, não microserviços — direção canônica de
  [docs/README.md](../README.md) e da
  [política de terminologia](../governance/terminology-policy.md).
- Isolamento por tenant via schema PostgreSQL — constatado no código e
  detalhado em [multitenancy.md](multitenancy.md).
- Plataforma SaaS compartilhada (schema público) separada dos dados
  operacionais de cada escritório (schema de tenant) — constatado em
  `SHARED_APPS` / `TENANT_APPS`.
- Backend como autoridade de segurança — direção canônica, registrada em
  todas as especificações de módulo lidas
  (por exemplo, "autorização e escopo de dados devem ser aplicados no
  backend, não apenas ocultando elementos de interface"); ainda não
  confirmada como plenamente aplicada nas views constatadas.
- Integridade entre módulos — direção canônica de
  [docs/product/scope.md](../product/scope.md) ("garantir vínculos
  válidos entre cliente e processo").
- Migrations revisadas antes da aplicação — direção canônica de
  [PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md)
  ("migrations relevantes produzidas em qualquer rodada exigem
  auditoria e revisão antes de aplicação").
- Evolução incremental, sem reescrita total — direção canônica de
  [docs/product/vision.md](../product/vision.md) e
  [docs/product/scope.md](../product/scope.md).
- IA posterior ao núcleo funcional — direção canônica de
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md),
  consistente com o estado constatado no código: `apps/laboratorio`
  possui apenas um model de placeholder
  (`CasoLaboratorio`, com status `"processando"` explicitamente
  reservado para "IA futura" em comentário do código) e uma view que
  apenas renderiza um template, sem integração de IA.
- Decisões técnicas relevantes registradas por ADR futuro — direção
  canônica do [índice de decisões](../governance/decision-index.md),
  que lista ADR-0001 a ADR-0005 como pendentes de formalização.

## Estado, direção e evolução

| Categoria | Significado | Exemplos |
| --- | --- | --- |
| Constatado no código | Comportamento ou estrutura observável nos arquivos atuais do repositório | `SHARED_APPS`/`TENANT_APPS` em `config/settings/base.py`; `TenantMainMiddleware` como primeiro middleware; ausência de Celery, Redis, Channels ou dependência de armazenamento em nuvem em `requirements/`; views de `clientes` e `processos` usando apenas `@login_required` |
| Direção canônica | Comportamento pretendido, registrado em documentação de produto ou governança aprovada | Monólito modular como estilo arquitetural; backend como autoridade de segurança; isolamento entre tenants como princípio; IA jurídica após consolidação do núcleo (PDR-0008); billing SaaS e Financeiro do tenant como domínios distintos, sem espelhamento automático entre eles (PDR-0003) |
| Evolução planejada | Registrado como objetivo futuro em escopo ou PDR, sem implementação confirmada | Aplicação sistemática de `tem_permissao_modulo()`/`tem_habilitacao()` às views (Rodada 2.1, [PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md)); Assistente/Laboratório com IA real ([PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)) |
| Não decidido | Sem decisão aprovada nas fontes canônicas lidas | Estratégia de segregação de arquivos por tenant; existência futura de fila ou processamento assíncrono; formato de deployment de produção além do que `requirements/production.txt` (gunicorn) sustenta; forma de uma eventual integração futura entre `saas_billing` e o Financeiro do tenant, caso venha a ser decidida por novo PDR |

## Restrições e não objetivos

- Não é arquitetura de microserviços — o sistema constitui uma única
  aplicação e unidade de implantação Django, conforme
  `config/wsgi.py`/`config/asgi.py`. A implantação pode utilizar um ou
  vários workers ou processos, sem que isso transforme os apps internos
  em serviços independentes.
- Não pressupõe event sourcing.
- Não pressupõe CQRS.
- Não pressupõe filas ou processamento assíncrono: nenhuma dependência
  de Celery, Redis, RabbitMQ ou Kafka foi encontrada em
  `requirements/base.txt`, `requirements/development.txt` ou
  `requirements/production.txt`. O único indício relacionado é um
  comentário em `apps/chat/models.py` ("Futuramente: implementar
  WebSocket via Django Channels"), que descreve uma intenção futura, não
  uma implementação existente.
- Não pressupõe frontend SPA — `package.json` não declara React, Vue ou
  bundler de JavaScript além do CLI do Tailwind.
- Não pressupõe IA como camada obrigatória — nenhum módulo funcional do
  núcleo depende de `apps.laboratorio` para operar, conforme
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
  e [docs/product/modules/inteligencia-artificial.md](../product/modules/inteligencia-artificial.md).
- Este documento não descreve deployment de produção: `docs/delivery/`
  e documentação de infraestrutura de produção, quando existirem, são
  as fontes apropriadas para esse tema.

## Relação com outros documentos

- [module-map.md](module-map.md) — mapa detalhado de módulos, shared
  versus tenant, e dependências entre eles.
- [multitenancy.md](multitenancy.md) — especificação da arquitetura
  multi-tenant, seleção de tenant e isolamento entre escritórios.
- [docs/product/vision.md](../product/vision.md) — visão do produto.
- [docs/product/scope.md](../product/scope.md) — escopo funcional e
  fases.
- [docs/governance/documentation-policy.md](../governance/documentation-policy.md) —
  política de documentação.
- [docs/governance/terminology-policy.md](../governance/terminology-policy.md) —
  termos canônicos de arquitetura e produto.
