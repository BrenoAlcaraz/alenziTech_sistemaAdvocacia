# Estado Atual do Projeto

Última atualização: 2026-07-10 (Fase 2.8 — Permissões iniciais concluída em nível básico)

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
| `accounts` | PerfilUsuario, signal de criação automática, helpers de permissão, grupos padrão | ✅ **Permissões básicas** |
| `dashboard` | Painel principal | ✅ **Básico operacional (dados reais)** |
| `clientes` | Cadastro de clientes | ✅ **CRUD real completo** |
| `processos` | Processos jurídicos | ✅ **Pasta jurídica básica funcional** |
| `tarefas` | Gestão de tarefas — quadro kanban | ✅ **Básico operacional completo** |
| `financeiro` | Lançamentos e custas | ✅ **Básico operacional (lançamentos)** |
| `agenda` | Compromissos e calendário | ✅ **Básico operacional completo** |
| `chat` | Conversas internas | mock |
| `modelos` | Modelos de peças jurídicas | mock |
| `laboratorio` | Laboratório Jurídico — placeholder IA | mock |
| `configuracoes` | Usuários, perfil, dados do escritório, criação de usuários, papéis | ✅ **Permissões básicas** |

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

## Módulo Financeiro — funcional em nível básico (Fase 2.5 concluída)

Todas as funcionalidades do escopo básico de lançamentos foram implementadas, testadas no navegador e commitadas:

| Funcionalidade | Implementação |
|---|---|
| Model `LancamentoFinanceiro` estruturado | `tipo`, `status`, `categoria`, `forma_pagamento`, `data_vencimento`, `data_pagamento`, `observacoes`, `cliente`, `processo`, `responsavel` |
| Model `CustaJudicial` mantido | existe no banco, sem fluxo real completo ainda |
| Tipos | `receita` / `despesa` |
| Status | `pendente` / `pago` / `cancelado` |
| Property `atrasado` | calculada dinamicamente: `status="pendente"` + `data_vencimento < hoje` |
| 13 categorias | honorário, êxito, reembolso, custa judicial, diligência, perícia, taxa, salário, aluguel, software, imposto, despesa do escritório, outro |
| 6 formas de pagamento | Pix, boleto, transferência, dinheiro, cartão, outro |
| Listagem real | `LancamentoFinanceiro.objects.select_related("cliente", "processo", "responsavel")` |
| Filtros | todos, pendentes, pagos, atrasados, receitas, despesas, mês atual |
| Normalização de filtro | valor inválido normalizado para `todos` |
| Cards de resumo | A receber, A pagar, Recebido no mês, Pago no mês, Saldo previsto |
| Formatação de moeda | helper `_formatar_moeda` na view; `floatformat:2` na lista |
| Criação real | `LancamentoFinanceiroForm` + POST; validação de `data_pagamento` se `status="pago"` |
| Edição real | `LancamentoFinanceiroForm(instance=lancamento)` |
| Auto-fill de cliente | se processo escolhido e cliente vazio → `processo.cliente` |
| Responsável selecionável | select de usuários ativos; fallback para `request.user` |
| Clientes inativos excluídos do select | `Cliente.objects.filter(ativo=True)` |
| Processos arquivados excluídos do select | `Processo.objects.exclude(status="arquivado")` |
| Ação rápida: Marcar como pago | `pendente` → `pago`; `data_pagamento = timezone.localdate()` via POST |
| Ação rápida: Cancelar | `pendente` → `cancelado` via POST |
| Ação rápida: Reabrir | `pago`/`cancelado` → `pendente`; `data_pagamento = None` via POST |
| POST-only em ações rápidas | GET direto não altera dados |
| Exclusão real | `lancamento.delete()` via POST; GET não remove; confirm nativo do browser |
| Redirecionamento seguro | `next` validado com `url_has_allowed_host_and_scheme`; preserva `?filtro=` |
| Ícone de edição na lista | lápis por card, redireciona para formulário de edição |
| Ícone de exclusão na lista | lixeira por card, POST com confirm |

Não implementado nesta fase (não bloqueante):

