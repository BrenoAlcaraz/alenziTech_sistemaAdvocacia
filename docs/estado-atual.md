# Estado Atual do Projeto

Última atualização: 2026-06-08

## Stack instalada e configurada

| Componente | Versão | Status |
|------------|--------|--------|
| Python | 3.12 | ✅ |
| Django | 5.2.x (LTS) | ✅ |
| django-tenants | 3.10.1 | ✅ |
| psycopg2-binary | — | ✅ |
| PostgreSQL | 16.14 | ✅ Rodando |
| Tailwind CSS | 3.x | Instalado e configurado; output.css pendente de validação/compilação |
| python-dotenv | — | ✅ |
| Pillow | — | ✅ |

## Apps criados

### Schema público (SHARED_APPS)

| App | Descrição |
|-----|-----------|
| `saas_tenants` | Escritorio, Dominio, ConfiguracaoVisual |
| `saas_billing` | Plano, Assinatura |

### Schema de cada tenant (TENANT_APPS)

| App | Descrição |
|-----|-----------|
| `accounts` | PerfilUsuario, signal de criação automática |
| `dashboard` | Painel principal (mock) |
| `clientes` | Cadastro de clientes (mock) |
| `processos` | Processos jurídicos (mock) |
| `tarefas` | Gestão de tarefas — quadro kanban (mock) |
| `financeiro` | Lançamentos e custas (mock) |
| `agenda` | Compromissos e calendário (mock) |
| `chat` | Conversas internas (mock) |
| `modelos` | Modelos de peças jurídicas (mock) |
| `laboratorio` | Laboratório Jurídico — placeholder IA |
| `configuracoes` | Usuários do escritório (mock) |

## Status do banco de dados

| Etapa | Status |
|-------|--------|
| PostgreSQL instalado e rodando | ✅ |
| Banco `juridico_db` criado | ✅ |
| `.env` configurado com credenciais | ✅ |
| Conexão psycopg2 validada | ✅ |
| `makemigrations` executado | ✅ — 11 arquivos `0001_initial.py` gerados |
| `migrate_schemas --shared` | ❌ Ainda não executado |
| Tenants criados | ❌ Ainda não |
| Superusuário criado | ❌ Ainda não |

## Dados

- Todas as views usam dados mockados (listas e dicionários Python estáticos)
- Nenhuma query real ao banco está implementada
- Os mocks estão marcados com `# Dados temporários apenas para layout`

## Templates

- Todos os templates principais existem. A navegação real será validada após bootstrap do tenant demo e login.
- Estrutura: `base.html` → `base_auth.html` / `base_public.html`
- Componentes: sidebar, header, badge, card_summary, empty_state, search_bar

## Validações realizadas

- `manage.py check`: ✅ 0 erros
- Conexão com PostgreSQL: ✅ OK
- `makemigrations`: ✅ OK
