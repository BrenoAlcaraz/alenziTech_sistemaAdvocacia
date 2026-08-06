# Plano Fase 2.4 — Agenda/Prazos

**Status:** Concluído em nível básico  
**Data:** 2026-07-02

---

## Objetivo do módulo

Permitir que advogados e equipe do escritório registrem, visualizem e gerenciem compromissos jurídicos — audiências, prazos, reuniões, protocolos, perícias, julgamentos e retornos — vinculados ou não a processos e clientes, com ações rápidas de mudança de status e exclusão direta pela lista.

---

## Funcionalidades entregues

| Funcionalidade | Detalhe |
|---|---|
| Model `Compromisso` estruturado | tipo, status, dia_inteiro, responsavel, processo, cliente, data_hora_inicio, data_hora_fim, local, descricao |
| Vínculo opcional com processo | `ForeignKey(Processo, SET_NULL)` |
| Vínculo opcional com cliente | `ForeignKey(Cliente, SET_NULL)` |
| Status | `agendado` / `concluido` / `cancelado`; default `agendado` |
| Tipos | audiência, prazo, reunião, protocolo, perícia, julgamento, retorno, outro |
| Campo `dia_inteiro` | oculta horário na exibição da lista |
| Listagem real | `select_related("responsavel", "processo", "cliente")` com filtro por período |
| Filtro: Próximos 7 dias | data entre hoje e hoje+7 (padrão ao entrar na lista) |
| Filtro: Hoje | `data_hora_inicio__date=hoje` |
| Filtro: Vencidos | `data_hora_inicio__lt=agora` + `status="agendado"` |
| Filtro: Todos | sem restrição de data ou status |
| Normalização de filtro | valor inválido normalizado para `proximos_7` |
| Criação real | `CompromissoForm` + POST; `status` e `responsavel` definidos na view |
| Edição real | `CompromissoForm(instance=compromisso)`; `status` preservado |
| Auto-fill de cliente | se processo escolhido e cliente vazio → preenche com `processo.cliente` |
| Responsável selecionável | select de usuários ativos; fallback para `request.user` na criação |
| Ação rápida: Concluir | `agendado` → `concluido` via POST |
| Ação rápida: Cancelar | `agendado` → `cancelado` via POST |
| Ação rápida: Reabrir | `concluido`/`cancelado` → `agendado` via POST |
| Exclusão real | `compromisso.delete()` via POST; GET não remove; confirm nativo do browser |
| Redirecionamento seguro | `next` validado com `url_has_allowed_host_and_scheme`; preserva `?filtro=` |
| Ícone de edição na lista | lápis por card, redireciona para formulário de edição |
| Ícone de exclusão na lista | lixeira por card, à direita do lápis, POST com confirm |
| Remoção de mocks | `/agenda/` passou a renderizar a lista real em vez do calendário estático |

---

## Decisões técnicas

- **`select_related`** obrigatório em todos os querysets: `.select_related("responsavel", "processo", "cliente")` para evitar N+1.
- **`FILTROS_VALIDOS` + `_normalizar_filtro()`** para whitelist de query params antes de usar no queryset e passar ao template.
- **Filtro `vencidos`** considera apenas `status="agendado"` — compromissos concluídos ou cancelados no passado são registros históricos, não vencidos.
- **`_redirect_seguro(request)`** centraliza toda lógica de redirect pós-ação: lê `request.POST.get("next")`, valida com `url_has_allowed_host_and_scheme`, cai em `agenda:index` se inválido.
- **`update_fields=["status"]`** nas ações rápidas para fazer `UPDATE` de coluna única, sem risco de sobrescrever outros campos.
- **`compromisso.delete()`** na view `excluir()`: hard delete direto, POST-only; soft delete adiado para etapa futura.
- **`status_original`** salvo antes de `form.save(commit=False)` na edição e restaurado após, impedindo que o form sobrescreva o status com o default do model.
- **Cores de tipo por `style=""` inline** (não classes Tailwind) para evitar problemas de purge/compilação com valores dinâmicos.
- **Cores de status por classes Tailwind completas** em blocos `{% if %}` — strings literais são seguras contra purge.
- **`next_url` no contexto** de `index()` via `request.get_full_path()`, incluindo `?filtro=` se presente.
- **`templates/agenda/index.html`** mantido intacto como referência visual para o calendário mensal futuro; não foi alterado nem removido.

