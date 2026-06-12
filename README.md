# Jurídico SaaS — Sistema Jurídico White Label

SaaS multi-tenant para escritórios de advocacia, construído com Django + PostgreSQL + django-tenants + Tailwind CSS.

## Pré-requisitos

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+

## Configuração inicial

### 1. Clonar e criar o ambiente virtual

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 2. Instalar dependências Python

```bash
pip install --upgrade pip
pip install -r requirements/development.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com suas credenciais do PostgreSQL
```

### 4. Criar o banco de dados PostgreSQL

```sql
CREATE DATABASE juridico_db;
```

> **Importante:** django-tenants requer PostgreSQL. Não funciona com SQLite.

### 5. Rodar as migrations

```bash
python manage.py migrate_schemas --shared   # cria tabelas públicas (tenants, planos)
python manage.py migrate_schemas            # cria tabelas de todos os tenants
```

### 6. Criar o tenant público inicial e um escritório de teste

```bash
python manage.py shell
```

```python
from apps.saas_tenants.models import Escritorio, Dominio

# Tenant público (obrigatório para django-tenants)
public = Escritorio(schema_name='public', slug='public', nome='Público')
public.save(verbosity=0)
Dominio(domain='localhost', tenant=public, is_primary=True).save()

# Escritório de teste
demo = Escritorio(schema_name='demo', slug='demo', nome='Escritório Demo')
demo.save(verbosity=0)
Dominio(domain='demo.localhost', tenant=demo, is_primary=True).save()
```

### 7. Criar superusuário no tenant demo

```bash
python manage.py tenant_command createsuperuser --schema=demo
```

### 8. Instalar e compilar Tailwind CSS

```bash
npm install
npm run build          # compila uma vez
npm run watch          # compila em modo watch (desenvolvimento)
```

### 9. Rodar o servidor

```bash
python manage.py runserver
```

Acesse: `http://demo.localhost:8000/login/`

> Para que subdomínios locais funcionem, adicione ao arquivo `hosts`:
> ```
> 127.0.0.1  demo.localhost
> ```

## Estrutura do projeto

```
config/         Configurações do Django (base, development, production)
apps/
  saas_tenants/ Tenants, domínios, configuração visual (schema público)
  saas_billing/ Planos e assinaturas (schema público)
  accounts/     Usuários e perfis (schema de cada tenant)
  dashboard/    Painel principal
  clientes/     Cadastro de clientes
  processos/    Processos jurídicos
  tarefas/      Gestão de tarefas
  financeiro/   Honorários, despesas e custas judiciais
  agenda/       Agenda de compromissos
  chat/         Conversas internas
  modelos/      Modelos de peças jurídicas
  laboratorio/  Laboratório Jurídico (IA futura)
  configuracoes/Configurações do escritório
templates/      Templates Django organizados por módulo
static/
  css/          input.css (Tailwind source) + output.css (compilado)
  js/           main.js (interações visuais)
```

## Fase atual

Esta é a **Fase 1 — Estrutura Visual**.

- Todas as páginas existem e são navegáveis
- Dados são mockados diretamente nas views
- Nenhuma funcionalidade real está implementada
- A próxima fase implementará CRUD real, busca, filtros e permissões

## Próximas fases planejadas

- Fase 2: CRUD real (clientes, processos, tarefas)
- Fase 3: Financeiro funcional
- Fase 4: Permissões granulares
- Fase 5: Chat em tempo real (Django Channels)
- Fase 6: IA no Laboratório Jurídico
- Fase 7: Integração de pagamentos
