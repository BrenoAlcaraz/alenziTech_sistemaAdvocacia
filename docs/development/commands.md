---
title: Comandos de desenvolvimento
status: canonical
owner: development
last_reviewed: 2026-08-06
---

# Comandos de desenvolvimento

## Objetivo

Registrar, a partir da leitura direta do HEAD, os comandos de
desenvolvimento que o Breno - LawSystem sustenta hoje: preparação de
ambiente, dependências, variáveis de ambiente, banco de dados e
multitenancy, comandos Django, Tailwind, static/media e diagnóstico.
Nenhum comando abaixo foi inventado; cada um é sustentado por um arquivo
do repositório (`manage.py`, `requirements/*.txt`, `package.json`,
`config/settings/*.py`) ou por uma execução de leitura/diagnóstico
realizada nesta auditoria (`python manage.py check`, `python manage.py
help`), sem alteração de estado.

## Convenções

Cada comando listado neste documento é classificado como um dos
seguintes:

- **constatado** — confirmado por leitura direta de um arquivo do
  repositório (por exemplo, um script em `package.json`).
- **leitura/diagnóstico** — executado nesta auditoria sem alterar
  estado (banco, arquivos versionados ou schema).
- **mutante** — altera estado (banco de dados, schema, arquivos) se
  executado; não foi executado neste lote.
- **dependente de ambiente** — só funciona com dependências externas
  disponíveis (PostgreSQL acessível, variáveis de ambiente configuradas,
  `node_modules` instalado).

## Pré-requisitos

- **Python** — `requirements/base.txt` fixa `django>=5.2,<5.3` e
  `django-tenants==3.10.1`, mas nenhum arquivo do repositório
  (`.python-version`, `pyproject.toml`, ou equivalente) fixa uma versão
  de Python. `README.md` (raiz do repositório) indica "Python 3.12+"
  como pré-requisito de desenvolvimento — registrado aqui apenas como
  pré-requisito documentado, não como versão tecnicamente pinada.
- **PostgreSQL** — obrigatório. `DATABASES["default"]["ENGINE"]`, em
  `config/settings/base.py`, é `"django_tenants.postgresql_backend"`,
  que não funciona com SQLite. `README.md` (raiz) indica "PostgreSQL
  15+" como pré-requisito; nenhum arquivo do repositório fixa
  tecnicamente essa versão.
- **Node.js / npm** — necessário apenas para compilar o CSS via
  Tailwind (`package.json`). `README.md` (raiz) indica "Node.js 18+";
  essa versão é apenas documentada ali, sem pin técnico correspondente:
  `package.json` não declara campo `engines`, e não foi encontrado
  `.nvmrc` nem `.node-version` na raiz do repositório.

## Ambiente Python

Criação e ativação de virtualenv (procedimento padrão multiplataforma;
o repositório não cria o virtualenv automaticamente):

Windows PowerShell:

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Unix-like:

```text
python -m venv .venv
source .venv/bin/activate
```

Classificação: leitura/diagnóstico (não altera o repositório; cria
apenas o diretório local do virtualenv, já coberto por `.gitignore`).

## Dependências

Confirmadas pela leitura direta de `requirements/base.txt`,
`requirements/development.txt` e `requirements/production.txt`:

- `requirements/base.txt`: `django>=5.2,<5.3`, `django-tenants==3.10.1`,
  `psycopg2-binary==2.9.12`, `pillow==12.2.0`, `python-dotenv==1.2.2`,
  `pypdf==6.14.2`, `python-docx==1.2.0`.
- `requirements/development.txt`: inclui `-r base.txt` e adiciona
  `django-debug-toolbar>=4.4,<6.0`.
- `requirements/production.txt`: inclui `-r base.txt` e adiciona
  `gunicorn>=21.0,<24.0`.

Instalação (dependente de ambiente — requer virtualenv ativo):

```text
pip install --upgrade pip
pip install -r requirements/development.txt
```

Para produção:

```text
pip install -r requirements/production.txt
```

**Observação constatada**: `django-debug-toolbar` está declarado em
`requirements/development.txt`, mas não foi encontrada nenhuma
referência a `debug_toolbar` em `config/settings/development.py`,
`config/settings/base.py` ou em qualquer app de `apps/` (busca por
`debug_toolbar` sem resultado). A dependência está instalada quando
`requirements/development.txt` é usado, mas não está ativada em
`INSTALLED_APPS` nem em `MIDDLEWARE`.

## Variáveis de ambiente

