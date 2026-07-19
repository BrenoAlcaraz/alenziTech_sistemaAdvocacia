# Fase 2.9 — Equipes e estrutura organizacional

**Status:** Concluída em nível básico (2026-07-13); refatoração Departamento → Equipe concluída em 2026-07-18  
**Contexto:** Continuação da Fase 2.8 (Permissões iniciais). Organiza usuários em equipes e cria infraestrutura de escopo para fases futuras.

> **Nota histórica:** Este documento foi originalmente planejado como "Departamentos". O conceito foi renomeado para "Equipes" por decisão de produto em 2026-07-18 via refatoração de banco e código (`accounts.0004_rename_departamento_equipe` + `processos.0004_rename_departamento_equipe`). Todas as referências abaixo já usam a nomenclatura atual.

---

## Objetivo

Permitir que o Administrador do Escritório organize usuários em equipes, defina gerentes de equipe e prepare a infraestrutura de escopo de dados. O escopo real (filtros nos módulos operacionais) fica para fase futura.

---

## Funcionalidades entregues

### 2.9B — Models e migration

**Arquivo:** `apps/accounts/models.py`

Adicionados dois novos models ao app `accounts` (tenant-scoped via `TENANT_APPS`):

#### `Equipe`

| Campo | Tipo | Observação |
|---|---|---|
| `nome` | `CharField(100)` | Obrigatório |
| `descricao` | `TextField` | Opcional |
| `equipe_pai` | `ForeignKey("self", SET_NULL, null=True)` | Hierarquia; circular bloqueado no form |
| `ativo` | `BooleanField(default=True)` | Soft disable |
| `criado_em` | `DateTimeField(auto_now_add=True)` | |
| `atualizado_em` | `DateTimeField(auto_now=True)` | |

Meta: `verbose_name="Equipe"`, `ordering=["nome"]`

#### `MembroEquipe`

| Campo | Tipo | Observação |
|---|---|---|
| `usuario` | `ForeignKey(settings.AUTH_USER_MODEL, CASCADE)` | Usa `AUTH_USER_MODEL` — não importa `User` diretamente |
| `equipe` | `ForeignKey(Equipe, CASCADE)` | |
| `eh_gerente` | `BooleanField(default=False)` | Papel dentro da equipe; não substitui `auth.Group` |
| `ativo` | `BooleanField(default=True)` | Permite desativar vínculo sem excluir |
| `criado_em` | `DateTimeField(auto_now_add=True)` | |

Constraint: `UniqueConstraint(fields=["usuario", "equipe"], name="uniq_usuario_equipe")`

**Migrations:**
- `accounts.0003_departamento_membrodepartamento` — criação inicial (com nome antigo)
- `accounts.0004_rename_departamento_equipe` — renomeação segura via `RenameModel`, `RenameField`, `AlterField`, `RemoveConstraint`, `AddConstraint`

Dependência da 0003: `('accounts', '0002_criar_grupos_padroes')` + `swappable_dependency(settings.AUTH_USER_MODEL)`  
Aplicada com `python manage.py migrate_schemas` (sem `--shared`, pois `accounts` é TENANT_APP).

### 2.9B — Admin

**Arquivo:** `apps/accounts/admin.py`

```python
@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ["nome", "equipe_pai", "ativo", "criado_em", "atualizado_em"]
    list_filter = ["ativo", "equipe_pai"]
    search_fields = ["nome", "descricao"]
    readonly_fields = ["criado_em", "atualizado_em"]

@admin.register(MembroEquipe)
class MembroEquipeAdmin(admin.ModelAdmin):
    list_display = ["usuario", "equipe", "eh_gerente", "ativo", "criado_em"]
    list_filter = ["eh_gerente", "ativo", "equipe"]
    search_fields = ["usuario__username", "usuario__email", "equipe__nome"]
    readonly_fields = ["criado_em"]
```

### 2.9C — Listagem de equipes

**Rota:** `GET /configuracoes/equipes/`  
**View:** `configuracoes.views.equipes`  
**Template:** `templates/configuracoes/equipes.html`  
**Proteção:** `@requer_admin_escritorio`

Exibe tabela com: nome, descrição, equipe pai, total de membros, total de gerentes, status (ativo/inativo), ações (Membros | Editar).

Contagem de membros e gerentes: calculada em Python via prefetch (sem query extra no template).

Empty state quando não há equipes.

Link "Gerenciar equipes" adicionado em `/configuracoes/` — visível apenas para admins (`{% if usuario_e_admin_escritorio %}`).

### 2.9D — Criação e edição de equipes

**Rotas:**
- `GET/POST /configuracoes/equipes/novo/`
- `GET/POST /configuracoes/equipes/<int:pk>/editar/`

**Views:** `nova_equipe`, `editar_equipe`  
**Template compartilhado:** `templates/configuracoes/equipe_form.html`  
**Form:** `EquipeForm` em `apps/accounts/forms.py`  
**Proteção:** `@requer_admin_escritorio`

