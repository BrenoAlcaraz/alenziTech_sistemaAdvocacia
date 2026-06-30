# Plano Fase 2.3 — Tarefas

**Status:** Concluído em nível básico  
**Data:** 2026-06-30

---

## Objetivo do módulo

Permitir que advogados e equipe do escritório criem, organizem e acompanhem tarefas operacionais — vinculadas ou não a processos e clientes — com visualização em quadro kanban e em lista, e com ações rápidas de mudança de status.

---

## Funcionalidades entregues

| Funcionalidade | Detalhe |
|---|---|
| Quadro kanban real | Tarefas agrupadas por status em 3 colunas: A fazer / Em andamento / Concluída |
| Visualização em lista | `/tarefas/lista/` com todos os metadados inline |
| Criação real | Formulário com título, descrição, prioridade, prazo, cliente e processo |
| Edição real | Mesmo formulário pré-preenchido; responsável e status protegidos |
| Vínculo com cliente | Opcional; seleção de clientes ativos |
| Vínculo com processo | Opcional; seleciona processos não arquivados |
| Auto-fill de cliente | Se processo escolhido e cliente vazio → preenche com `processo.cliente` |
| Prazo opcional | `DateField(null=True, blank=True)` com widget `type="date"` |
| Exibição de prazo | Badge urgente (≤ 3 dias), badge normal, "Prazo não informado" |
| Ordenação | 6 opções via `?ordem=`: prazo próximo/distante, prioridade alta/baixa, mais recentes/antigas |
| Normalização de ordem | Valor inválido normalizado para `prazo_proximo`; `<select>` reflete corretamente |
| Ação rápida: Iniciar | `a_fazer` → `em_andamento` via POST |
| Ação rápida: Concluir | Qualquer status → `concluida` via POST |
| Ação rápida: Reabrir | `concluida` → `a_fazer` via POST |
| Redirecionamento seguro | `next` validado com `url_has_allowed_host_and_scheme`; preserva `?ordem=` |
| Botão de edição | Ícone de lápis no card do quadro e na linha da lista |
| Remoção de mocks | Todos os dados temporários removidos de `views.py` |

---

## Decisões técnicas

- **`select_related`** obrigatório em todos os querysets: `.select_related("responsavel", "processo", "cliente")` para evitar N+1.
- **`F("campo").asc(nulls_last=True)`** / `.desc(nulls_last=True)` para ordenação NULL-aware em `DateField`.
- **`Case`/`When`/`Value`/`IntegerField`** para ordenação semântica de `prioridade` (não alfabética).
- **`ORDENS_VALIDAS` + `_normalizar_ordem()`** para whitelist de query params antes de usar em `.order_by()` e antes de passar ao template.
- **`_redirect_seguro(request)`** centraliza toda lógica de redirect pós-ação: lê `request.POST.get("next")`, valida com `url_has_allowed_host_and_scheme`, cai em `tarefas:quadro` se inválido.
- **`update_fields=["status"]`** nas ações rápidas para fazer `UPDATE` de coluna única, sem risco de sobrescrever outros campos.
- **Cores de prioridade por `style=""` inline** (não classes Tailwind) para evitar problemas de purge/compilação: Alta `#ef4444`/`#b91c1c`, Média `#D6D300`/`#78700a`, Baixa `#3b82f6`/`#1d4ed8`.
- **`next_url` no contexto** das views `quadro()` e `lista()` via `request.get_full_path()`, incluindo `?ordem=` se presente.

---

## Decisões de produto

- `responsavel` é definido automaticamente como o usuário logado (`request.user`) na criação; preservado na edição.
- `status` não aparece no formulário de criação nem de edição; controlado apenas pelas ações rápidas.
- Tarefa nasce com `status="a_fazer"`.
- Tarefa pode ter cliente sem processo.
- Tarefa pode ter processo sem cliente selecionado manualmente (auto-fill resolve).
- Processos arquivados não aparecem no select do formulário.
- Clientes inativos não aparecem no select do formulário.
- Ações rápidas são POST-only; GET não altera status.
- Exclusão não implementada; lixeira continua apenas visual.
- Ordenação por status não foi implementada (removida do escopo após diagnóstico).
- Transição `em_andamento` → `a_fazer` não implementada (reservada para etapa futura).

---

## Models utilizados

**`apps/tarefas/models.py` — `Tarefa`**

| Campo | Tipo | Detalhe |
|---|---|---|
| `titulo` | `CharField(max_length=255)` | Obrigatório |
| `descricao` | `TextField(blank=True)` | Opcional |
| `status` | `CharField`, choices | `a_fazer` / `em_andamento` / `concluida`; default `a_fazer` |
| `prioridade` | `CharField`, choices | `baixa` / `media` / `alta`; default `media` |
| `responsavel` | `ForeignKey(User, SET_NULL)` | Definido na view, não no form |
| `processo` | `ForeignKey(Processo, SET_NULL)` | Opcional |
| `cliente` | `ForeignKey(Cliente, SET_NULL)` | Opcional |
| `prazo` | `DateField(null=True, blank=True)` | Opcional |
| `criado_em` | `DateTimeField(auto_now_add=True)` | Imutável |

**Properties:**

- `prazo_urgente` — `True` se `prazo` existe e `(prazo - hoje).days <= 3`
- `prazo_label` — retorna `"sem prazo"` / `"prazo vencido"` / `"hoje"` / `"amanhã"` / `"em N dias"` (**nota**: retorna string truthy mesmo sem prazo — não usar para checar existência de prazo no template)

---

## Forms utilizados

**`apps/tarefas/forms.py` — `TarefaForm`**

`ModelForm` com `fields = ["titulo", "descricao", "prioridade", "prazo", "cliente", "processo"]`.

