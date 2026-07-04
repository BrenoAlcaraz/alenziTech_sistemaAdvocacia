# Plano Fase 2.5 — Financeiro

**Status**: concluído em nível básico (lançamentos financeiros)
**Data de conclusão**: 2026-07-04

---

## Objetivo do módulo

Implementar o controle financeiro básico do escritório: lançamentos de receitas e despesas vinculados a clientes e processos, com CRUD completo, ações rápidas de status e cards de resumo com valores reais.

---

## Funcionalidades entregues

| Funcionalidade | Status |
|---|---|
| Model `LancamentoFinanceiro` estruturado | ✅ |
| Listagem real com filtros | ✅ |
| 5 cards de resumo com valores reais | ✅ |
| Criação real de lançamento | ✅ |
| Edição real de lançamento | ✅ |
| Validação: status pago exige data de pagamento | ✅ |
| Auto-fill de cliente pelo processo | ✅ |
| Responsável selecionável com fallback | ✅ |
| Ação rápida: Marcar como pago | ✅ |
| Ação rápida: Cancelar | ✅ |
| Ação rápida: Reabrir | ✅ |
| Exclusão real com confirmação | ✅ |
| Preservação de filtro via `next` | ✅ |
| Ícones de edição e exclusão na lista | ✅ |

---

## Decisões técnicas

### Model único

Optou-se por um único model `LancamentoFinanceiro` com campo `tipo` (`receita` / `despesa`), ao invés de dois models separados. Essa decisão simplifica queries, forms, filtros e views.

### Renomeação de campo

O campo `data` foi renomeado para `data_vencimento` via `RenameField` na migration `0002`, preservando os dados existentes. A `data_vencimento` permaneceu obrigatória (`NOT NULL`, `NOT blank`).

### `atrasado` como property, não campo

O `atrasado` não é armazenado no banco. É calculado dinamicamente:

```python
@property
def atrasado(self):
    return (
        self.status == "pendente"
        and self.data_vencimento is not None
        and self.data_vencimento < timezone.localdate()
    )
```

Isso evita dados desatualizados e elimina a necessidade de tasks periódicos de atualização.

### `_formatar_moeda` na view

A formatação de moeda brasileira (`R$ 1.234,56`) foi implementada como helper simples na `views.py`, sem criar template tag customizada. Nos cards usa o helper; na lista usa `{{ l.valor|floatformat:2 }}`. Refinamento futuro pode centralizar em template tag ou filtro.

### Redirecionamento com `next`

O padrão `_redirect_seguro(request)` + `next_url = request.get_full_path()` + `<input type="hidden" name="next">` foi aplicado nas ações rápidas e na exclusão, preservando o filtro ativo (`?filtro=pendentes`, `?filtro=pagos`, etc.) após cada ação.

---

## Decisões de produto

### Status disponíveis

Três status: `pendente`, `pago`, `cancelado`. Não há "inadimplente" como status fixo — o badge "Atrasado" é exibido dinamicamente quando `status=pendente` e a data de vencimento já passou.

### Status aparece no formulário

O status é editável no formulário de criação e edição. Isso permite registrar lançamentos retroativos já como pagos sem ter que usar a ação rápida depois.

### Data de pagamento obrigatória para status pago

Implementado via `clean()` no form:

```python
if status == "pago" and not data_pagamento:
    self.add_error("data_pagamento", "Informe a data de pagamento para lançamentos pagos.")
```

### Marcar como pago preenche data automaticamente

A ação rápida "Marcar como pago" define `data_pagamento = timezone.localdate()` automaticamente, evitando que o usuário esqueça de informar a data.

### Reabrir limpa data de pagamento

Ao reabrir (`pendente`), `data_pagamento` é definida como `None`. Semanticamente, o lançamento ainda não foi pago.

### CustaJudicial mantido, sem UI real

O model `CustaJudicial` existe no banco e no admin, mas a tela de Custas ainda usa mocks. O fluxo real de custas (adiantamentos, depósitos, saldos por cliente) fica para etapa futura.

### Exclusão permanente

Foi implementado `lancamento.delete()`. Soft delete/arquivamento fica para etapa futura quando houver necessidade operacional clara.

---

## Models utilizados

### `LancamentoFinanceiro` (`apps/financeiro/models.py`)

| Campo | Tipo | Observação |
|---|---|---|
| `tipo` | `CharField` | `receita` / `despesa` |
| `descricao` | `CharField(255)` | obrigatório |
| `valor` | `DecimalField(12,2)` | obrigatório |
| `data_vencimento` | `DateField` | obrigatório; renomeado de `data` |
| `status` | `CharField` | `pendente` / `pago` / `cancelado`; default `pendente` |
| `categoria` | `CharField` | 13 choices; default `honorario` |
| `forma_pagamento` | `CharField` | 6 choices; blank |
| `data_pagamento` | `DateField` | null/blank; obrigatório quando `status="pago"` |
| `observacoes` | `TextField` | blank |
| `cliente` | `ForeignKey(Cliente)` | SET_NULL, null/blank |
| `processo` | `ForeignKey(Processo)` | SET_NULL, null/blank |
| `responsavel` | `ForeignKey(User)` | SET_NULL, null/blank |
| `criado_em` | `DateTimeField` | auto_now_add |

### `CustaJudicial` (`apps/financeiro/models.py`)

Mantido no banco. Sem fluxo real completo nesta fase.

---

## Forms utilizados

### `LancamentoFinanceiroForm` (`apps/financeiro/forms.py`)