Confirmadas pela leitura direta de `config/settings/base.py`,
`config/settings/production.py` e `.env.example`. `.env` existe no
repositório (não versionado, conforme `.gitignore`); apenas sua
existência é registrada aqui — seu conteúdo não foi lido para este
documento.

| Variável | Uso | Default | Observação |
| --- | --- | --- | --- |
| `SECRET_KEY` | Chave secreta do Django (`config/settings/base.py`) | `"chave-insegura-somente-dev"` | Default claramente marcado como inseguro; deve ser sobrescrito fora de desenvolvimento |
| `DEBUG` | Liga/desliga modo debug (`config/settings/base.py`) | `"True"` | `config/settings/development.py` força `DEBUG = True` independentemente da variável; `config/settings/production.py` força `DEBUG = False` |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula (`config/settings/base.py`) | `"localhost,127.0.0.1,.localhost"` em `base.py` | `config/settings/development.py` sobrescreve para `["*"]`; `config/settings/production.py` lê a variável com default `""`, o que a torna obrigatória em produção |
| `DB_NAME` | Nome do banco PostgreSQL | `"juridico_db"` | — |
| `DB_USER` | Usuário do PostgreSQL | `"postgres"` | — |
| `DB_PASSWORD` | Senha do PostgreSQL | `""` | Não possui valor seguro por default; deve ser definida |
| `DB_HOST` | Host do PostgreSQL | `"localhost"` | — |
| `DB_PORT` | Porta do PostgreSQL | `"5432"` | — |
| `STATIC_URL` | URL pública de arquivos estáticos | `"/static/"` | — |
| `MEDIA_URL` | URL pública de arquivos de mídia | `"/media/"` | — |

Nenhum valor real de segredo é reproduzido neste documento.

Configuração inicial (leitura/diagnóstico — apenas copia um arquivo
local, não versionado):

```text
cp .env.example .env
```

## Banco / multitenancy

Confirmado em `config/settings/base.py` e detalhado em
[docs/architecture/multitenancy.md](../architecture/multitenancy.md):

- `TENANT_MODEL = "saas_tenants.Escritorio"`,
  `TENANT_DOMAIN_MODEL = "saas_tenants.Dominio"`.
- `SHARED_APPS` (schema público) e `TENANT_APPS` (schema de cada
  escritório) são listas separadas em `config/settings/base.py`.
- `DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]`.

`python manage.py help` (executado nesta auditoria, sem alteração de
estado) confirma o grupo de comandos `[django_tenants]` disponível no
ambiente instalado: `all_tenants_command`, `clone_tenant`,
`collectstatic_schemas`, `create_domain`, `create_missing_schemas`,
`create_tenant`, `create_tenant_superuser`, `delete_domain`,
`delete_tenant`, `migrate`, `migrate_schemas`, `rename_schema`,
`tenant_command`.

Nenhum comando de gestão customizado foi encontrado em
`apps/*/management/commands/` (busca sem resultado).

| Objetivo | Comando | Mutante? | Observação |
| --- | --- | --- | --- |
| Migrar schema público | `python manage.py migrate_schemas --shared` | Sim | Aplica migrations dos apps de `SHARED_APPS`; não executado neste lote |
| Migrar schemas de tenant | `python manage.py migrate_schemas` | Sim | Aplica migrations dos apps de `TENANT_APPS` a todos os schemas de tenant existentes; não executado neste lote |
| Criar um tenant | `python manage.py create_tenant [--schema_name ...] [--nome ...] [--slug ...] [--ativo ...] [--domain-domain ...] [--domain-is_primary ...]` | Sim | Comando genérico de django-tenants, confirmado por `python manage.py help create_tenant` nesta auditoria. Seus argumentos (`--nome`, `--slug`, `--ativo`, `--domain-domain`, `--domain-is_primary`) correspondem diretamente aos campos de `Escritorio`/`Dominio` em `apps/saas_tenants/models.py` (`nome`, `slug`, `ativo`; `domain`, `is_primary`). Não executado neste lote; nenhum procedimento do repositório documenta seu uso — ver "Provisioning de tenant" abaixo |
| Criar um domínio para um tenant existente | `python manage.py create_domain -s <schema> [--domain-domain ...] [--domain-is_primary ...]` | Sim | Confirmado por `python manage.py help create_domain` nesta auditoria. Não executado neste lote; nenhum procedimento do repositório documenta seu uso |
| Criar superusuário em um schema de tenant | `python manage.py tenant_command createsuperuser --schema=<schema>` ou `python manage.py create_tenant_superuser -s <schema> --username ...` | Sim | O primeiro é usado por `README.md` (raiz) como procedimento operacional; o segundo é um comando dedicado de django-tenants, confirmado por `python manage.py help create_tenant_superuser` nesta auditoria, mas não referenciado em nenhum procedimento documentado do repositório. Nenhum dos dois foi executado neste lote |
| Console de shell do Django | `python manage.py shell` | Neutro por si; mutante conforme uso | `README.md` (raiz) demonstra seu uso para criar `Escritorio`/`Dominio` via ORM — nesse uso é mutante |
| Ajuda sobre comandos disponíveis | `python manage.py help` / `python manage.py help <comando>` | Não | Executado nesta auditoria |

