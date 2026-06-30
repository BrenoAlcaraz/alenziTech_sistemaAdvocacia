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
✅ Mocks removidos de `views.py`

### Pendências futuras de Tarefas (não bloqueantes)

- **Exclusão/arquivamento de tarefa** — lixeira atualmente é apenas visual
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

## Fase 2.4 — Próximo módulo recomendado

### Opções disponíveis

**Opção A — Agenda/Prazos**
Compromissos, audiências e prazos processuais com visualização de calendário.
Prioridade: operação diária do escritório — advogado nunca perde prazo, sabe o que tem na semana.

**Opção B — Financeiro**
Lançamentos, custas e receitas por processo/cliente. Controle de honorários.
Prioridade: gestão administrativa — sócio/gerente acompanha fluxo de caixa e inadimplência.

### Recomendação técnica

**Recomendado: Fase 2.4 — Agenda/Prazos.**

Razão: tarefas e agenda são complementares no workflow diário do advogado. O módulo Tarefas cobre atividades internas; a Agenda cobre compromissos externos (audiências, perícias, reuniões) e prazos processuais (que têm data limite legal). O risco de perder um prazo processual é muito maior do que o risco financeiro de curto prazo. Além disso, o model de Processo já tem um slot implícito de "Prazos" (aba em detalhe com empty state) que aguarda implementação real.

Se a prioridade do escritório for **gestão administrativa e fluxo de caixa**, escolher Financeiro.
Se a prioridade for **operação diária e controle de prazos legais**, escolher Agenda/Prazos.

---

## Sequência recomendada após Fase 2.4

1. **Financeiro** — lançamentos, custas e honorários
2. **Modelos** — templates de peças jurídicas
3. **Configurações** — usuários e perfis do escritório por tenant
4. **Chat** — conversas internas por processo ou geral

Cada módulo seguirá o mesmo padrão: listar → criar → editar → arquivar/reativar.