---

## Decisões de produto

- Modelo único `Compromisso` cobre agenda e prazos — diferenciação feita pelo campo `tipo`.
- `status` não aparece no formulário de criação nem de edição; controlado apenas pelas ações rápidas.
- Compromisso nasce com `status="agendado"`.
- Compromisso pode ter cliente sem processo.
- Compromisso pode ter processo sem cliente selecionado manualmente (auto-fill resolve).
- Quando processo é escolhido e cliente está vazio, o cliente é preenchido automaticamente com `processo.cliente`.
- Processos arquivados não aparecem no select do formulário.
- Clientes inativos não aparecem no select do formulário.
- Campo `participantes` (M2M) existe no model mas ficou fora do formulário básico; implementação futura.
- Responsável é selecionável entre usuários ativos; fallback para `request.user` na criação.
- Ações rápidas são POST-only; GET direto nas rotas não altera status.
- Exclusão implementada como hard delete (`compromisso.delete()`); soft delete/arquivamento adiado.
- Confirmação de exclusão via `confirm()` nativo do browser; modal customizado adiado.

---

## Models utilizados

**`apps/agenda/models.py` — `Compromisso`**

| Campo | Tipo | Detalhe |
|---|---|---|
| `titulo` | `CharField(max_length=255)` | Obrigatório |
| `descricao` | `TextField(blank=True)` | Opcional |
| `tipo` | `CharField`, choices | audiencia / prazo / reuniao / protocolo / pericia / julgamento / retorno / outro |
| `status` | `CharField`, choices | agendado / concluido / cancelado; default `agendado` |
| `dia_inteiro` | `BooleanField(default=False)` | Oculta horário na exibição |
| `data_hora_inicio` | `DateTimeField` | Obrigatório |
| `data_hora_fim` | `DateTimeField(null=True, blank=True)` | Opcional |
| `local` | `CharField(max_length=255, blank=True)` | Opcional |
| `responsavel` | `ForeignKey(User, SET_NULL)` | Selecionável; fallback para usuário logado |
| `participantes` | `ManyToManyField(User, blank=True)` | Fora do formulário por ora |
| `processo` | `ForeignKey(Processo, SET_NULL)` | Opcional |
| `cliente` | `ForeignKey(Cliente, SET_NULL)` | Opcional; auto-fill via processo |
| `criado_em` | `DateTimeField(auto_now_add=True)` | Imutável |

---

## Forms utilizados

**`apps/agenda/forms.py` — `CompromissoForm`**

`ModelForm` com `fields = ["titulo", "descricao", "tipo", "dia_inteiro", "data_hora_inicio", "data_hora_fim", "local", "responsavel", "cliente", "processo"]`.

Campos explicitamente **fora** do form (protegidos): `status`, `participantes`, `criado_em`.

Overrides:
- `cliente` → `ModelChoiceField(queryset=Cliente.objects.filter(ativo=True))`
- `processo` → `ModelChoiceField(queryset=Processo.objects.select_related("cliente").exclude(status="arquivado"))`
- `responsavel` → `ModelChoiceField(queryset=User.objects.filter(is_active=True).order_by("first_name", "username"))`
- `data_hora_inicio` → `DateTimeField(input_formats=["%Y-%m-%dT%H:%M"], widget=DateTimeInput(type="datetime-local"))`
- `data_hora_fim` → idem, `required=False`

---

## Views implementadas

| View | Rota | Método | Descrição |
|---|---|---|---|
| `index` | `/agenda/` | GET | Lista com filtros por período e `next_url` |
| `form_compromisso` | `/agenda/novo/` | GET/POST | Criação com `CompromissoForm` |
| `editar` | `/agenda/<pk>/editar/` | GET/POST | Edição com `CompromissoForm(instance=compromisso)` |
| `concluir` | `/agenda/<pk>/concluir/` | POST | `status = "concluido"` |
| `cancelar` | `/agenda/<pk>/cancelar/` | POST | `status = "cancelado"` |
| `reabrir` | `/agenda/<pk>/reabrir/` | POST | `status = "agendado"` |
| `excluir` | `/agenda/<pk>/excluir/` | POST | `compromisso.delete()` |

**Auxiliares privadas:**