### Provisioning de tenant

`apps/saas_tenants/models.py` confirma `Escritorio(TenantMixin)` com
`auto_create_schema = True` (o schema PostgreSQL é criado
automaticamente ao salvar um `Escritorio`) e `Dominio(DomainMixin)`
associando um domínio a um `Escritorio`.

`README.md` (raiz do repositório) descreve, como procedimento
atualmente documentado ali — não como fonte canônica de arquitetura —,
a criação manual de um tenant público e de um escritório de teste via
`python manage.py shell`, instanciando `Escritorio`/`Dominio`
diretamente pelo ORM. Este documento cita esse procedimento apenas como
o fluxo observável no `README.md` da raiz, não como um fluxo canônico
de `docs/development/`: o próprio `README.md` (raiz) contém, em outras
seções, informação desatualizada sobre a fase do produto (ver
[current-state.md](../delivery/current-state.md)), o que reduz sua
autoridade como fonte operacional isolada. Este documento não usa o
`README.md` da raiz, isoladamente, como prova de versão mínima técnica,
de ordem obrigatória de comandos, de comportamento de migrations, ou de
que a criação do tenant público/escritório demo descrita ali seja a
forma correta ou atual de provisionar um tenant.

Separadamente, django-tenants disponibiliza no ambiente instalado os
comandos genéricos `create_tenant`, `create_domain` e
`create_tenant_superuser` (confirmados por `python manage.py help
<comando>` nesta auditoria), cujos argumentos são compatíveis com os
campos de `Escritorio`/`Dominio`. Nenhum procedimento do repositório
(README da raiz ou qualquer documento canônico) documenta o uso desses
três comandos como alternativa ao fluxo manual via `shell`.

**Conclusão constatada**: o repositório não possui, hoje, um fluxo
canônico próprio de provisioning de tenant. Existem dois caminhos
tecnicamente possíveis e comprovados pelo ambiente instalado — o
procedimento manual via `shell` demonstrado no `README.md` da raiz, e
os comandos genéricos `create_tenant`/`create_domain`/
`create_tenant_superuser` de django-tenants — mas nenhum dos dois está
registrado como o procedimento oficial em uma fonte canônica de
`docs/`. Este documento não decide qual dos dois deve ser adotado; essa
decisão, se necessária, pertence a um Work Item ou documento canônico
futuro, não a este lote de auditoria.

## Django

Comandos confirmados por `python manage.py help` (executado nesta
auditoria) e pela leitura de `manage.py`, que define
`DJANGO_SETTINGS_MODULE=config.settings.development` como padrão:

| Objetivo | Comando | Mutante? | Observação |
| --- | --- | --- | --- |
| Rodar o servidor de desenvolvimento | `python manage.py runserver` | Não altera dados, mas inicia processo | Usa `config.settings.development` por padrão |
| Validação estrutural | `python manage.py check` | Não | Executado nesta auditoria: retornou "System check identified no issues (0 silenced)." Não aplica migrations. Nenhum efeito mutante foi observado nesta execução; esta auditoria não instrumentou a chamada para confirmar categoricamente a ausência de qualquer acesso ao banco de dados |
| Executar testes | `python manage.py test [rótulo]` | Cria/derruba banco de teste temporário | Ver [testing.md](testing.md) para detalhes e rótulos válidos |
| Gerar migrations | `python manage.py makemigrations` | Gera arquivo (não altera banco) | Não executado neste lote |
| Migrar | `python manage.py migrate` | Sim | Não é o comando genérico padrão do Django neste projeto: `python manage.py help` lista `migrate` dentro do grupo `[django_tenants]`, não `[django]`, e a leitura direta de `.venv/Lib/site-packages/django_tenants/management/commands/migrate.py` confirma `Command = MigrateSchemasCommand` — ou seja, django-tenants substitui o `migrate` padrão do Django pelo mesmo comando de `migrate_schemas`. `python manage.py migrate` e `python manage.py migrate_schemas` são, portanto, o mesmo comando sob dois nomes neste projeto, incluindo as mesmas flags `--tenant`/`--shared`/`-s SCHEMA_NAME` |
| Criar superusuário no schema ativo | `python manage.py createsuperuser` | Sim | Para um tenant específico, ver `tenant_command createsuperuser --schema=<schema>` acima |
| Console de shell | `python manage.py shell` | Neutro por si | Ver "Banco / multitenancy" |
| Ajuda | `python manage.py help [comando]` | Não | — |

