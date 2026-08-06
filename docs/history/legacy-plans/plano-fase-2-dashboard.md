# Plano Fase 2.6 — Dashboard real

**Status**: concluído em nível básico
**Data de conclusão**: 2026-07-07

---

## Objetivo do módulo

Substituir o Dashboard completamente mockado por um painel com dados reais dos módulos já funcionais (Clientes, Processos, Tarefas, Agenda/Prazos, Financeiro), tornando-o útil para a operação diária do escritório.

---

## Funcionalidades entregues

| Funcionalidade | Status |
|---|---|
| Cards reais: Clientes ativos | ✅ |
| Cards reais: Processos ativos | ✅ |
| Cards reais: Tarefas pendentes | ✅ |
| Cards reais: Compromissos próximos | ✅ |
| Cards reais: A receber (receitas pendentes) | ✅ |
| Cards reais: A pagar (despesas pendentes) | ✅ |
| Formatação de moeda brasileira nos cards financeiros | ✅ |
| Cards clicáveis como atalhos para módulos | ✅ |
| Hover visual discreto nos cards | ✅ |
| Lista real: Tarefas pendentes | ✅ |
| Lista real: Agenda próxima | ✅ |
| Lista real: Financeiro pendente | ✅ |
| Links inferiores ("Ver todas", "Ver agenda", "Ver financeiro") | ✅ |
| `RESUMO_MOCK` removido | ✅ |
| `CASOS_MOCK` removido | ✅ |
| Correção de inconsistência Agenda próxima (card vs. lista) | ✅ |

---

## Decisões técnicas

### Dashboard sem model próprio

O app `dashboard` não tem `models.py` e não gera migrations. Ele apenas importa e consulta os models dos outros apps. Essa decisão mantém o painel como uma camada de apresentação pura, sem acoplamento de dados próprio.

### Sequência de implementação

A fase foi dividida em mini-etapas:

1. Diagnóstico do estado atual e identificação de mocks
2. Cards reais (substituir `RESUMO_MOCK`)
3. Listas reais (substituir `CASOS_MOCK`)
4. Links e refinamentos (cards clicáveis)
5. Documentação

### Remoção de mocks

`RESUMO_MOCK` e `CASOS_MOCK` eram constantes de módulo em `apps/dashboard/views.py`. Foram removidos completamente. A view `painel()` passou a usar apenas queries reais.

### `_formatar_moeda` na view

A formatação de moeda brasileira (`R$ 1.234,56`) foi implementada como helper local em `apps/dashboard/views.py`, replicando o mesmo helper já existente em `apps/financeiro/views.py`. Não foi criada uma template tag para evitar complexidade desnecessária nesta fase.

### Cards superiores como `<a>` em vez de `<div>`

Os 6 cards foram transformados de `<div class="card ...">` para `<a href="..." class="card ...">`. A tag `<a>` é block-level em HTML5 e aceita qualquer filho — todos os utilitários Tailwind da classe `card` funcionam identicamente. O cursor pointer é nativo do elemento `<a>` com href.

### Hover nos cards

```
hover:shadow-md transition-shadow duration-150
```

Aumenta a sombra suavemente ao passar o mouse. Sem cor nova, sem borda extra — compatível com a paleta bege/ouro/off-white do projeto.

### `plano_nome` hardcoded

O badge de plano exibe `"Mestre"` hardcoded. O billing/SaaS (`saas_billing`) ainda não tem fluxo real implementado. A substituição por dados reais de `Assinatura` fica para etapa futura.

### `agora = timezone.now()` removido

Inicialmente adicionado para a query de compromissos, foi removido após a correção da regra de negócio (ver próxima seção). `timezone.localdate()` via `hoje` é suficiente para todas as queries da view.

---

## Decisões de produto

### Agenda próxima — regra por data, não por datetime

**Problema identificado:** a query inicial usava `data_hora_inicio__gte=agora` (datetime exato). Isso fazia compromissos desaparecerem da lista imediatamente após seu horário de início — mesmo que tivessem começado há segundos. O card superior, por sua vez, usava `data_hora_inicio__date__gte=hoje` e continuava contando o compromisso. Resultado: card mostrava 1, lista mostrava 0 — inconsistência visual.

**Correção:** a lista de Agenda próxima passou a usar a mesma regra da Agenda (`proximos_7`) e do card superior:

```python
.filter(
    status="agendado",
    data_hora_inicio__date__gte=hoje,
    data_hora_inicio__date__lte=hoje + timedelta(days=7),
)
```

**Justificativa de produto:** um compromisso agendado para hoje às 14h ainda é operacionalmente relevante às 16h — pode estar em andamento, pode precisar de acompanhamento. A data é a granularidade correta para o painel de um escritório.