Campos explicitamente **fora** do form (protegidos): `responsavel`, `status`, `criado_em`.

Overrides:
- `cliente` → `ModelChoiceField(queryset=Cliente.objects.filter(ativo=True))`
- `processo` → `ModelChoiceField(queryset=Processo.objects.select_related("cliente").exclude(status="arquivado"))`
- `prazo` → `DateField(input_formats=["%Y-%m-%d"], widget=DateInput(type="date"))`

---

## Views implementadas

| View | Rota | Método | Descrição |
|---|---|---|---|
| `quadro` | `/tarefas/` | GET | Kanban agrupado por status, com ordenação e `next_url` |
| `lista` | `/tarefas/lista/` | GET | Lista tabular com metadados, ordenação e `next_url` |
| `nova` | `/tarefas/nova/` | GET/POST | Criação com `TarefaForm` |
| `editar` | `/tarefas/<pk>/editar/` | GET/POST | Edição com `TarefaForm(instance=tarefa)` |
| `concluir` | `/tarefas/<pk>/concluir/` | POST | `status = "concluida"` |
| `reabrir` | `/tarefas/<pk>/reabrir/` | POST | `status = "a_fazer"` |
| `iniciar` | `/tarefas/<pk>/iniciar/` | POST | `status = "em_andamento"` |

**Auxiliares privadas:**

- `_normalizar_ordem(ordem)` — whitelist + fallback para `"prazo_proximo"`
- `_get_order_args(ordem)` — retorna lista de argumentos para `.order_by()`
- `_redirect_seguro(request)` — valida `next` e redireciona com segurança

---

## Rotas implementadas

```python
path("tarefas/", views.quadro, name="quadro"),
path("tarefas/lista/", views.lista, name="lista"),
path("tarefas/nova/", views.nova, name="nova"),
path("tarefas/<int:pk>/editar/", views.editar, name="editar"),
path("tarefas/<int:pk>/concluir/", views.concluir, name="concluir"),
path("tarefas/<int:pk>/reabrir/", views.reabrir, name="reabrir"),
path("tarefas/<int:pk>/iniciar/", views.iniciar, name="iniciar"),
```

---

## Templates principais

| Template | Descrição |
|---|---|
| `templates/tarefas/quadro.html` | Quadro kanban com 3 colunas e seletor de ordenação |
| `templates/tarefas/lista.html` | Lista tabular com metadados, ordenação e ações inline |
| `templates/tarefas/form.html` | Formulário compartilhado para criação e edição (alterna via `modo`) |
| `templates/tarefas/_card_tarefa.html` | Card reutilizável: prazo, responsável, processo/cliente, prioridade, ações |

---

## Ordenação

Opções via `?ordem=`:

| Valor | Critério |
|---|---|
| `prazo_proximo` (padrão) | `F("prazo").asc(nulls_last=True)`, depois título |
| `prazo_distante` | `F("prazo").desc(nulls_last=True)`, depois título |
| `prioridade_alta` | `Case/When` alta→1, média→2, baixa→3, depois título |
| `prioridade_baixa` | `Case/When` baixa→1, média→2, alta→3, depois título |
| `mais_recentes` | `-criado_em` |
| `mais_antigas` | `criado_em` |

Valores inválidos são normalizados para `prazo_proximo` antes de passar ao template e ao queryset.

---

## Ações rápidas

Todas usam `<form method="post">` com `{% csrf_token %}` e `<input type="hidden" name="next" value="{{ next_url }}">`.

| Status atual | Botões exibidos |
|---|---|
| `a_fazer` | **Iniciar** + **Concluir** |
| `em_andamento` | **Concluir** |
| `concluida` | **Reabrir** |

GET direto nas rotas de ação não altera status — apenas redireciona via `_redirect_seguro`.

---

## Limitações conhecidas

- **Tarefa com processo arquivado já vinculado**: o `TarefaForm` exclui processos arquivados do queryset, então ao editar uma tarefa com esse vínculo o campo aparece vazio e o processo pode ser perdido silenciosamente ao salvar. Não corrigido nesta fase.
- **Tarefa com cliente inativo já vinculado**: mesma situação — cliente não aparece no select ao editar.
- **`prazo_label` sempre truthy**: a property retorna `"sem prazo"` mesmo quando `prazo is None`. Templates não devem usar `{% if tarefa.prazo_label %}` para checar existência de prazo — usar `{% if tarefa.prazo %}`.
- **Responsável não selecionável**: definido como o usuário logado na criação e preservado na edição. Não há UI para reatribuição.
- **Exclusão ausente**: lixeira é visual; não há endpoint de exclusão.

---

## Pendências futuras

- Exclusão/arquivamento de tarefa
- Detalhe de tarefa com histórico
- Responsável selecionável
- Transição `em_andamento` → `a_fazer`
- Tratamento de cliente inativo / processo arquivado em edição
- Busca por título e descrição
- Filtros por status, prioridade, responsável, cliente, processo e prazo
- Paginação
- Calendário ou agenda de tarefas
- Notificações de vencimento
- Tarefas recorrentes
- Anexos
- Comentários internos
- Histórico de alterações / auditoria
- Permissões por grupo/cargo
- Correção da property `prazo_label` (retorno falsy quando sem prazo)

---

## Próximos passos recomendados

**Fase 2.4 — Agenda/Prazos** (recomendada)

Motivo: prazos processuais têm consequência legal direta. A aba "Prazos" no detalhe de Processo já existe com empty state aguardando implementação. Agenda completa o workflow diário iniciado por Tarefas.

Alternativa: **Fase 2.4 — Financeiro**, se a prioridade for gestão administrativa e controle de honorários/custas.