## Tailwind

Confirmado em `package.json`, `tailwind.config.js` e pela leitura
integral de `static/css/input.css`:

- `tailwindcss: ^3.4.19` é a única dependência declarada
  (`devDependencies`).
- Entrada real: `static/css/input.css` — confirmado tanto pelos scripts
  de `package.json` quanto pelo conteúdo do próprio arquivo, que usa as
  diretivas `@tailwind base;`, `@tailwind components;`, `@tailwind
  utilities;` (sintaxe do Tailwind 3.x, consistente com a versão fixada
  em `package.json`; não usa `@import "tailwindcss";`, sintaxe do
  Tailwind 4.x). O arquivo também define classes utilitárias de projeto
  via `@layer components`/`@apply` (por exemplo, `.btn-primary`,
  `.card`, `.sidebar-item`), sem outra diretiva de build além das três
  diretivas Tailwind padrão.
- Saída: `static/css/output.css`, conforme os scripts `-o` de
  `package.json` (não lido integralmente por ser arquivo gerado).
- `content` do Tailwind, em `tailwind.config.js`: `./templates/**/*.html`,
  `./apps/**/*.html`, `./static/js/**/*.js`.
- Nenhum framework JavaScript ou bundler adicional foi encontrado: não
  há `postcss.config.js`, `vite.config.js`/`.ts` nem
  `webpack.config.js` na raiz do repositório, e `package.json` não
  declara nenhuma dessas ferramentas.

Scripts reais, confirmados em `package.json`:

```text
npm install
npm run build          # compila uma vez
npm run watch           # compila em modo watch
```

Classificação: `npm install` é dependente de ambiente (rede/registro
npm); `npm run build`/`npm run watch` são mutantes apenas sobre
`static/css/output.css` (arquivo gerado), não sobre banco de dados ou
código-fonte versionado de outra forma.

## Static/media

Confirmado em `config/settings/base.py`:

- `STATIC_URL` (default `/static/`), `STATICFILES_DIRS = [BASE_DIR /
  "static"]`, `STATIC_ROOT = BASE_DIR / "staticfiles"`.
- `MEDIA_URL` (default `/media/`), `MEDIA_ROOT = BASE_DIR / "media"`.
- Em `config/urls.py`, quando `settings.DEBUG` é verdadeiro, as rotas de
  `MEDIA_URL` e `STATIC_URL` são servidas diretamente pelo Django via
  `django.conf.urls.static.static`.
- Nenhuma segregação de arquivos por tenant foi identificada — ver
  [docs/architecture/multitenancy.md](../architecture/multitenancy.md#arquivos-e-anexos).

Nenhum comando de gestão adicional (por exemplo, `collectstatic`) foi
executado neste lote; `python manage.py help` confirma sua existência
no grupo `[staticfiles]`.

## Diagnóstico

Comandos de leitura, seguros para uso a qualquer momento, sustentados
pela execução realizada nesta auditoria:

```text
python manage.py check
python manage.py help
python manage.py help <comando>
git status --short
```

## Comandos não estabelecidos

Não encontrados no HEAD auditado, portanto não documentados como
padrão atual do projeto: `pytest`, `pytest-django`, `Ruff`, `Black`,
`isort`, `mypy`, `pre-commit`, `tox`, `coverage.py`, `Docker`, `Docker
Compose`, `Celery`, `Redis`, `GitHub Actions`/CI. Nenhum `Makefile`,
`Dockerfile`, `docker-compose.yml`/`.yaml`, `pyproject.toml`,
`pytest.ini`, `tox.ini`, `setup.cfg` ou `Procfile` foi encontrado na
raiz do repositório. `django-debug-toolbar` é uma exceção parcial: está
declarado em `requirements/development.txt`, mas não está ativado em
nenhum arquivo de settings (ver "Dependências").

## Referências

- [README.md](README.md)
- [testing.md](testing.md)
- [docs/architecture/overview.md](../architecture/overview.md)
- [docs/architecture/multitenancy.md](../architecture/multitenancy.md)
- [docs/delivery/current-state.md](../delivery/current-state.md)