### Processos com prazo próximo — fora desta fase

O field `prazo_proximo` existe no model `Processo` (`DateField null/blank`). A query seria:

```python
Processo.objects.filter(status="ativo", prazo_proximo__isnull=False).order_by("prazo_proximo")[:5]
```

Ficou fora desta fase porque:
- O field é opcional e provavelmente vazio para a maioria dos processos em uso inicial
- 3 colunas de listas já é o limite natural do grid desktop
- A preferência do usuário foi começar com 3 listas e avaliar depois

### Links dos cards financeiros

| Card | Link | Filtro |
|---|---|---|
| A receber | `financeiro/?filtro=receitas` | Aba de receitas |
| A pagar | `financeiro/?filtro=despesas` | Aba de despesas |

O link "Ver financeiro" do bloco inferior usa `?filtro=pendentes` — cada atalho tem intenção diferente.

### Não implementar gráficos nesta fase

Gráficos aumentam complexidade de template e dependem de bibliotecas JS externas (Chart.js, ApexCharts) ou renderização server-side. Ficam para fase futura após decisão de qual biblioteca usar.

### Não implementar filtros internos nesta fase

O Dashboard mostra uma visão geral. Filtros por período, responsável ou área pertencem aos módulos individuais. O usuário pode navegar para o módulo correspondente pelos links e cards.

---

## Models consumidos

| Model | App | Campos/queries usados |
|---|---|---|
| `Cliente` | `clientes` | `filter(ativo=True).count()` |
| `Processo` | `processos` | `filter(status="ativo").count()` |
| `Tarefa` | `tarefas` | `exclude(status="concluida").count()` + lista |
| `Compromisso` | `agenda` | `filter(status="agendado", data_hora_inicio__date...)` + lista |
| `LancamentoFinanceiro` | `financeiro` | `Sum("valor")` por tipo/status + lista pendentes |

---

## Views implementadas/ajustadas

### `apps/dashboard/views.py`

Única view: `painel(request)`.

Queries de cards:
```python
hoje = timezone.localdate()

clientes_ativos = Cliente.objects.filter(ativo=True).count()
processos_ativos = Processo.objects.filter(status="ativo").count()
tarefas_pendentes = Tarefa.objects.exclude(status="concluida").count()
compromissos_proximos = Compromisso.objects.filter(
    status="agendado",
    data_hora_inicio__date__gte=hoje,
    data_hora_inicio__date__lte=hoje + timedelta(days=7),
).count()
a_receber = LancamentoFinanceiro.objects.filter(tipo="receita", status="pendente").aggregate(total=Sum("valor"))["total"] or Decimal("0")
a_pagar   = LancamentoFinanceiro.objects.filter(tipo="despesa", status="pendente").aggregate(total=Sum("valor"))["total"] or Decimal("0")
```

Queries de listas:
```python
tarefas_dashboard = (
    Tarefa.objects.select_related("cliente", "processo", "responsavel")
    .exclude(status="concluida")
    .order_by("prazo", "-prioridade")[:5]
)

compromissos_dashboard = (
    Compromisso.objects.select_related("cliente", "processo", "responsavel")
    .filter(
        status="agendado",
        data_hora_inicio__date__gte=hoje,
        data_hora_inicio__date__lte=hoje + timedelta(days=7),
    )
    .order_by("data_hora_inicio")[:5]
)

financeiro_dashboard = (
    LancamentoFinanceiro.objects.select_related("cliente", "processo", "responsavel")
    .filter(status="pendente")
    .order_by("data_vencimento")[:5]
)
```

---

## Template principal

**`templates/dashboard/painel.html`**

Estrutura:
```
cabeçalho (título + badge de plano)
├── grid 2 colunas — 6 cards clicáveis (dados reais)
└── grid 3 colunas (desktop) / 1 coluna (mobile)
    ├── Bloco: Tarefas pendentes + link Ver todas
    ├── Bloco: Agenda próxima + link Ver agenda
    └── Bloco: Financeiro pendente + link Ver financeiro
```

---

## Cards reais

| Card | Dado | Link de destino |
|---|---|---|
| Clientes ativos | `resumo.clientes_ativos` | `clientes:lista` |
| Processos ativos | `resumo.processos_ativos` | `processos:lista` |
| Tarefas pendentes | `resumo.tarefas_pendentes` | `tarefas:quadro` |
| Compromissos próximos | `resumo.compromissos_proximos` | `agenda:index` |
| A receber | `resumo.a_receber` (formatado) | `financeiro:index?filtro=receitas` |
| A pagar | `resumo.a_pagar` (formatado) | `financeiro:index?filtro=despesas` |

