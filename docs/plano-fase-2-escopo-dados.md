# Fase 2.10 — Escopo de dados nos módulos operacionais

**Status:** Em andamento — Fase 2.10A concluída em 2026-07-13  
**Contexto:** Continuação da Fase 2.9 (Departamentos). Aplicar filtros de dados por usuário, departamento e papel nos módulos operacionais.

---

## Objetivo

Permitir que diferentes perfis de usuário (administrador, gerente, advogado, financeiro) vejam apenas os dados relevantes ao seu escopo de atuação — sem esconder dados indevidamente e sem quebrar registros existentes.

---

## Por que começar com diagnóstico

Aplicar filtros diretamente nos módulos operacionais sem auditoria prévia causaria **perda silenciosa de dados** para todos os usuários não-administradores:

- Registros com `responsavel=null` simplesmente desapareceriam das listagens.
- `Cliente` não tem campo `responsavel` — filtro quebraria com `FieldError`.
- Registros criados antes da Fase 2.8 podem não ter `responsavel` definido.
- Sem campo `departamento` nos models operacionais, qualquer filtro por departamento exigiria joins frágeis e difíceis de manter.

Por isso, a Fase 2.10 iniciou com uma etapa de diagnóstico antes de qualquer implementação de filtro.

---

## Diagnóstico realizado (pré-2.10A)

### Mapa de campos por módulo

| Model | `responsavel` | `departamento` | Observação |
|---|---|---|---|
| `Cliente` | ❌ não existe | ❌ | Maior gap — impossível filtrar por usuário sem migration |
| `Processo` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ | Melhor candidato para piloto |
| `Tarefa` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ | Responsável preservado na edição |
| `Compromisso` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ | Também tem `participantes` M2M |
| `LancamentoFinanceiro` | ✅ `ForeignKey(User, SET_NULL, null=True)` | ❌ | Dado sensível |
| `CustaJudicial` | ❌ não existe | ❌ | UI ainda usa mocks |

### Como `responsavel` é atribuído na criação

| Módulo | Atribuição na criação |
|---|---|
| `Cliente` | **impossível** — campo não existe |
| `Processo` | `processo.responsavel = request.user` — **sempre** |
| `Tarefa` | `tarefa.responsavel = request.user` — **sempre** |
| `Compromisso` | `if not compromisso.responsavel:` — **condicional** (form pode enviar outro) |
| `Financeiro` | `if not lancamento.responsavel:` — **condicional** (form pode enviar outro) |

**Implicação:** Compromisso e Financeiro podem ter registros com `responsavel` diferente do criador — o form permite selecionar outro responsável.

### Riscos identificados se filtro for aplicado hoje

| Risco | Grau |
|---|---|
| `Cliente` sem `responsavel` — filtro quebraria a query | Alto |
| Registros antigos com `responsavel=null` sumindo para todos | Alto |
| Dashboard incoerente com módulos filtrados | Alto |
| Compromissos onde usuário é só `participante` sumindo | Médio |
| Financeiro com responsável diferente do criador | Médio |
| Múltiplos departamentos causando duplicatas sem `.distinct()` | Médio |
| Join transitivo `responsavel → membros_departamento → departamento` frágil | Médio |

---

## Fase 2.10A — Diagnóstico de Escopo (concluída)

### O que foi implementado

| Item | Detalhe |
|---|---|
| View | `configuracoes.views.diagnostico_escopo` |
| Rota | `/configuracoes/diagnostico-escopo/` |
| Proteção | `@requer_admin_escritorio` — advogado recebe 403 |
| Link | Card "Administração" em `/configuracoes/` — visível apenas para admin |
| Template | `templates/configuracoes/diagnostico_escopo.html` |

### O que a tela exibe

**Clientes:**
- Total de clientes ativos
- Aviso: campo `responsavel` não existe — badge "Risco alto"

**Processos, Tarefas, Compromissos, Financeiro:**
- Total de registros
- Contagem de registros com `responsavel=null`
- Badge "OK" (verde) se zero sem responsável; badge "Atenção" (âmbar) se houver

**Avisos específicos:**
- Agenda: `Compromisso` tem `participantes` M2M — escopo não pode considerar só `responsavel`
- Financeiro: dado sensível; exige regra própria de acesso

### O que a tela NÃO faz