- `ModelForm` com 12 campos (exclui `criado_em`)
- Querysets filtrados: `Cliente.objects.filter(ativo=True)`, `Processo.objects.exclude(status="arquivado")`
- Widgets: `DateInput(type="date")` para datas; `Textarea` para observações; classe `input` / `select`
- `clean()`: valida que `data_pagamento` é obrigatória quando `status="pago"`

---

## Views implementadas

| View | Método | Ação |
|---|---|---|
| `index` | GET | lista, filtros, cards de resumo |
| `form_lancamento` | GET/POST | criar lançamento |
| `editar_lancamento` | GET/POST | editar lançamento |
| `marcar_pago` | POST-only | `status="pago"`, `data_pagamento=hoje` |
| `cancelar_lancamento` | POST-only | `status="cancelado"` |
| `reabrir_lancamento` | POST-only | `status="pendente"`, `data_pagamento=None` |
| `excluir_lancamento` | POST-only | `lancamento.delete()` |
| `custas` | GET | lista custas (ainda mock) |
| `form_custa` | GET | formulário de custa (ainda mock) |

---

## Rotas implementadas

| URL | Name | View |
|---|---|---|
| `financeiro/` | `index` | `index` |
| `financeiro/custas/` | `custas` | `custas` |
| `financeiro/lancamentos/novo/` | `form_lancamento` | `form_lancamento` |
| `financeiro/lancamentos/<pk>/editar/` | `editar_lancamento` | `editar_lancamento` |
| `financeiro/lancamentos/<pk>/marcar-pago/` | `marcar_pago` | `marcar_pago` |
| `financeiro/lancamentos/<pk>/cancelar/` | `cancelar_lancamento` | `cancelar_lancamento` |
| `financeiro/lancamentos/<pk>/reabrir/` | `reabrir_lancamento` | `reabrir_lancamento` |
| `financeiro/lancamentos/<pk>/excluir/` | `excluir_lancamento` | `excluir_lancamento` |
| `financeiro/custas/nova/` | `form_custa` | `form_custa` |

---

## Templates principais

| Template | Descrição |
|---|---|
| `financeiro/index.html` | Listagem com filtros, cards e ações por card |
| `financeiro/form_lancamento.html` | Formulário real (criação e edição via `modo`) |
| `financeiro/custas.html` | Custas (ainda mock) |
| `financeiro/form_custa.html` | Formulário de custa (ainda mock) |

---

## Filtros

| Valor | Lógica |
|---|---|
| `todos` | sem filtro adicional (padrão) |
| `pendentes` | `status="pendente"` |
| `pagos` | `status="pago"` |
| `atrasados` | `status="pendente"` + `data_vencimento__lt=hoje` |
| `receitas` | `tipo="receita"` |
| `despesas` | `tipo="despesa"` |
| `mes_atual` | `data_vencimento__year=ano` + `data_vencimento__month=mes` |

Filtro inválido → normalizado para `todos`.

---

## Cards de resumo

| Card | Lógica |
|---|---|
| A receber | `Sum("valor")` onde `tipo="receita"` e `status="pendente"` |
| A pagar | `Sum("valor")` onde `tipo="despesa"` e `status="pendente"` |
| Recebido no mês | `Sum("valor")` onde `tipo="receita"`, `status="pago"`, `data_pagamento` no mês atual |
| Pago no mês | `Sum("valor")` onde `tipo="despesa"`, `status="pago"`, `data_pagamento` no mês atual |
| Saldo previsto | A receber − A pagar |

---

## Ações rápidas

| Ação | Transição | Campos alterados |
|---|---|---|
| Marcar como pago | `pendente` → `pago` | `status`, `data_pagamento = hoje` |
| Cancelar | `pendente` → `cancelado` | `status` |
| Reabrir | `pago`/`cancelado` → `pendente` | `status`, `data_pagamento = None` |

Todas usam `update_fields` para UPDATE single-column.
GET direto nas rotas não altera dados.

---

## Exclusão

- POST-only: `lancamento.delete()`
- GET direto redireciona sem excluir
- Confirm nativo do browser antes do POST
- Preserva `?filtro=` via `next`

---

## Limitações conhecidas

- `CustaJudicial` existe no banco mas sem UI real funcional
- Formatação de valor na lista (`floatformat:2`) pode ser refinada futuramente
- Clientes inativos ou processos arquivados já vinculados a lançamentos existentes não têm tratamento especial no formulário de edição
- UX do formulário e da listagem pendente de revisão com o sócio

---

## Pendências futuras

- Fluxo real de Custas Judiciais
- Filtros avançados (cliente, processo, período, categoria)
- Busca textual por descrição
- Relatórios por cliente, por processo, mensais
- Gráficos de receitas vs. despesas
- DRE
- Recorrência de lançamentos
- Anexos/comprovantes de pagamento
- Exportação Excel/PDF
- Integração bancária (extrato OFX)
- Emissão de boletos via API
- Notas fiscais (NFS-e)
- Conciliação bancária
- Permissões financeiras por cargo/grupo
- Auditoria/logs de alterações
- Soft delete/arquivamento (exclusão permanente foi implementada)
- Revisão de UX do formulário e listagem com o sócio

---

## Próximos passos recomendados

**Fase 2.6 — Dashboard real**

Substituir os mocks do Dashboard por indicadores reais dos módulos já funcionais:

- Total de clientes ativos
- Processos ativos
- Tarefas pendentes e em andamento
- Compromissos dos próximos 7 dias
- Lançamentos financeiros pendentes (A receber / A pagar)
- Receitas e despesas do mês atual
- Cards e listas reais sem dados mockados
