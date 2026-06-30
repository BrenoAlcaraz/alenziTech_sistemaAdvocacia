# Estado Atual do Projeto

Última atualização: 2026-06-30

## Stack instalada e configurada

| Componente | Versão | Status |
|------------|--------|--------|
| Python | 3.12 | ✅ |
| Django | 5.2.x (LTS) | ✅ |
| django-tenants | 3.10.1 | ✅ |
| psycopg2-binary | — | ✅ |
| PostgreSQL | 16.14 | ✅ Rodando |
| Tailwind CSS | 3.x | ✅ Compilado e validado |
| python-dotenv | — | ✅ |
| Pillow | — | ✅ |

## Apps criados

### Schema público (SHARED_APPS)

| App | Descrição |
|-----|-----------|
| `saas_tenants` | Escritorio, Dominio, ConfiguracaoVisual |
| `saas_billing` | Plano, Assinatura |

### Schema de cada tenant (TENANT_APPS)

| App | Descrição | Status |
|-----|-----------|--------|
| `accounts` | PerfilUsuario, signal de criação automática | ✅ Estruturado |
| `dashboard` | Painel principal | mock |
| `clientes` | Cadastro de clientes | ✅ **CRUD real completo** |
| `processos` | Processos jurídicos | ✅ **Pasta jurídica básica funcional** |
| `tarefas` | Gestão de tarefas — quadro kanban | mock |
| `financeiro` | Lançamentos e custas | mock |
| `agenda` | Compromissos e calendário | mock |
| `chat` | Conversas internas | mock |
| `modelos` | Modelos de peças jurídicas | mock |
| `laboratorio` | Laboratório Jurídico — placeholder IA | mock |
| `configuracoes` | Usuários do escritório | mock |

## Status do banco de dados

| Etapa | Status |
|-------|--------|
| PostgreSQL instalado e rodando | ✅ |
| Banco `juridico_db` criado | ✅ |
| `.env` configurado com credenciais | ✅ |
| Conexão psycopg2 validada | ✅ |
| `makemigrations` executado | ✅ — migrations iniciais geradas |
| `migrate_schemas --shared` | ✅ Concluído com sucesso |
| Tenant `public` criado | ✅ schema public |
| Tenant `demo` criado | ✅ schema demo com migrations automáticas |
| Domínios criados | ✅ localhost → public, demo.localhost → demo |
| Superusuário criado | ✅ Acessível em schema demo |
| Hosts Windows configurado | ✅ 127.0.0.1 demo.localhost |
| Servidor Django rodou | ✅ Sucesso |
| Login funcionando | ✅ Validado com superusuário |

## Módulo Clientes — funcional (Fase 2.1 concluída)

Todas as funcionalidades implementadas, testadas no navegador e commitadas:

| Funcionalidade | Implementação |
|---|---|
| Listagem real | `Cliente.objects.filter(ativo=True)` |
| Criação real | `ClienteForm` + POST handler |
| Detalhe real | `get_object_or_404(Cliente, pk=pk, ativo=True)` |
| Edição real | `ClienteForm(instance=cliente)` |
| Soft delete / desativação | `ativo=False` via POST |
| Tela de inativos | `Cliente.objects.filter(ativo=False)` |
| Reativação | `ativo=True` via POST |

Dados mockados de Clientes foram completamente removidos de `views.py`.

Pendências futuras (não bloqueantes para Processos):
- Busca/filtros reais
- Paginação
- Validação avançada de CPF/CNPJ
- Permissões por grupo/cargo
- Hard delete restrito a gerente/dono
- Auditoria/logs de ações

## Módulo Processos — funcional em nível básico (Fase 2.2 concluída)

Todas as funcionalidades planejadas foram implementadas, testadas no navegador e commitadas:

| Funcionalidade | Implementação |
|---|---|
| Listagem real | `Processo.objects.exclude(status="arquivado")` |
| Criação real | `ProcessoForm` + POST handler; `responsavel=request.user`, `status="ativo"` |
| Detalhe real | `get_object_or_404` com `select_related` + `prefetch_related` |
| Edição real | `ProcessoForm(instance=processo)`, 11 campos editáveis |
| Partes reais | Formulário inline na aba Partes, rota POST-only |
| Movimentações reais | Formulário inline na aba Andamentos, `DateTimeField`, tipo exibido na timeline |
| Arquivamento | `status="arquivado"` via POST, banner visual no detalhe, sai da listagem |
| Reabertura | `status="ativo"` via POST, redireciona para detalhe |
| Lista de arquivados | `/processos/arquivados/` com reabrir inline e empty state |
| Remoção de mocks | Todos os dados temporários removidos de `views.py` |
| Saneamento visual | Contadores falsos `(1)` removidos das abas Prazos e Documentos |

Abas do detalhe com implementação futura (empty state por enquanto):
- **Prazos** — sem model real; exibe "Nenhum prazo cadastrado."
- **Documentos** — sem model real; exibe "Nenhum documento anexado."

Pendências futuras (não bloqueantes):
- Edição/exclusão de partes e movimentações
- Campos adicionais de partes (OAB, e-mail, telefone, endereço)
- Documentos processuais e upload real
- Prazos processuais estruturados com cálculo de prazos úteis
- Busca/filtros reais
- Paginação
- Permissões por grupo/cargo
- Auditoria/logs de ações
- Importação de movimentações de tribunais
- Integração com IA

## Templates

- ✅ Todas as páginas existem e são navegáveis
- ✅ Estrutura: `base.html` → `base_auth.html` / `base_public.html`
- ✅ Componentes: sidebar, header, badge, card_summary, empty_state, search_bar
- ✅ Visual validado: cores, tipografia, Tailwind aplicado corretamente
- ✅ `item_ativo` funcionando corretamente na sidebar
- ✅ Templates de Clientes usando dados reais (sem mocks)

## Validações realizadas

- `manage.py check`: ✅ 0 erros
- Conexão com PostgreSQL: ✅ OK
- Migrations: ✅ OK (incluindo `0002_cliente_ativo`)
- `migrate_schemas`: ✅ aplicado em todos os schemas de tenants
- Multi-tenancy: ✅ Schemas isolados confirmados
- Visual/UX: ✅ Navegação básica e layout validados
- Login: ✅ Funcionando em schema demo
- CRUD Clientes: ✅ Validado no navegador (criação, edição, detalhe, desativação, reativação)