---

## Listas reais

### Tarefas pendentes

- `exclude(status="concluida")` — inclui `a_fazer` e `em_andamento`
- Ordenação: `order_by("prazo", "-prioridade")` — prazo mais próximo primeiro; tarefas sem prazo ao final (NULL last no PostgreSQL)
- Exibe: `titulo`, `prazo_label` (property), badge urgente se `prazo_urgente`
- Exibe: `cliente.nome_razao_social` ou `processo.titulo` como subtexto

### Agenda próxima

- `filter(status="agendado", data_hora_inicio__date__gte=hoje, data_hora_inicio__date__lte=hoje + 7 dias)`
- Ordenação: `order_by("data_hora_inicio")`
- Exibe: `titulo`, `tipo` (badge), `data_hora_inicio` formatada (`d/m/Y H:i` ou `d/m/Y — Dia inteiro`)
- Exibe: `cliente.nome_razao_social` ou `processo.titulo` como subtexto

### Financeiro pendente

- `filter(status="pendente")` — receitas e despesas juntas
- Ordenação: `order_by("data_vencimento")` — atrasados aparecem primeiro (datas passadas antes das futuras)
- Exibe: `descricao`, badge `Atrasado` (se `atrasado`) ou tipo (`Receita`/`Despesa`)
- Exibe: `R$ {{ valor|floatformat:2 }}`, `data_vencimento` formatada
- Exibe: `cliente.nome_razao_social` ou `processo.titulo` como subtexto

---

## Links e navegação

| Elemento | Destino |
|---|---|
| Card Clientes ativos | `/clientes/` |
| Card Processos ativos | `/processos/` |
| Card Tarefas pendentes | `/tarefas/` |
| Card Compromissos próximos | `/agenda/` |
| Card A receber | `/financeiro/?filtro=receitas` |
| Card A pagar | `/financeiro/?filtro=despesas` |
| "Ver todas →" (bloco Tarefas) | `/tarefas/` |
| "Ver agenda →" (bloco Agenda) | `/agenda/` |
| "Ver financeiro →" (bloco Financeiro) | `/financeiro/?filtro=pendentes` |

---

## Regras importantes

- **Sem migration:** Dashboard não tem models — nunca rodar `makemigrations` para este app
- **Agenda por data:** usar sempre `data_hora_inicio__date__gte=hoje`, nunca `__gte=agora` para evitar inconsistência entre card e lista
- **`select_related` nas listas:** obrigatório para evitar N+1 queries ao acessar `cliente`, `processo`, `responsavel` por item
- **`Sum(...) or Decimal("0"):** padrão para aggregates que retornam `None` quando não há registros
- **`timezone.localdate()`:** usar sempre em vez de `datetime.date.today()` para respeitar o fuso horário configurado

---

## Limitações conhecidas

- `plano_nome` é hardcoded (`"Mestre"`) — billing/SaaS não implementado
- Formatação de valor nas listas usa `floatformat:2` (ponto como separador decimal), não o formato brasileiro — refinamento futuro
- Sem paginação nas listas — limite de 5 itens por bloco
- Sem tratamento especial para tenants sem dados — listas mostram empty state
- Processos com prazo próximo não aparecem no Dashboard

---

## Pendências futuras

- Processos com prazo próximo — lista no Dashboard
- Links individuais nos itens das listas (tarefa → detalhe, compromisso → edição, lançamento → edição)
- Gráficos simples de receitas vs. despesas e distribuição de tarefas
- Filtros por período (semana, mês) no painel
- Indicadores por responsável (quantas tarefas/processos por usuário)
- Indicadores por cliente (processos e lançamentos por cliente)
- Indicadores por área do direito
- Alertas de tarefas vencidas, compromissos do dia, financeiro vencido
- Widgets configuráveis por usuário/perfil
- Plano real vindo de `saas_billing.Assinatura` — substituir `plano_nome` hardcoded
- Revisão visual com o sócio

---

## Próximos passos recomendados

**Fase 2.7 — Configurações/Perfil/Permissões iniciais**

Com todos os módulos operacionais básicos funcionando, o próximo passo é organizar a estrutura administrativa do escritório:

- Dados do escritório por tenant (nome, logo, endereço, contatos)
- Listagem e gestão de usuários do tenant
- Perfil do usuário (nome, cargo, avatar)
- Grupos e cargos (sócio, advogado, estagiário, administrativo)
- Permissões iniciais por grupo
- Ajustes gerais (fuso horário, formato de data)
- Base estrutural para controle de acesso em todos os módulos