- `_normalizar_filtro(filtro)` — whitelist + fallback para `"proximos_7"`
- `_redirect_seguro(request)` — valida `next` e redireciona com segurança

---

## Rotas implementadas

```python
path("agenda/", views.index, name="index"),
path("agenda/novo/", views.form_compromisso, name="novo"),
path("agenda/<int:pk>/editar/", views.editar, name="editar"),
path("agenda/<int:pk>/concluir/", views.concluir, name="concluir"),
path("agenda/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
path("agenda/<int:pk>/reabrir/", views.reabrir, name="reabrir"),
path("agenda/<int:pk>/excluir/", views.excluir, name="excluir"),
```

---

## Templates principais

| Template | Descrição |
|---|---|
| `templates/agenda/lista.html` | Lista com filtros, badges de tipo/status, metadados, ações rápidas e ícones de editar/excluir |
| `templates/agenda/form.html` | Formulário compartilhado para criação e edição (alterna via `modo`) |
| `templates/agenda/index.html` | Calendário estático mantido como referência visual para implementação futura |

---

## Filtros por período

Implementados via `?filtro=` na URL:

| Valor | Critério | Observação |
|---|---|---|
| `proximos_7` (padrão) | `data_hora_inicio__date` entre hoje e hoje+7 | Inclui hoje |
| `hoje` | `data_hora_inicio__date=hoje` | Apenas o dia atual |
| `vencidos` | `data_hora_inicio__lt=agora` + `status="agendado"` | Apenas pendentes no passado |
| `todos` | sem restrição | Todos os registros do tenant |

Valores inválidos são normalizados para `proximos_7` antes de passar ao template e ao queryset.

---

## Ações rápidas

Todas usam `<form method="post">` com `{% csrf_token %}` e `<input type="hidden" name="next" value="{{ next_url }}">`.

| Status atual | Botões exibidos |
|---|---|
| `agendado` | **Concluir** + **Cancelar** |
| `concluido` | **Reabrir** |
| `cancelado` | **Reabrir** |

GET direto nas rotas de ação não altera status — apenas redireciona via `_redirect_seguro`.

---

## Exclusão

- Rota: `POST /agenda/<pk>/excluir/`
- View: `excluir(request, pk)` — `get_object_or_404` + `compromisso.delete()` se POST
- Template: formulário POST com lixeira à direita do lápis de editar; `onclick="return confirm(...)"` para confirmação nativa
- GET direto não exclui — redireciona via `_redirect_seguro`
- `next_url` preserva o filtro ativo após a exclusão

---

## Limitações conhecidas

- **Compromisso com processo arquivado já vinculado**: o `CompromissoForm` exclui processos arquivados do queryset — ao editar, o campo aparece vazio e o processo pode ser perdido silenciosamente ao salvar. Não corrigido nesta fase.
- **Compromisso com cliente inativo já vinculado**: mesma situação.
- **Participantes**: campo `ManyToManyField` existe no model mas fora do formulário; não é possível adicionar participantes pela UI ainda.
- **Soft delete ausente**: exclusão remove permanentemente; arquivamento reversível não implementado.
- **Calendário dinâmico ausente**: `/agenda/` exibe lista; calendário mensal está em `index.html` como referência visual estática.

---

## Pendências futuras

- Calendário mensal dinâmico (template `index.html` mantido como referência)
- Navegação por mês no calendário
- Visão semanal e diária
- Cálculo de prazos úteis (excluindo feriados e fins de semana)
- Integração de prazos com processos
- Criação automática de prazo a partir de movimentação processual
- Notificações de vencimento
- Compromissos recorrentes
- Integração com Google Calendar
- Participantes no formulário
- Permissões por grupo/cargo
- Auditoria/logs
- Soft delete/arquivamento
- Busca e filtros avançados (por tipo, responsável, processo, cliente)
- Tratamento de cliente inativo/processo arquivado em edição

---

## Próximos passos recomendados

**Fase 2.5 — Financeiro** (recomendada)

Motivo: com Clientes, Processos, Tarefas e Agenda/Prazos cobertos no nível básico, o próximo bloco de valor para o escritório é controle financeiro — honorários, custas, contas a receber e inadimplência. Permite ao sócio/gerente acompanhar fluxo de caixa vinculado aos processos já cadastrados.