- Fluxo real completo de Custas Judiciais (UI de custas ainda usa mocks)
- Emissão de boleto
- Integração bancária
- Nota fiscal
- Conciliação
- Recorrência de lançamentos
- Relatórios avançados (por cliente, por processo, mensais)
- DRE (Demonstrativo de Resultados)
- Permissões financeiras específicas por cargo/grupo
- Auditoria/logs financeiros
- Soft delete/arquivamento de lançamentos (exclusão permanente foi implementada)
- Exportação Excel/PDF
- Gráficos
- Anexos/comprovantes de pagamento
- Busca textual
- Filtros avançados por cliente, processo, período e categoria
- Tratamento de cliente inativo/processo arquivado já vinculado em edição
- Revisão de UX do formulário e listagem com o sócio

## Módulo Dashboard — funcional em nível básico (Fase 2.6 concluída)

Dashboard sem model próprio — consome dados reais dos módulos já funcionais:

| Funcionalidade | Implementação |
|---|---|
| Sem model próprio | Dashboard lê dados de outros apps; sem migrations |
| Card: Clientes ativos | `Cliente.objects.filter(ativo=True).count()` |
| Card: Processos ativos | `Processo.objects.filter(status="ativo").count()` |
| Card: Tarefas pendentes | `Tarefa.objects.exclude(status="concluida").count()` |
| Card: Compromissos próximos | `status="agendado"`, `data_hora_inicio__date` entre hoje e hoje+7 |
| Card: A receber | `Sum("valor")` onde `tipo="receita"` e `status="pendente"` |
| Card: A pagar | `Sum("valor")` onde `tipo="despesa"` e `status="pendente"` |
| Formatação de moeda | helper `_formatar_moeda` na view (R$ 1.234,56) |
| Cards clicáveis | cada card navega para o módulo correspondente |
| Card A receber → link | `financeiro/?filtro=receitas` |
| Card A pagar → link | `financeiro/?filtro=despesas` |
| Hover nos cards | `hover:shadow-md transition-shadow duration-150` |
| Lista: Tarefas pendentes | `exclude(status="concluida")`, ordenado por prazo, até 5 itens |
| Lista: Agenda próxima | `status="agendado"`, `data_hora_inicio__date` hoje a hoje+7, até 5 itens |
| Lista: Financeiro pendente | `status="pendente"`, ordenado por `data_vencimento`, até 5 itens |
| Agenda próxima — regra de data | usa `__date__gte=hoje` (não `__gte=agora`) — consistente com card e com Agenda |
| Links inferiores | "Ver todas" → tarefas, "Ver agenda" → agenda, "Ver financeiro" → financeiro pendente |
| Mocks removidos | `RESUMO_MOCK` e `CASOS_MOCK` completamente eliminados |
| `plano_nome` | hardcoded `"Mestre"` — billing/SaaS ainda não implementado |

Não implementado nesta fase (não bloqueante):

- Gráficos de receitas/despesas ou de carga de trabalho
- Filtros internos no Dashboard por período, responsável ou área
- Links individuais em cada item das listas (tarefa → detalhe, etc.)
- Processos com prazo próximo na lista do Dashboard
- Calendário embutido
- Relatórios avançados
- Indicadores por responsável, por área do direito ou por cliente
- Alertas inteligentes (tarefas vencidas, compromissos do dia, financeiro vencido)
- Widgets configuráveis por usuário
- Plano real vindo do billing/SaaS (exibe badge fixo "Mestre")
- Permissões específicas por perfil no Dashboard
- Auditoria/logs de acesso ao painel

---

## Módulo Configurações — funcional em nível básico (Fase 2.7 concluída)

