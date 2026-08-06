# Fase 2.10 — Escopo de dados nos módulos operacionais

**Status:** Em andamento — Fase 2.10A concluída em 2026-07-13  
**Contexto:** Continuação da Fase 2.9 (Equipes). Aplicar filtros de dados por usuário, equipe e papel nos módulos operacionais.

---

## Objetivo

Permitir que diferentes perfis de usuário (administrador, gerente, advogado, financeiro) vejam apenas os dados relevantes ao seu escopo de atuação — sem esconder dados indevidamente e sem quebrar registros existentes.

---

## Por que começar com diagnóstico

Aplicar filtros diretamente nos módulos operacionais sem auditoria prévia causaria **perda silenciosa de dados** para todos os usuários não-administradores:

- Registros com `responsavel=null` simplesmente desapareceriam das listagens.
- `Cliente` não tem campo `responsavel` — filtro quebraria com `FieldError`.
- Registros criados antes da Fase 2.8 podem não ter `responsavel` definido.
- Sem campo `equipe` em Tarefa, Compromisso e Financeiro, qualquer filtro por equipe nestes módulos exigiria joins frágeis e difíceis de manter.

Por isso, a Fase 2.10 iniciou com uma etapa de diagnóstico antes de qualquer implementação de filtro.

---

## Diagnóstico realizado (pré-2.10A)

### Mapa de campos por módulo

| Model | `responsavel` | `equipe` | Observação |
|---|---|---|---|
| `Cliente` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ (deliberado) | Cliente não possui equipe — decisão de produto |
| `Processo` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ✅ `ForeignKey(Equipe, SET_NULL, null=True)` | `equipe_padrao_para_usuario` aplicado na criação |
| `Tarefa` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ | Campo `equipe` ainda não existe no model |
| `Compromisso` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ | Também tem `participantes` M2M |
| `LancamentoFinanceiro` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ | Campo `equipe` ainda não existe; dado sensível |
| `CustaJudicial` | ❌ não existe | ❌ | UI ainda usa mocks |

### Como `responsavel` é atribuído na criação

| Módulo | Atribuição na criação |
|---|---|
| `Cliente` | `cliente.responsavel = request.user` — **sempre** (implementado na Fase 2.10B1) |
| `Processo` | `processo.responsavel = request.user` — **sempre** |
| `Tarefa` | `tarefa.responsavel = request.user` — **sempre** |
| `Compromisso` | `if not compromisso.responsavel:` — **condicional** (form pode enviar outro) |
| `Financeiro` | `if not lancamento.responsavel:` — **condicional** (form pode enviar outro) |

**Implicação:** Compromisso e Financeiro podem ter registros com `responsavel` diferente do criador — o form permite selecionar outro responsável.

### Riscos identificados se filtro for aplicado hoje

| Risco | Grau |
|---|---|
| Registros antigos com `responsavel=null` sumindo para usuários comuns | Alto |
| Registros antigos com `responsavel=null` sumindo para todos | Alto |
| Dashboard incoerente com módulos filtrados | Alto |
| Compromissos onde usuário é só `participante` sumindo | Médio |
| Financeiro com responsável diferente do criador | Médio |
| Múltiplas equipes causando duplicatas sem `.distinct()` | Médio |
| Join transitivo `responsavel → membros_equipe → equipe` frágil | Médio |

---

## Fase 2.10A — Diagnóstico de Escopo (concluída e removida)

A tela foi criada como ferramenta temporária de desenvolvimento para mapear riscos antes de aplicar filtros de escopo, e removida após cumprir seu papel.

**Commits históricos:**
- `ef8c5fd` — `feat(configuracoes): adicionar diagnostico de escopo` (criação)
- Commits 2.10B1A, 2.10B3A — atualizações dos contadores
- Removida após Fase 2.10B3 — os problemas identificados foram endereçados

**O que ela revelou e que foi endereçado:**
- `Cliente` sem `responsavel` → corrigido na Fase 2.10B1
- `Processo` sem `equipe` → corrigido na Fase 2.10B3 (`Processo.equipe` implementado via migration)
- `Compromisso` tem `participantes` M2M → a considerar quando escopo de Agenda for implementado
- `Dashboard` lê tudo globalmente → a ajustar por último

### Reavaliação obrigatória antes da produção

Possíveis caminhos:

- **Manter como "Saúde dos Dados"** — informar o administrador sobre consistência dos dados
- **Transformar em "Auditoria Administrativa"** — log de ações + análise de integridade
- **Transformar em "Consistência do Escritório"** — checklist de onboarding e manutenção
- **Restringir a suporte da plataforma SaaS** — ferramenta interna, fora do tenant UI
- **Remover** — se o problema for resolvido e a tela não fizer mais sentido

---

## Decisão sobre registros sem responsável

