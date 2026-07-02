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

## Fase 2.5 — Próximo módulo recomendado: Financeiro

**Fase 2.5 — Financeiro** é o próximo bloco operacional natural.

Após Clientes, Processos, Tarefas e Agenda/Prazos, o escritório já tem os módulos de operação jurídica diária cobertos no nível básico. O próximo passo relevante é o controle financeiro básico:

- Receitas e despesas por processo/cliente
- Honorários (fixo, por êxito, por hora)
- Vencimentos e contas a receber/pagar
- Status de pagamento (pendente, pago, inadimplente)
- Custo de processo (custas judiciais, perícias, diligências)

### Sequência recomendada após Fase 2.5

1. **Modelos** — templates de peças jurídicas
2. **Configurações** — usuários e perfis do escritório por tenant
3. **Chat** — conversas internas por processo ou geral

Cada módulo seguirá o mesmo padrão: listar → criar → editar → arquivar/reativar.