- Não altera, filtra nem bloqueia qualquer dado
- Não altera models
- Não cria migrations
- Não altera módulos operacionais
- Não aplica regras de escopo

### Arquivos alterados

| Arquivo | Operação |
|---|---|
| `apps/configuracoes/views.py` | Imports dos models operacionais + view `diagnostico_escopo` |
| `apps/configuracoes/urls.py` | Rota `configuracoes/diagnostico-escopo/` |
| `templates/configuracoes/index.html` | Card "Administração" com links Departamentos e Diagnóstico |
| `templates/configuracoes/diagnostico_escopo.html` | Template criado |

### Commit

`ef8c5fd` — `feat(configuracoes): adicionar diagnostico de escopo`

---

## Decisão de produto/arquitetura sobre a tela de diagnóstico

> A tela de Diagnóstico de Escopo deve ser tratada, **por enquanto**, como ferramenta administrativa/técnica de apoio ao desenvolvimento.

### Para que serve

- Auxiliar o desenvolvimento incremental de escopo de dados
- Mostrar riscos antes de ativar filtros por usuário, departamento ou papel
- Evitar que dados sumam silenciosamente durante a evolução do sistema
- Identificar registros antigos sem responsável antes de aplicar filtros
- Apoiar decisões de arquitetura com dados reais do banco
- Validar se o sistema está pronto para receber regras reais de escopo

### O que ela NÃO é ainda

- Não é uma funcionalidade principal do produto
- Não é uma tela de auditoria de produção
- Não é um painel de saúde permanente
- Não é obrigatória para o funcionamento do sistema

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
| Gerente | Poderá ter regra própria associada ao `departamento` do registro |
| Advogado | **Não deve** ganhar acesso a registros com `responsavel=null` |
| Financeiro | Regra própria a definir — dado sensível |

---

## Próximas etapas planejadas

### Fase 2.10B — Preparação dos models para escopo

**Pré-requisito:** corrigir registros com `responsavel=null` no ambiente demo.

Migrations planejadas (ainda não criadas):

| Migration | App | Campo |
|---|---|---|
| `clientes.0002_...` | `clientes` | `responsavel = ForeignKey(User, null=True, blank=True, SET_NULL)` |
| `clientes.0003_...` | `clientes` | `departamento = ForeignKey(Departamento, null=True, blank=True, SET_NULL)` |
| `processos.0002_...` | `processos` | `departamento = ForeignKey(Departamento, null=True, blank=True, SET_NULL)` |

Todos os campos com `null=True` — registros existentes ficam com `null` sem perda de dados.

**Nenhuma migration deve ser criada antes de aprovação explícita.**

### Fase 2.10C — Backfill/correção de dados antigos

- Usar tela de diagnóstico para identificar registros com `responsavel=null`
- Atribuir responsáveis manualmente via shell ou tela administrativa
- Confirmar que contadores da tela mostram zero para todos os módulos antes de ativar filtros

### Fase 2.10D — Escopo piloto em Processo

- Aplicar filtro de escopo apenas na view `processos.lista`
- Administrador: sem filtro
- Gerente: processos dos departamentos que gerencia
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
| `gerente` | Dados cujo responsável pertence aos departamentos gerenciados |
| `advogado` | Próprios itens + itens em que participa (Agenda: `participantes`) |
| `financeiro` | Definição pendente — provavelmente todo o financeiro do tenant |

**Observações:**
- Administrador deve sempre ver 100% — nunca aplicar filtro em admin.
- Gerente em múltiplos departamentos: usar `IN` com lista de ids gerenciados.
- Advogado em múltiplos departamentos: `responsavel=user OR departamento IN meus_departamentos`.
- Dashboard sempre por último — incoerência entre cards e módulos é confusa para o usuário.
- `responsavel=null`: visível para admin e gerente; invisível para advogado e financeiro.

---

## O que NÃO foi implementado na Fase 2.10A (deliberado)

| Item | Motivo |
|---|---|
| Filtros nas views operacionais | Risco de perda silenciosa de dados |
| Campo `departamento` nos models operacionais | Exige migration; depende de auditoria prévia |
| Campo `responsavel` em `Cliente` | Exige migration; depende de decisão sobre backfill |
| Regras de escopo por papel | Depende de preparação dos models e correção de dados |
| Ajuste do Dashboard | Deve ser feito por último |
| Bloqueio de acesso por papel | Fase futura — Fase 2.10D+ |
