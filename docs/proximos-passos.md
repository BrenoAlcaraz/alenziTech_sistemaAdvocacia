# Próximos Passos

## Status da Fase 1 — Concluída

✅ Bloco 1 — Verificar PostgreSQL  
✅ Bloco 2 — Criar banco juridico_db  
✅ Bloco 3 — Criar .env  
✅ Bloco 4 — makemigrations  
✅ Bloco 5 — migrate_schemas --shared  
✅ Bloco 6 — Criar tenants public e demo  
✅ Bloco 7 — Criar superusuário no schema demo  
✅ Bloco 8 — Hosts Windows  
✅ Bloco 9 — Compilar Tailwind  
✅ Bloco 10 — Rodar servidor  
✅ Bloco 11 — Validar no navegador  

**Fase 1 — Estrutura Visual** finalizada com sucesso.

---

## Fase 2 — CRUD Real e Funcionalidades

### Checkpoint Git recomendado

Antes de começar a Fase 2, criar um checkpoint da Fase 1:

```bash
git add .
git commit -m "Fase 1: estrutura visual multi-tenant funcional

- PostgreSQL 16 e django-tenants configurados
- Schemas public e demo criados e funcionando
- Todos os 11 apps estruturados com models de negócio
- Templates responsivos com Tailwind validados
- Multi-tenancy isolada por schema
- Dados mockados em todas as views
- Ready para implementar CRUD real em Fase 2"
```

---

## Fase 2.1 — Começando por Clientes (CRUD Real)

### Objetivo

Implementar a primeira funcionalidade real: gestão de clientes com CRUD completo.
Manter layout e estrutura visual atual. Substituir mocks gradualmente.

### Escopo do módulo `clientes`

**Criar:**
1. Form de novo cliente (reutilizar template `clientes/form.html`)
2. View `criar` com POST
3. Migration para adicionar campos faltantes (se necessário)

**Listar:**
1. View `lista()` com query real de `Cliente.objects.all()`
2. Exibir na tabela de `templates/clientes/lista.html`
3. Manter mock apenas como fallback se não houver clientes

**Detalhar:**
1. View `detalhe()` com `get_object_or_404(Cliente, pk=pk)`
2. Exibir dados reais em `templates/clientes/detalhe.html`
3. Abas de processos relacionados (mock ou real)

**Editar:**
1. View `editar()` com `POST` para atualizar cliente
2. Form pré-preenchido com dados do cliente
3. Reutilizar `templates/clientes/form.html`

**Excluir/Inativar:**
1. Adicionar campo `ativo` (BooleanField) ao model `Cliente` se não existir
2. View `deletar()` que marca como inativo (soft delete) ou remove fisicamente
3. Button na tela de detalhe

### Sequência de implementação recomendada

1. **Revisar o model `Cliente`** — campos já definidos, identificar se faltam campos
2. **Adicionar campos faltantes se necessário** — criar migration
3. **Implementar a view `lista()`** — query real + fallback mock
4. **Implementar a view `detalhe()`** — get_object_or_404 + contexto
5. **Implementar a view `criar()`** — POST handler + redirect
6. **Implementar a view `editar()`** — GET para form, POST para update
7. **Implementar a view `deletar()`** — soft delete ou remove
8. **Atualizar `apps/clientes/urls.py`** — incluir novas rotas se necessário
9. **Testar via navegador** — CRUD completo no browser
10. **Refatorar os templates** — remover mocks, usar dados reais

### Não fazer nesta etapa

- Permissões granulares (apenas @login_required)
- Busca/filtros complexos
- Paginação (se houver muitos clientes, adicionar depois)
- Testes automatizados (podem vir em fase posterior)
- Validação complexa de CPF/CNPJ (formato básico OK)

---

## Após Clientes estar funcional

Replicar o padrão para os demais módulos:
- Processos
- Tarefas
- Financeiro
- Agenda
- Chat
- Modelos

Cada um seguirá o mesmo padrão: listar → detalhar → criar → editar → deletar/inativar.