| Funcionalidade | Implementação |
|---|---|
| Listagem real de usuários | `User.objects.filter(is_active=True).select_related("perfil")` |
| Contador real de usuários ativos | `usuarios.count()` |
| Proteção contra perfil inexistente | `getattr(request.user, "perfil", None)` |
| Edição de perfil — nome completo | `PerfilUsuarioForm` + `PerfilUsuario.objects.get_or_create(user=request.user)` |
| Edição de perfil — cargo | campo descritivo, sem controle de permissão |
| Model `ConfiguracaoEscritorio` | tenant-specific, sem FK para `Escritorio` público |
| Migration `configuracoes.0001_initial` | aplicada em todos os schemas |
| Admin do escritório | `ConfiguracaoEscritorioAdmin` com `list_display`, `search_fields`, `readonly_fields` |
| Edição de dados do escritório | tela `/configuracoes/escritorio/` com `ConfiguracaoEscritorioForm` |
| Singleton por tenant | `ConfiguracaoEscritorio.objects.get_or_create(pk=1)` |
| Card "Dados do escritório" | exibe nome, email, telefone, site; empty state quando vazio |
| Campo `site` com UX melhorada | `forms.CharField` + `clean_site()` normaliza `google.com` → `https://google.com` |
| `plano_nome` | hardcoded `"Mestre"` — billing/SaaS ainda não implementado |
| `limite_usuarios` | hardcoded `10` — billing/SaaS ainda não implementado |

Não implementado nesta fase (não bloqueante):

- Permissões reais com `auth.Group` / `Permission`
- Criação/convite de usuários
- Alteração de senha
- Edição de e-mail
- Avatar do usuário (`ImageField` — aguarda definição de media em produção)
- Logo do escritório (mesma razão do avatar)
- Validação/máscara de CNPJ e telefone
- Limite real de usuários via billing
- Auditoria/logs de ações em Configurações
- Controle de acesso por cargo/perfil nos demais módulos
- Dados fiscais mais completos (IE, regime tributário, etc.)

---

## Permissões iniciais e controle de acesso — Fase 2.8 concluída

| Funcionalidade | Implementação |
|---|---|
| Grupos padrão via migration | `accounts.0002_criar_grupos_padroes` com `get_or_create` idempotente |
| Grupos criados | `administrador_escritorio`, `gerente`, `advogado`, `financeiro` via `auth.Group` |
| Helpers de permissão | `apps/accounts/decorators.py` |
| `usuario_admin_escritorio(user)` | is_superuser / is_admin_escritorio / grupo — três caminhos independentes |
| `requer_admin_escritorio` | decorator para proteger views administrativas |
| `obter_papel_principal_usuario(user)` | retorna primeiro grupo padrão do usuário |
| `nome_legivel_grupo(nome)` | slug → nome humanizado |
| Criação de usuários pelo admin | `/configuracoes/usuarios/novo/` protegida por `@requer_admin_escritorio` |
| Papéis disponíveis na criação | apenas `gerente`, `advogado`, `financeiro` — não cria outro admin |
| Usuário criado com segurança | `is_staff=False`, `is_superuser=False`, `PerfilUsuario` criado automaticamente |
| Validação de email único | `User.objects.filter(email__iexact=email).exists()` |
| Papel real exibido na lista | nome humanizado baseado em `auth.Group` via `usuarios_contexto` |
| Botão "Novo usuário" condicional | visível apenas para admins (`usuario_e_admin_escritorio`) |
| Botão "Editar dados do escritório" condicional | visível apenas para admins |
| Proteção backend de `/configuracoes/escritorio/` | `@requer_admin_escritorio` |
| `/configuracoes/` mantido para todos | `@login_required` — não bloqueado inteiro |
| Edição de perfil mantida para todos | `@login_required` |

Não implementado nesta fase (não bloqueante):

- Bloqueio por papel nos módulos operacionais (Clientes, Processos, Tarefas, Agenda, Financeiro, Dashboard)
- `auth.Permission` granular por model/ação
- Edição do papel de usuário existente
- Exclusão/desativação de usuários pela interface
- Redefinição de senha pela interface
- Convite por e-mail / confirmação real de e-mail
- Departamentos e escopo de dados
- Auditoria de ações administrativas

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
- Migrations: ✅ OK (incluindo `configuracoes.0001_initial`, `accounts.0002_criar_grupos_padroes`)
- `migrate_schemas`: ✅ aplicado em todos os schemas de tenants
- Multi-tenancy: ✅ Schemas isolados confirmados
- Visual/UX: ✅ Navegação básica e layout validados
- Login: ✅ Funcionando em schema demo
- CRUD Clientes: ✅ Validado no navegador (criação, edição, detalhe, desativação, reativação)
- Configurações: ✅ Usuários reais, edição de perfil e dados do escritório validados no navegador
- Permissões: ✅ Grupos criados, admin inicial formalizado, criação de usuário pelo admin validada no navegador
