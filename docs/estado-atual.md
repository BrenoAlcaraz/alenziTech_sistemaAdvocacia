# Estado Atual do Projeto

Última atualização: 2026-07-02 (Fase 2.4 — Agenda/Prazos concluída em nível básico)

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
| `tarefas` | Gestão de tarefas — quadro kanban | ✅ **Básico operacional completo** |
| `financeiro` | Lançamentos e custas | mock |
| `agenda` | Compromissos e calendário | ✅ **Básico operacional completo** |
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

## Módulo Tarefas — funcional em nível básico (Fase 2.3 concluída)

Todas as funcionalidades do escopo básico foram implementadas, testadas no navegador e commitadas:

| Funcionalidade | Implementação |
|---|---|
| Listagem real | `Tarefa.objects.select_related(...)` com ordenação por query param |
| Quadro kanban real | tarefas agrupadas por status em colunas |
| Visualização em lista | `/tarefas/lista/` com metadados inline |
| Criação real | `TarefaForm` + POST; `responsavel=request.user`, `status="a_fazer"` |
| Edição real | `TarefaForm(instance=tarefa)`; `responsavel` e `status` preservados |
| Vínculo com cliente | opcional, `ForeignKey(Cliente)` |
| Vínculo com processo | opcional, `ForeignKey(Processo)` |
| Auto-fill de cliente | se processo escolhido e cliente vazio, preenche com `processo.cliente` |
| Prazo opcional | `DateField(null=True, blank=True)` com widget `type="date"` |
| Exibição de prazo | badge urgente / badge normal / "Prazo não informado" |
| Ordenação | 6 opções via `?ordem=`: prazo próximo/distante, prioridade alta/baixa, mais recentes/antigas |
| Normalização de ordem | query param inválido normalizado para `prazo_proximo` |
| Ação rápida: Iniciar | `a_fazer` → `em_andamento` via POST |
| Ação rápida: Concluir | qualquer status → `concluida` via POST |
| Ação rápida: Reabrir | `concluida` → `a_fazer` via POST |
| Redirecionamento seguro | `next` validado com `url_has_allowed_host_and_scheme`; preserva `?ordem=` |
| Botão de edição | ícone de lápis no card do quadro e na lista |
| Exclusão real | `tarefa.delete()` via POST; GET não remove; lixeira no quadro e na lista |
| Remoção de mocks | todos os dados temporários removidos de `views.py` |

Não implementado nesta fase (não bloqueante):

- Soft delete/arquivamento de tarefa (exclusão permanente foi implementada)
- Detalhe de tarefa
- Responsável selecionável (definido automaticamente como usuário logado)
- Transição `em_andamento` → `a_fazer`
- Tratamento de tarefa com processo arquivado ou cliente inativo já vinculado
- Comentários e anexos
- Recorrência de tarefas
- Notificações de vencimento
- Integração com agenda/calendário
- Permissões por cargo/grupo
- Auditoria/logs
- Filtros avançados e busca
- Paginação

## Módulo Agenda/Prazos — funcional em nível básico (Fase 2.4 concluída)

Todas as funcionalidades do escopo básico foram implementadas, testadas no navegador e commitadas:

| Funcionalidade | Implementação |
|---|---|
| Model `Compromisso` estruturado | `tipo`, `status`, `dia_inteiro`, `responsavel`, `processo`, `cliente` |
| Vínculo opcional com processo | `ForeignKey(Processo, SET_NULL)` |
| Vínculo opcional com cliente | `ForeignKey(Cliente, SET_NULL)` |
| Status | `agendado` / `concluido` / `cancelado`; default `agendado` |
| Tipos | audiência, prazo, reunião, protocolo, perícia, julgamento, retorno, outro |
| Campo `dia_inteiro` | `BooleanField`; oculta horário na exibição |
| Listagem real | `Compromisso.objects.select_related("responsavel", "processo", "cliente")` |
| Filtro: Próximos 7 dias | `data_hora_inicio__date` entre hoje e hoje+7 (padrão) |
| Filtro: Hoje | `data_hora_inicio__date=hoje` |
| Filtro: Vencidos | `data_hora_inicio__lt=agora` + `status="agendado"` |
| Filtro: Todos | sem filtro de data ou status |
| Normalização de filtro | valor inválido normalizado para `proximos_7` |
| Criação real | `CompromissoForm` + POST; `status="agendado"` definido na view |
| Edição real | `CompromissoForm(instance=compromisso)`; `status` preservado |
| Auto-fill de cliente | se processo escolhido e cliente vazio → preenche com `processo.cliente` |
| Responsável selecionável | select de usuários ativos; fallback para `request.user` na criação |
| Ação rápida: Concluir | `agendado` → `concluido` via POST |
| Ação rápida: Cancelar | `agendado` → `cancelado` via POST |
| Ação rápida: Reabrir | `concluido`/`cancelado` → `agendado` via POST |
| Exclusão real | `compromisso.delete()` via POST; GET não remove; confirm nativo do browser |
| POST-only em ações e exclusão | GET direto nas rotas não altera dados |
| Redirecionamento seguro | `next` validado com `url_has_allowed_host_and_scheme`; preserva `?filtro=` |
| Ícone de edição na lista | lápis por card, redireciona para formulário de edição |
| Ícone de exclusão na lista | lixeira por card, POST com confirm |
| Remoção de mocks | dados temporários removidos; `/agenda/` renderiza lista real |

Não implementado nesta fase (não bloqueante):

- Calendário mensal dinâmico (template `index.html` mantido como referência visual)
- Cálculo automático de prazos processuais
- Notificações de vencimento
- Recorrência de compromissos
- Integração com Google Calendar
- Participantes no formulário
- Soft delete/arquivamento de compromisso (exclusão permanente foi implementada)
- Histórico/logs/auditoria
- Permissões específicas por cargo/grupo
- Tratamento de cliente inativo ou processo arquivado já vinculado em edição
- Visão de agenda por dia/semana/mês

---

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
