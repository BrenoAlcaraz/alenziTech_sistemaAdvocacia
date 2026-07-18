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

## Fase 2.1 — Clientes (CRUD Real) — Concluída ✅

Todas as funcionalidades implementadas, testadas e commitadas:

✅ Listagem real (`Cliente.objects.filter(ativo=True)`)  
✅ Criação real (`ClienteForm` + POST)  
✅ Detalhe real (`get_object_or_404` com `ativo=True`)  
✅ Edição real (`ClienteForm(instance=cliente)`)  
✅ Soft delete / desativação (`ativo=False`)  
✅ Tela de clientes inativos  
✅ Reativação (`ativo=True`)  
✅ Mocks removidos de `views.py`  

### Pendências futuras de Clientes (não bloqueantes)

Estas funcionalidades serão implementadas em etapa posterior, após os demais módulos terem CRUD real:

- Busca/filtros reais (a barra de busca visual já existe no template)
- Paginação (quando o volume de clientes justificar)
- Validação avançada de CPF/CNPJ (formato e dígito verificador)
- Permissões por grupo/cargo (usuários comuns vs. gerente/dono)
- Hard delete restrito a gerente/dono (com aviso de perda de histórico)
- Auditoria/logs de ações sobre clientes
- Contagem real de processos por cliente no card da lista

---

## Fase 2.2 — Processos (Pasta Jurídica Básica) — Concluída ✅

Todas as funcionalidades do escopo básico foram implementadas, testadas e commitadas:

✅ Listagem real (`exclude(status="arquivado")`)
✅ Criação real (`ProcessoForm` + POST; `responsavel` e `status` definidos na view)
✅ Detalhe real (dados, partes, movimentações, status visual)
✅ Edição real (`ProcessoForm(instance=processo)`)
✅ Partes reais (formulário inline, rota POST-only)
✅ Movimentações reais (formulário inline, `DateTimeField`, tipo na timeline)
✅ Arquivamento (soft state `status="arquivado"`, sai da listagem, banner no detalhe)
✅ Reabertura (`status="ativo"` via POST)
✅ Lista de arquivados (`/processos/arquivados/`)
✅ Mocks removidos de `views.py`
✅ Contadores falsos removidos das abas Prazos/Documentos

### Pendências futuras de Processos (não bloqueantes)

Estas funcionalidades foram intencionalmente deixadas para etapa posterior:

- **Edição/exclusão de partes** — atualmente só é possível adicionar
- **Campos adicionais de partes** — OAB, e-mail, telefone, qualificação completa, endereço
- **Edição/exclusão de movimentações** — atualmente só é possível adicionar
- **Documentos processuais** — upload real, categorização, versionamento, download
- **Prazos processuais estruturados** — model `PrazoProcessual`, `data_limite`, `cumprido`, alerta
- **Cálculo de prazos úteis** — excluindo feriados e fins de semana
- **Busca/filtros reais** — barra de busca visual já existe no template, sem lógica real
- **Paginação** — quando o volume de processos justificar
- **Permissões por grupo/cargo** — usuários comuns vs. gerente/dono do tenant
- **Auditoria/logs** — registro de quem arquivou, reabriu, editou e quando
- **Lista/filtros avançados por status/fase** — processos suspensos, encerrados, em recursal, etc.
- **Apensos** — processos relacionados/vinculados
- **Importação de movimentações de tribunais** — e-SAJ, PJe, TJSP
- **Integração com IA** — análise de petição inicial, contestação, sentença, recursos e execução

---

## Fase 2.3 — Tarefas — Concluída em nível básico ✅

Todas as funcionalidades do escopo básico foram implementadas, testadas e commitadas:

✅ Listagem real (quadro kanban e visualização em lista)
✅ Criação real (`TarefaForm`, `responsavel` e `status` definidos na view)
✅ Edição real (`TarefaForm(instance=tarefa)`, `responsavel` e `status` preservados)
✅ Auto-fill de cliente a partir do processo
✅ Prazo opcional com exibição visual (badge urgente / normal / "Prazo não informado")
✅ Ordenação por 6 critérios via query param `?ordem=`
✅ Normalização de ordem inválida
✅ Ações rápidas POST-only: Iniciar, Concluir, Reabrir
✅ Redirecionamento seguro com preservação de `next` e `?ordem=`
✅ Botão de edição (ícone de lápis) no quadro e na lista
✅ Exclusão real (`tarefa.delete()` via POST; lixeira funcional no quadro e na lista)
✅ Mocks removidos de `views.py`