**`EquipeForm`:**
- Campos: `nome`, `descricao`, `equipe_pai`, `ativo`
- `__init__`: limita `equipe_pai` a equipes ativas; exclui a própria na edição
- `clean_equipe_pai`: bloqueia equipe como pai de si mesma; bloqueia ciclo via loop `while atual`

### 2.9E — Gestão de membros de equipes

**Rotas:**
- `GET/POST /configuracoes/equipes/<int:pk>/membros/`
- `POST /configuracoes/equipes/<int:pk>/membros/<int:membro_pk>/remover/`
- `POST /configuracoes/equipes/<int:pk>/membros/<int:membro_pk>/alternar-gerente/`

**Views:** `equipe_membros`, `remover_membro_equipe`, `alternar_gerente_equipe`  
**Template:** `templates/configuracoes/equipe_membros.html`  
**Form:** `MembroEquipeForm` em `apps/accounts/forms.py`  
**Proteção:** `@requer_admin_escritorio` em todas as três views

**`MembroEquipeForm`:**
- Campos: `usuario`, `eh_gerente`
- Equipe não é campo do form — vem pela URL
- `__init__(equipe=None)`: exclui usuários já vinculados à equipe
- Se não houver usuários disponíveis, aviso discreto substituiu o form

**Regras de negócio:**
- Vínculo salvo com `ativo=True` sempre
- Alternância de gerente usa `save(update_fields=["eh_gerente"])`
- Remoção é `membro.delete()` (hard delete do vínculo, não do usuário)
- `eh_gerente` é papel organizacional — não substitui `auth.Group`
- Constraint `uniq_usuario_equipe` garante unicidade no banco

### 2.9F — Exibição de equipes na lista de usuários

**Arquivo:** `apps/configuracoes/views.py` (view `index`)  
**Template:** `templates/configuracoes/index.html`

A view `index` agora inclui `prefetch_related("membros_equipe", "membros_equipe__equipe")` e monta `membros_equipe` por usuário — filtrando apenas vínculos ativos com equipes ativas.

No template, cada usuário exibe:
```
Equipes: Cível, Família (gerente)
```
ou:
```
Equipes: Nenhuma equipe vinculada
```

Papel real continua vindo de `auth.Group`. Cargo continua apenas descritivo.

### 2.9G — Helpers de escopo

**Arquivo:** `apps/accounts/escopo.py`

```
Estes helpers ainda não aplicam filtros nos módulos operacionais.
Eles apenas expõem consultas de equipes para uso futuro.
```

#### Constantes

```python
ESCOPO_TUDO = "tudo"
ESCOPO_EQUIPES_GERENCIADAS = "equipes_gerenciadas"
ESCOPO_EQUIPE = "equipe"
ESCOPO_PROPRIOS_ITENS = "proprios_itens"
ESCOPO_NENHUM = "nenhum"

ESCOPOS_DADOS = [...]
```

#### Funções

| Função | Retorna |
|---|---|
| `equipes_do_usuario(user, somente_ativos=True)` | `QuerySet[Equipe]` |
| `equipes_gerenciadas_pelo_usuario(user, somente_ativos=True)` | `QuerySet[Equipe]` |
| `usuario_gerencia_equipe(user, equipe)` | `bool` — considera equipe ativa |
| `ids_equipes_do_usuario(user, somente_ativos=True)` | `list[int]` |
| `ids_equipes_gerenciadas_pelo_usuario(user, somente_ativos=True)` | `list[int]` |
| `equipes_descendentes(equipe, incluir_proprio=False, somente_ativos=True)` | `list[Equipe]` — recursivo; retorna `[]` se raiz inativa e `somente_ativos=True` |
| `equipe_padrao_para_usuario(user)` | `Equipe \| None` — `None` para admin/superuser, 0 ou 2+ equipes |

---

## Rotas criadas

| Rota | View | Proteção |
|---|---|---|
| `GET /configuracoes/equipes/` | `equipes` | `@requer_admin_escritorio` |
| `GET/POST /configuracoes/equipes/novo/` | `nova_equipe` | `@requer_admin_escritorio` |
| `GET/POST /configuracoes/equipes/<pk>/editar/` | `editar_equipe` | `@requer_admin_escritorio` |
| `GET/POST /configuracoes/equipes/<pk>/membros/` | `equipe_membros` | `@requer_admin_escritorio` |
| `POST /configuracoes/equipes/<pk>/membros/<membro_pk>/remover/` | `remover_membro_equipe` | `@requer_admin_escritorio` |
| `POST /configuracoes/equipes/<pk>/membros/<membro_pk>/alternar-gerente/` | `alternar_gerente_equipe` | `@requer_admin_escritorio` |

---

## Arquivos criados/modificados