> Registros antigos sem `responsavel` **não devem ser automaticamente liberados para todos os usuários** quando filtros de escopo forem ativados.

Registros sem responsável podem existir porque:
- Foram criados antes da Fase 2.8 (quando papéis foram formalizados)
- Foram criados via shell, importação ou admin
- O usuário responsável foi removido do sistema (`SET_NULL` esvaziou o campo)

### Regra recomendada por contexto

| Contexto | Tratamento |
|---|---|
| Desenvolvimento / demo | Atribuir ao administrador ou corrigir manualmente antes de ativar filtros |
| Produção | Tratar como pendência administrativa — não liberar automaticamente |
| Administrador | Deve enxergar **todos** os registros, inclusive sem responsável |
| Gerente | Poderá ter regra própria associada à `equipe` do registro |
| Advogado | **Não deve** ganhar acesso a registros com `responsavel=null` |
| Financeiro | Regra própria a definir — dado sensível |

---

## Próximas etapas planejadas

### Fase 2.10B — Preparação dos models para escopo

**Pré-requisito:** corrigir registros com `responsavel=null` no ambiente demo.

Migrations já aplicadas:

| Migration | App | Campo | Status |
|---|---|---|---|
| `clientes.0002_cliente_responsavel` | `clientes` | `responsavel = ForeignKey(User, null=True, blank=True, SET_NULL)` | ✅ aplicada |
| `processos.0003_processo_departamento` | `processos` | criação de `Processo.equipe` (com nome antigo) | ✅ aplicada |
| `processos.0004_rename_departamento_equipe` | `processos` | renomeação `departamento` → `equipe` em `Processo` | ✅ aplicada |

Migrations planejadas (ainda não criadas):

| Migration | App | Campo |
|---|---|---|
| `tarefas.0002_...` | `tarefas` | `equipe = ForeignKey(Equipe, null=True, blank=True, SET_NULL)` |
| `agenda.0002_...` | `agenda` | `equipe = ForeignKey(Equipe, null=True, blank=True, SET_NULL)` |
| `financeiro.0002_...` | `financeiro` | `equipe = ForeignKey(Equipe, null=True, blank=True, SET_NULL)` |

Todos os campos com `null=True` — registros existentes ficam com `null` sem perda de dados.

**Nenhuma migration deve ser criada antes de aprovação explícita.**

### Fase 2.10C — Backfill/correção de dados antigos

- Usar tela de diagnóstico para identificar registros com `responsavel=null`
- Atribuir responsáveis manualmente via shell ou tela administrativa
- Confirmar que contadores da tela mostram zero para todos os módulos antes de ativar filtros

### Fase 2.10D — Escopo piloto em Processo

- Aplicar filtro de escopo apenas na view `processos.lista`
- Administrador: sem filtro
- Gerente: processos das equipes que gerencia
- Advogado: próprios processos (`responsavel=request.user`)
- `responsavel=null`: visível apenas para administrador

### Fase 2.10E — Propagar escopo gradualmente

Na ordem recomendada:

1. **Tarefas** — modelo mais simples, `responsavel` sempre definido na criação
2. **Agenda** — usar `Q(responsavel=user) | Q(participantes=user)`, obrigatório
3. **Financeiro** — definir regra própria para o papel `financeiro` antes de aplicar
4. **Dashboard** — por último, após todos os módulos estarem com escopo consistente

---

## Regras futuras por papel (referência)

| Papel | Regra de escopo |
|---|---|
| `administrador_escritorio` | Sem filtro — vê tudo do tenant |
| `gerente` | Dados cujo `equipe` pertence às equipes gerenciadas |
| `advogado` | Próprios itens + itens em que participa (Agenda: `participantes`) |
| `financeiro` | Definição pendente — provavelmente todo o financeiro do tenant |

**Observações:**
- Administrador deve sempre ver 100% — nunca aplicar filtro em admin.
- Gerente em múltiplas equipes: usar `IN` com lista de ids de equipes gerenciadas.
- Advogado em múltiplas equipes: `responsavel=user OR equipe IN minhas_equipes`.
- Dashboard sempre por último — incoerência entre cards e módulos é confusa para o usuário.
- `responsavel=null`: visível para admin e gerente; invisível para advogado e financeiro.

---

## O que NÃO foi implementado na Fase 2.10A (deliberado)

| Item | Motivo |
|---|---|
| Filtros nas views operacionais | Risco de perda silenciosa de dados |
| Campo `equipe` em Tarefa, Compromisso e Financeiro | Exige migration; depende de auditoria prévia |
| Backfill de `responsavel` em registros antigos | Dados sem responsável devem ser atribuídos manualmente antes de ativar filtros |
| Regras de escopo por papel | Depende de preparação dos models e correção de dados |
| Ajuste do Dashboard | Deve ser feito por último |
| Bloqueio de acesso por papel | Fase futura — Fase 2.10D+ |