### Pendências futuras de Tarefas (não bloqueantes)

- **Soft delete/arquivamento de tarefa** — exclusão permanente foi implementada; arquivamento reversível fica para etapa futura
- **Modal de confirmação de exclusão customizado** — atualmente usa `confirm()` nativo do browser
- **Permissões de exclusão** — qualquer usuário logado pode excluir; restringir por cargo/grupo futuramente
- **Auditoria de exclusão** — log de quem excluiu e quando
- **Detalhe de tarefa** — página dedicada com histórico e metadados completos
- **Responsável selecionável** — atualmente definido como o usuário logado
- **Transição `em_andamento` → `a_fazer`** — "desfazer início" não implementado
- **Tratamento de cliente inativo / processo arquivado já vinculado** — edição pode perder o vínculo silenciosamente
- **Busca por título/descrição**
- **Filtros** — por status, prioridade, responsável, cliente, processo e prazo
- **Paginação**
- **Calendário ou agenda de tarefas**
- **Notificações de vencimento** — e-mail ou push quando prazo se aproxima
- **Tarefas recorrentes**
- **Anexos**
- **Comentários internos**
- **Histórico de alterações / auditoria**
- **Permissões por grupo/cargo**
- **Logs de ações**

---

## Fase 2.4 — Agenda/Prazos — Concluída em nível básico ✅

Todas as funcionalidades do escopo básico foram implementadas, testadas e commitadas:

✅ Model `Compromisso` estruturado (tipo, status, dia_inteiro, responsavel, processo, cliente)  
✅ Listagem real com filtros por período (próximos 7 dias, hoje, vencidos, todos)  
✅ Normalização de filtro inválido para `proximos_7`  
✅ Vencidos: apenas compromissos com `status="agendado"` no passado  
✅ Criação real (`CompromissoForm`, `status="agendado"` definido na view)  
✅ Edição real (`CompromissoForm(instance=compromisso)`, `status` preservado)  
✅ Auto-fill de cliente a partir do processo  
✅ Responsável selecionável com fallback para usuário logado  
✅ Ação rápida: Concluir (`agendado` → `concluido` via POST)  
✅ Ação rápida: Cancelar (`agendado` → `cancelado` via POST)  
✅ Ação rápida: Reabrir (`concluido`/`cancelado` → `agendado` via POST)  
✅ Exclusão real (`compromisso.delete()` via POST; GET não remove)  
✅ Redirecionamento seguro com preservação de `next` e `?filtro=`  
✅ Ícone de edição (lápis) e exclusão (lixeira) por card na lista  
✅ Mocks removidos; `/agenda/` renderiza lista real  

### Pendências futuras de Agenda/Prazos (não bloqueantes)

- **Calendário mensal dinâmico** — template `index.html` mantido como referência visual para implementação futura
- **Navegação por mês** — anterior/próximo no calendário
- **Visão semanal e diária** — grid por hora
- **Cálculo de prazos úteis** — excluindo feriados e fins de semana
- **Integração de prazos com processos** — vincular prazo a movimentação processual
- **Criação automática de prazo a partir de movimentação processual**
- **Notificações de vencimento** — e-mail ou push quando prazo se aproxima
- **Compromissos recorrentes** — audiências semanais, reuniões mensais
- **Integração com Google Calendar**
- **Participantes no formulário** — campo `ManyToManyField` já existe no model
- **Permissões por grupo/cargo**
- **Auditoria/logs** — quem criou, editou, concluiu, cancelou e quando
- **Soft delete/arquivamento** — exclusão permanente foi implementada; arquivamento reversível fica para etapa futura
- **Busca e filtros avançados** — por tipo, responsável, processo, cliente
- **Vínculo futuro com tarefas** — se fizer sentido operacional
- **Tratamento de cliente inativo/processo arquivado em edição** — vínculo pode ser perdido silenciosamente ao salvar

---

## Fase 2.5 — Financeiro — Concluída em nível básico ✅

Todas as funcionalidades do escopo básico de lançamentos foram implementadas, testadas e commitadas:

✅ Model `LancamentoFinanceiro` estruturado (tipo, status, categoria, forma de pagamento, datas, vínculos)
✅ Listagem real com 7 filtros (todos, pendentes, pagos, atrasados, receitas, despesas, mês atual)
✅ Normalização de filtro inválido para `todos`
✅ 5 cards de resumo (A receber, A pagar, Recebido no mês, Pago no mês, Saldo previsto)
✅ Criação real (`LancamentoFinanceiroForm` + POST; validação de `data_pagamento` se `status="pago"`)
✅ Edição real (`LancamentoFinanceiroForm(instance=lancamento)`)
✅ Auto-fill de cliente a partir do processo
✅ Responsável selecionável com fallback para `request.user`
✅ Ação rápida: Marcar como pago (`pendente` → `pago`; `data_pagamento` preenchida automaticamente)
✅ Ação rápida: Cancelar (`pendente` → `cancelado`)
✅ Ação rápida: Reabrir (`pago`/`cancelado` → `pendente`; `data_pagamento` limpa)
✅ Ações rápidas POST-only; GET direto não altera dados
✅ Exclusão real (`lancamento.delete()` via POST; GET não remove; confirm nativo)
✅ Redirecionamento seguro com preservação de `next` e `?filtro=`
✅ Ícone de edição (lápis) e exclusão (lixeira) por card na lista

### Pendências futuras de Financeiro (não bloqueantes)

- **Custas Judiciais** — fluxo real completo; UI ainda usa mocks
- **Filtros avançados** — por cliente, processo, período, categoria
- **Busca textual** — por descrição
- **Relatórios por cliente** — extrato de honorários
- **Relatórios por processo** — custo total do processo
- **Relatórios mensais** — visão por competência
- **Gráficos** — receitas vs. despesas por período
- **DRE** — Demonstrativo de Resultados do Exercício
- **Recorrência** — lançamentos mensais automáticos
- **Anexos/comprovantes** — PDF de comprovante de pagamento
- **Exportação** — Excel/PDF de extratos
- **Integração bancária** — importação de extrato OFX
- **Boletos** — emissão via API bancária
- **Notas fiscais** — NFS-e, vinculada ao lançamento
- **Conciliação** — cruzar extrato bancário com lançamentos
- **Permissões financeiras** — restringir por cargo/grupo
- **Auditoria/logs** — quem lançou, editou, cancelou e quando
- **Soft delete/arquivamento** — exclusão permanente foi implementada; arquivamento fica para etapa futura
- **Revisão de UX** — formulário e listagem com o sócio

---

## Fase 2.6 — Dashboard real — Concluída em nível básico ✅

Todas as funcionalidades do escopo básico foram implementadas, testadas e commitadas:

✅ Cards reais: Clientes ativos, Processos ativos, Tarefas pendentes, Compromissos próximos, A receber, A pagar
✅ Formatação de moeda brasileira nos cards financeiros
✅ Cards superiores clicáveis como atalhos para os módulos correspondentes
✅ Hover visual discreto nos cards (`hover:shadow-md transition-shadow`)
✅ Lista real: Tarefas pendentes (até 5, ordenadas por prazo)
✅ Lista real: Agenda próxima (até 5, próximos 7 dias por data)
✅ Lista real: Financeiro pendente (até 5, ordenadas por data de vencimento)
✅ Agenda próxima usa regra por data (`__date__gte=hoje`), consistente com card e com Agenda
✅ Links inferiores: "Ver todas", "Ver agenda", "Ver financeiro"
✅ `RESUMO_MOCK` e `CASOS_MOCK` completamente removidos
✅ Diagnóstico e correção de inconsistência entre card e lista da Agenda

### Pendências futuras de Dashboard (não bloqueantes)