| Arquivo | Operação |
|---|---|
| `apps/accounts/models.py` | Adicionados `Equipe` e `MembroEquipe` |
| `apps/accounts/admin.py` | Adicionados `EquipeAdmin` e `MembroEquipeAdmin` |
| `apps/accounts/migrations/0003_departamento_membrodepartamento.py` | Criado e aplicado (nome histórico) |
| `apps/accounts/migrations/0004_rename_departamento_equipe.py` | Renomeação segura — criado e aplicado |
| `apps/processos/migrations/0004_rename_departamento_equipe.py` | Renomeação de `Processo.departamento` → `Processo.equipe` |
| `apps/accounts/forms.py` | Adicionados `EquipeForm` e `MembroEquipeForm` |
| `apps/accounts/escopo.py` | Criado — helpers de escopo |
| `apps/configuracoes/views.py` | Adicionadas 6 novas views; `index` atualizado com prefetch |
| `apps/configuracoes/urls.py` | Adicionadas 6 novas rotas |
| `templates/configuracoes/equipes.html` | Criado |
| `templates/configuracoes/equipe_form.html` | Criado |
| `templates/configuracoes/equipe_membros.html` | Criado |
| `templates/configuracoes/index.html` | Adicionado card de equipes e exibição na lista de usuários |

---

## Decisões técnicas

- **Models em `apps.accounts`**, não em app separado — equipes são dados de usuário, não operacionais.
- **Telas em `apps.configuracoes`** — gestão de equipes é administração do escritório.
- **Não foi criado app novo** — evita overhead de configuração.
- **`settings.AUTH_USER_MODEL` no FK** — evita importar `User` diretamente em models.
- **`UniqueConstraint`** preferido sobre `unique_together` (Django 5.2+).
- **Apenas Administrador do Escritório gerencia** equipes nesta versão — gerente ainda não.
- **`eh_gerente` não substitui `auth.Group`** — é papel organizacional dentro da equipe.
- **Contagem de membros/gerentes em Python** via prefetch — evita N+1 queries.
- **Ações de membro via POST** — nunca GET para alterar dados.
- **Escopo real não aplicado** — deliberado; risco de esconder dados exige diagnóstico separado.
- **`Cliente` não possui equipe** — equipe pertence ao `Processo`; um cliente pode ter processos em equipes diferentes.
- **Renomeação via `RenameModel`/`RenameField`** — preserva dados; não usa delete+create.

---

## Riscos e atenções para fases futuras

- **`responsavel` pode ser `null`** em Processos, Tarefas, Compromissos e Financeiro — dados sem responsável precisam de regra explícita (mostrar para todos? esconder? mostrar só para admin?).
- **Registros criados antes das equipes** não têm vínculo — garantir que admin veja tudo sempre.
- **Equipes múltiplas** — usuário pode estar em mais de uma equipe; queries de escopo devem usar `IN` ou `ANY`.
- **Hierarquia de equipes** — escopo de gerente pode precisar incluir subequipes.

---

## Testes realizados

| Teste | Resultado |
|---|---|
| Admin acessa `/configuracoes/equipes/` | ✅ |
| Advogado recebe 403 em equipes | ✅ |
| Admin cria equipe sem pai | ✅ |
| Admin cria subequipe | ✅ |
| Admin edita equipe | ✅ |
| Ciclo hierárquico é bloqueado | ✅ |
| Admin adiciona membro à equipe | ✅ |
| Admin marca usuário como gerente | ✅ |
| Admin alterna gerente | ✅ |
| Admin remove membro | ✅ |
| Usuário já vinculado não reaparece no select | ✅ |
| Usuário com equipe aparece em `/configuracoes/` | ✅ |
| Gerente aparece com indicação `(gerente)` | ✅ |
| Usuário sem equipe mostra "Nenhuma equipe vinculada" | ✅ |
| Helpers retornam equipes/gerência corretamente (tenant demo) | ✅ |
| Dados preservados após refatoração Departamento → Equipe | ✅ |
| `python manage.py check` — 0 issues | ✅ |

---

## Escopo deliberadamente NÃO implementado

| Item | Motivo |
|---|---|
| Filtro por equipe em Clientes | Cliente não possui equipe — decisão de produto |
| Filtro por equipe em Processos | Risco de esconder dados existentes |
| Filtro por equipe em Tarefas | Idem |
| Filtro por equipe em Agenda | Idem |
| Filtro por equipe em Financeiro | Idem |
| Filtro por equipe no Dashboard | Depende dos outros módulos |
| Escopo real nas views | Fase futura dedicada |
| Gerente gerenciando equipes | Apenas admin nesta versão |
| Campo `equipe` em Tarefa, Compromisso e Financeiro | Fase futura; exige migration |
| Herança automática por processo | Fase futura |
| Drag and drop na árvore | Fora do escopo atual |

---

## Próximos passos recomendados

### Fase 2.10 — Opção A: Escopo de dados nos módulos operacionais

Pré-requisito: diagnóstico completo antes de implementar.

1. Definir regra para dados sem responsável (`null`)
2. Aplicar `equipes_do_usuario(user)` nas queries de listagem de processos
3. Decidir se escopo é por `responsavel` ou por `equipe` nos demais módulos
4. Garantir que `is_superuser` e `is_admin_escritorio` continuem vendo tudo
5. Testar com dados reais no tenant demo

### Fase 2.10 — Opção B: Segurança de usuários e onboarding

- Redefinição de senha pela interface
- Desativação/reativação de usuários
- Edição do papel de usuário existente
- Convite por e-mail
- Auditoria de ações administrativas