- **Processos com prazo próximo** — lista do Dashboard; field `prazo_proximo` existe no model
- **Links individuais nos itens das listas** — tarefa → detalhe, compromisso → edição, lançamento → edição
- **Gráficos simples** — receitas vs. despesas por período, carga de tarefas
- **Filtros por período** — dashboard customizável por semana/mês
- **Indicadores por responsável** — quantas tarefas/processos por usuário
- **Indicadores por cliente** — processos, lançamentos pendentes por cliente
- **Indicadores por área do direito** — distribuição de processos por área
- **Indicadores financeiros mais completos** — DRE, saldo previsto, mês a mês
- **Alertas de tarefas vencidas** — badge ou banner se há tarefas com prazo vencido
- **Alertas de compromissos do dia** — destaque para eventos de hoje
- **Alertas de financeiro vencido** — badge se há lançamentos atrasados
- **Widgets configuráveis** — cada usuário escolhe o que exibir
- **Plano real vindo do billing** — `plano_nome` hardcoded, substituir por `Assinatura` real
- **Revisão visual com o sócio**

---

## Fase 2.7 — Configurações/Perfil — Concluída em nível básico ✅

Todas as funcionalidades do escopo básico foram implementadas, testadas no navegador e commitadas:

✅ Listagem real de usuários do tenant (mocks removidos)  
✅ Contador real de usuários ativos  
✅ Proteção contra `PerfilUsuario` inexistente  
✅ Edição de perfil do usuário logado (`nome_completo`, `cargo`)  
✅ `PerfilUsuario.objects.get_or_create(user=request.user)` garante perfil sempre existente  
✅ Model `ConfiguracaoEscritorio` tenant-specific (sem FK para `Escritorio` público)  
✅ Migration `configuracoes.0001_initial` aplicada em todos os schemas  
✅ Admin de `ConfiguracaoEscritorio` registrado  
✅ Edição de dados do escritório (`nome_escritorio`, `nome_fantasia`, `cnpj`, `email`, `telefone`, `endereco`, `site`, `observacoes`)  
✅ Singleton por tenant via `get_or_create(pk=1)`  
✅ Card "Dados do escritório" em `/configuracoes/` com empty state  
✅ Campo `site` aceita `google.com` e normaliza para `https://google.com`  

### Pendências futuras de Configurações (não bloqueantes)

- Permissões reais com `auth.Group` e `Permission`
- Criação/convite de usuários
- Alteração de senha
- Edição de e-mail
- Avatar do usuário
- Logo do escritório
- Validação/máscara de CNPJ e telefone
- Limite real de usuários via billing
- Auditoria/logs de ações
- Controle de acesso por cargo nos módulos

---

## Fase 2.8 — Permissões iniciais e controle de acesso — Concluída ✅

Todas as funcionalidades do escopo básico foram implementadas, testadas no navegador e commitadas:

✅ Migration `accounts.0002_criar_grupos_padroes` — grupos criados de forma idempotente  
✅ `apps/accounts/decorators.py` — helpers e constantes de permissão  
✅ `usuario_admin_escritorio(user)` — três caminhos: is_superuser / is_admin_escritorio / grupo  
✅ `requer_admin_escritorio` — decorator aplicado em views administrativas  
✅ Administrador inicial do tenant `demo` formalizado (is_admin_escritorio + grupo)  
✅ `/configuracoes/usuarios/novo/` — criação de usuários pelo Administrador do Escritório  
✅ Papéis exibidos na lista de usuários com nome humanizado  
✅ Botões administrativos ocultos para não-admins  
✅ `/configuracoes/escritorio/` protegida no backend  
✅ `/configuracoes/` e edição de perfil mantidos acessíveis para todos os usuários logados  

### Pendências futuras de Permissões (não bloqueantes)

- Bloqueio por papel nos módulos operacionais (Clientes, Processos, Tarefas, Agenda, Financeiro, Dashboard)
- `auth.Permission` granular por model/ação
- Edição do papel de usuário existente
- Exclusão/desativação de usuários pela interface
- Redefinição de senha pela interface
- Convite por e-mail / confirmação real de e-mail
- Departamentos e escopo de dados por departamento
- Auditoria de ações administrativas

---

## Fase 2.9 — Departamentos e escopo de dados — Concluída ✅

Todas as funcionalidades do escopo básico foram implementadas, testadas e commitadas:

✅ Model `Departamento` (tenant-scoped) com hierarquia de departamento pai  
✅ Model `MembroDepartamento` com constraint de unicidade `usuario+departamento`  
✅ Migration `accounts.0003_departamento_membrodepartamento` aplicada em todos os schemas  
✅ Admin de `Departamento` e `MembroDepartamento` registrados  
✅ Listagem de departamentos em `/configuracoes/departamentos/` (admin only)  
✅ Criação de departamento com validação de ciclo hierárquico  
✅ Edição de departamento (nome, descrição, pai, status ativo)  
✅ Gestão de membros: vincular/desvincular, marcar/remover gerente  
✅ Exibição de departamentos na lista de usuários em `/configuracoes/`  
✅ Helpers de escopo em `apps/accounts/escopo.py` — 6 funções de consulta + constantes  
✅ Todos os acessos administrativos protegidos por `@requer_admin_escritorio`  
✅ Nenhum filtro de escopo aplicado nos módulos operacionais (deliberado)  

### Pendências futuras de Departamentos (não bloqueantes)

- Escopo real aplicado nas views (Clientes, Processos, Tarefas, Agenda, Financeiro, Dashboard)
- Campo `departamento` nos módulos operacionais
- Gerente vendo apenas dados do departamento
- Advogado vendo apenas próprios itens
- Financeiro com escopo específico
- Herança automática de departamento por cliente/processo
- Regra para dados sem departamento/responsável
- Edição do papel de usuário existente pela interface
- Desativação/reativação de usuários pela interface

---

## Fase 2.10 — Escopo de dados nos módulos operacionais

### Fase 2.10A — Diagnóstico de Escopo — Concluída e removida ✅

✅ Tela implementada, usada para mapear riscos de escopo, e removida após cumprir seu papel.  
✅ O que ela revelou foi endereçado nas Fases 2.10B1 e 2.10B3 (`Cliente.responsavel`, `Cliente.departamento`, `Processo.departamento`).  
✅ Nenhum dado foi alterado, nenhuma migration criada por ela.

---

### Fase 2.10B — Preparação dos models para escopo (próxima etapa recomendada)

Pré-requisito: corrigir registros sem `responsavel` manualmente no ambiente demo antes de prosseguir.

- Adicionar `responsavel = ForeignKey(User, null=True, blank=True, SET_NULL)` ao model `Cliente`
- Avaliar adição de `departamento = ForeignKey(Departamento, null=True, blank=True, SET_NULL)` em `Cliente` e `Processo`
- Usar `null=True` e `blank=True` em todos os novos campos — não quebra dados existentes
- Criar migrations com `null=True` (sem valor padrão obrigatório)
- Aplicar `migrate_schemas` após aprovação

**Cuidados:**
- Não aplicar filtros ainda nesta etapa — apenas preparar os models
- Não tornar os campos obrigatórios nos forms nesta etapa
- Confirmar que `python manage.py check` passa antes de aplicar

---

### Fase 2.10C — Backfill/correção de dados antigos

Antes de ativar filtros, atribuir responsáveis a registros sem `responsavel`:

- Identificar processos, tarefas, compromissos e lançamentos com `responsavel=null` via tela de diagnóstico
- Atribuir manualmente ao administrador ou ao responsável correto via shell ou tela administrativa
- Confirmar que contadores da tela de diagnóstico mostram zero para todos os módulos antes de avançar

---

### Fase 2.10D — Escopo piloto em Processo

- Aplicar filtro de escopo apenas na view `processos.lista`
- Regra inicial: administrador vê tudo; gerente vê processos do departamento; advogado vê próprios
- Manter `responsavel=null` visível apenas para administrador
- Testar com múltiplos usuários antes de propagar

---

### Fase 2.10E — Propagar escopo gradualmente

Na ordem recomendada (menor risco → maior risco):

1. Tarefas
2. Agenda — usar `Q(responsavel=user) | Q(participantes=user)`, não só `responsavel`
3. Financeiro — definir regra própria para o papel `financeiro`
4. Dashboard — por último, após todos os módulos estarem consistentes

---

---

### Opção paralela — Segurança de usuários e onboarding (Fase 2.10 alternativa)

Pode ser feita antes ou em paralelo com o escopo de dados:

- Redefinição de senha pela interface (`PasswordChangeForm`)
- Desativação/reativação de usuários pela interface
- Edição do papel de usuário existente
- Convite por e-mail
- Confirmação real de e-mail
- Auditoria de ações administrativas

### Sequência recomendada após Fase 2.10

1. **Modelos** — templates de peças jurídicas
2. **Chat** — conversas internas por processo ou geral
