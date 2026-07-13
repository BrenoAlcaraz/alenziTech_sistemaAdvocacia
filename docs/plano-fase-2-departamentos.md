# Fase 2.9 — Departamentos e escopo de dados

**Status:** Concluída em nível básico (2026-07-13)  
**Contexto:** Continuação da Fase 2.8 (Permissões iniciais). Organiza usuários em departamentos e cria infraestrutura de escopo para fases futuras.

---

## Objetivo

Permitir que o Administrador do Escritório organize usuários em departamentos, defina gerentes de departamento e prepare a infraestrutura de escopo de dados. O escopo real (filtros nos módulos operacionais) fica para fase futura.

---

## Funcionalidades entregues

### 2.9B — Models e migration

**Arquivo:** `apps/accounts/models.py`

Adicionados dois novos models ao app `accounts` (tenant-scoped via `TENANT_APPS`):

#### `Departamento`

| Campo | Tipo | Observação |
|---|---|---|
| `nome` | `CharField(100)` | Obrigatório |
| `descricao` | `TextField` | Opcional |
| `departamento_pai` | `ForeignKey("self", SET_NULL, null=True)` | Hierarquia; circular bloqueado no form |
| `ativo` | `BooleanField(default=True)` | Soft disable |
| `criado_em` | `DateTimeField(auto_now_add=True)` | |
| `atualizado_em` | `DateTimeField(auto_now=True)` | |

Meta: `verbose_name="Departamento"`, `ordering=["nome"]`

#### `MembroDepartamento`

| Campo | Tipo | Observação |
|---|---|---|
| `usuario` | `ForeignKey(settings.AUTH_USER_MODEL, CASCADE)` | Usa `AUTH_USER_MODEL` — não importa `User` diretamente |
| `departamento` | `ForeignKey(Departamento, CASCADE)` | |
| `eh_gerente` | `BooleanField(default=False)` | Papel dentro do departamento; não substitui `auth.Group` |
| `ativo` | `BooleanField(default=True)` | Permite desativar vínculo sem excluir |
| `criado_em` | `DateTimeField(auto_now_add=True)` | |

Constraint: `UniqueConstraint(fields=["usuario", "departamento"], name="uniq_usuario_departamento")`

**Migration:** `accounts.0003_departamento_membrodepartamento`  
Dependência: `('accounts', '0002_criar_grupos_padroes')` + `swappable_dependency(settings.AUTH_USER_MODEL)`  
Aplicada com `python manage.py migrate_schemas` (sem `--shared`, pois `accounts` é TENANT_APP).

### 2.9B — Admin

**Arquivo:** `apps/accounts/admin.py`

```python
@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ["nome", "departamento_pai", "ativo", "criado_em", "atualizado_em"]
    list_filter = ["ativo", "departamento_pai"]
    search_fields = ["nome", "descricao"]
    readonly_fields = ["criado_em", "atualizado_em"]

@admin.register(MembroDepartamento)
class MembroDepartamentoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "departamento", "eh_gerente", "ativo", "criado_em"]
    list_filter = ["eh_gerente", "ativo", "departamento"]
    search_fields = ["usuario__username", "usuario__email", "departamento__nome"]
    readonly_fields = ["criado_em"]
```

### 2.9C — Listagem de departamentos

**Rota:** `GET /configuracoes/departamentos/`  
**View:** `configuracoes.views.departamentos`  
**Template:** `templates/configuracoes/departamentos.html`  
**Proteção:** `@requer_admin_escritorio`

Exibe tabela com: nome, descrição, departamento pai, total de membros, total de gerentes, status (ativo/inativo), ações (Membros | Editar).

Contagem de membros e gerentes: calculada em Python via prefetch (sem query extra no template).

Empty state quando não há departamentos.

Link "Gerenciar departamentos" adicionado em `/configuracoes/` — visível apenas para admins (`{% if usuario_e_admin_escritorio %}`).

### 2.9D — Criação e edição de departamentos

**Rotas:**
- `GET/POST /configuracoes/departamentos/novo/`
- `GET/POST /configuracoes/departamentos/<int:pk>/editar/`

**Views:** `novo_departamento`, `editar_departamento`  
**Template compartilhado:** `templates/configuracoes/departamento_form.html`  
**Form:** `DepartamentoForm` em `apps/accounts/forms.py`  
**Proteção:** `@requer_admin_escritorio`

**`DepartamentoForm`:**
- Campos: `nome`, `descricao`, `departamento_pai`, `ativo`
- `__init__`: limita `departamento_pai` a departamentos ativos; exclui o próprio na edição
- `clean_departamento_pai`: bloqueia departamento como pai de si mesmo; bloqueia ciclo via loop `while atual`

### 2.9E — Gestão de membros de departamentos

**Rotas:**
- `GET/POST /configuracoes/departamentos/<int:pk>/membros/`
- `POST /configuracoes/departamentos/<int:pk>/membros/<int:membro_pk>/remover/`
- `POST /configuracoes/departamentos/<int:pk>/membros/<int:membro_pk>/alternar-gerente/`

**Views:** `departamento_membros`, `remover_membro_departamento`, `alternar_gerente_departamento`  
**Template:** `templates/configuracoes/departamento_membros.html`  
**Form:** `MembroDepartamentoForm` em `apps/accounts/forms.py`  
**Proteção:** `@requer_admin_escritorio` em todas as três views

**`MembroDepartamentoForm`:**
- Campos: `usuario`, `eh_gerente`
- Departamento não é campo do form — vem pela URL
- `__init__(departamento=None)`: exclui usuários já vinculados ao departamento
- Se não houver usuários disponíveis, aviso discreto substituiu o form

**Regras de negócio:**
- Vínculo salvo com `ativo=True` sempre
- Alternância de gerente usa `save(update_fields=["eh_gerente"])`
- Remoção é `membro.delete()` (hard delete do vínculo, não do usuário)
- `eh_gerente` é papel organizacional — não substitui `auth.Group`
- Constraint `uniq_usuario_departamento` garante unicidade no banco

### 2.9F — Exibição de departamentos na lista de usuários

**Arquivo:** `apps/configuracoes/views.py` (view `index`)  
**Template:** `templates/configuracoes/index.html`

A view `index` agora inclui `prefetch_related("membros_departamento", "membros_departamento__departamento")` e monta `membros_departamento` por usuário — filtrando apenas vínculos ativos com departamentos ativos.

No template, cada usuário exibe:
```
Departamentos: Cível, Família (gerente)
```
ou:
```
Departamentos: Nenhum departamento vinculado
```

Papel real continua vindo de `auth.Group`. Cargo continua apenas descritivo.

### 2.9G — Helpers de escopo

**Arquivo:** `apps/accounts/escopo.py`

```
Estes helpers ainda não aplicam filtros nos módulos operacionais.
Eles apenas expõem consultas de departamentos para uso futuro.
```

#### Constantes

```python
ESCOPO_TUDO = "tudo"
ESCOPO_DEPARTAMENTOS_GERENCIADOS = "departamentos_gerenciados"
ESCOPO_DEPARTAMENTO = "departamento"
ESCOPO_PROPRIOS_ITENS = "proprios_itens"
ESCOPO_NENHUM = "nenhum"

ESCOPOS_DADOS = [...]
```

#### Funções

| Função | Retorna |
|---|---|
| `departamentos_do_usuario(user, somente_ativos=True)` | `QuerySet[Departamento]` |
| `departamentos_gerenciados_pelo_usuario(user, somente_ativos=True)` | `QuerySet[Departamento]` |
| `usuario_gerencia_departamento(user, departamento)` | `bool` — considera departamento ativo |
| `ids_departamentos_do_usuario(user, somente_ativos=True)` | `list[int]` |
| `ids_departamentos_gerenciados_pelo_usuario(user, somente_ativos=True)` | `list[int]` |
| `departamentos_descendentes(departamento, incluir_proprio=False, somente_ativos=True)` | `list[Departamento]` — recursivo; retorna `[]` se raiz inativa e `somente_ativos=True` |

---

## Rotas criadas

| Rota | View | Proteção |
|---|---|---|
| `GET /configuracoes/departamentos/` | `departamentos` | `@requer_admin_escritorio` |
| `GET/POST /configuracoes/departamentos/novo/` | `novo_departamento` | `@requer_admin_escritorio` |
| `GET/POST /configuracoes/departamentos/<pk>/editar/` | `editar_departamento` | `@requer_admin_escritorio` |
| `GET/POST /configuracoes/departamentos/<pk>/membros/` | `departamento_membros` | `@requer_admin_escritorio` |
| `POST /configuracoes/departamentos/<pk>/membros/<membro_pk>/remover/` | `remover_membro_departamento` | `@requer_admin_escritorio` |
| `POST /configuracoes/departamentos/<pk>/membros/<membro_pk>/alternar-gerente/` | `alternar_gerente_departamento` | `@requer_admin_escritorio` |

---

## Arquivos criados/modificados

| Arquivo | Operação |
|---|---|
| `apps/accounts/models.py` | Adicionados `Departamento` e `MembroDepartamento` |
| `apps/accounts/admin.py` | Adicionados `DepartamentoAdmin` e `MembroDepartamentoAdmin` |
| `apps/accounts/migrations/0003_departamento_membrodepartamento.py` | Criado e aplicado |
| `apps/accounts/forms.py` | Adicionados `DepartamentoForm` e `MembroDepartamentoForm` |
| `apps/accounts/escopo.py` | Criado — helpers de escopo |
| `apps/configuracoes/views.py` | Adicionadas 5 novas views; `index` atualizado com prefetch |
| `apps/configuracoes/urls.py` | Adicionadas 5 novas rotas |
| `templates/configuracoes/departamentos.html` | Criado |
| `templates/configuracoes/departamento_form.html` | Criado |
| `templates/configuracoes/departamento_membros.html` | Criado |
| `templates/configuracoes/index.html` | Adicionado card de departamentos e exibição na lista de usuários |

---

## Decisões técnicas

- **Models em `apps.accounts`**, não em app separado — departamentos são dados de usuário, não operacionais.
- **Telas em `apps.configuracoes`** — gestão de departamentos é administração do escritório.
- **Não foi criado app novo** — evita overhead de configuração.
- **`settings.AUTH_USER_MODEL` no FK** — evita importar `User` diretamente em models.
- **`UniqueConstraint`** preferido sobre `unique_together` (Django 5.2+).
- **Apenas Administrador do Escritório gerencia** departamentos nesta versão — gerente ainda não.
- **`eh_gerente` não substitui `auth.Group`** — é papel organizacional dentro do departamento.
- **Contagem de membros/gerentes em Python** via prefetch — evita N+1 queries.
- **Ações de membro via POST** — nunca GET para alterar dados.
- **Escopo real não aplicado** — deliberado; risco de esconder dados exige diagnóstico separado.

---

## Riscos e atenções para fases futuras

- **`Cliente` não tem `responsavel`** — campo FK ainda não existe no model. Escopo por usuário em clientes exige migration adicional.
- **`responsavel` pode ser `null`** em Processos, Tarefas, Compromissos e Financeiro — dados sem responsável precisam de regra explícita (mostrar para todos? esconder? mostrar só para admin?).
- **Registros criados antes dos departamentos** não têm vínculo — garantir que admin veja tudo sempre.
- **Departamentos múltiplos** — usuário pode estar em mais de um departamento; queries de escopo devem usar `IN` ou `ANY`.
- **Hierarquia de departamentos** — escopo de gerente pode precisar incluir subdepartamentos.

---

## Testes realizados

| Teste | Resultado |
|---|---|
| Admin acessa `/configuracoes/departamentos/` | ✅ |
| Advogado recebe 403 em departamentos | ✅ |
| Admin cria departamento sem pai | ✅ |
| Admin cria subdepartamento | ✅ |
| Admin edita departamento | ✅ |
| Ciclo hierárquico é bloqueado | ✅ |
| Admin adiciona membro ao departamento | ✅ |
| Admin marca usuário como gerente | ✅ |
| Admin alterna gerente | ✅ |
| Admin remove membro | ✅ |
| Usuário já vinculado não reaparece no select | ✅ |
| Usuário com departamento aparece em `/configuracoes/` | ✅ |
| Gerente aparece com indicação `(gerente)` | ✅ |
| Usuário sem departamento mostra "Nenhum departamento vinculado" | ✅ |
| Helpers retornam departamentos/gerência corretamente (tenant demo) | ✅ |
| `python manage.py check` — 0 issues | ✅ |

---

## Escopo deliberadamente NÃO implementado

| Item | Motivo |
|---|---|
| Filtro por departamento em Clientes | `Cliente` não tem `responsavel`; exige diagnóstico |
| Filtro por departamento em Processos | Risco de esconder dados existentes |
| Filtro por departamento em Tarefas | Idem |
| Filtro por departamento em Agenda | Idem |
| Filtro por departamento em Financeiro | Idem |
| Filtro por departamento no Dashboard | Depende dos outros módulos |
| Escopo real nas views | Fase futura dedicada |
| Gerente gerenciando departamentos | Apenas admin nesta versão |
| Campo `departamento` em modelos operacionais | Fase futura; exige migration |
| Herança automática por cliente/processo | Fase futura |
| Drag and drop na árvore | Fora do escopo atual |

---

## Próximos passos recomendados

### Fase 2.10 — Opção A: Escopo de dados nos módulos operacionais

Pré-requisito: diagnóstico completo antes de implementar.

1. Definir regra para dados sem responsável (`null`)
2. Adicionar `responsavel` ao model `Cliente` (migration necessária)
3. Decidir se escopo é por `responsavel` ou por `departamento` nos módulos
4. Aplicar `departamentos_do_usuario(user)` nas queries de listagem
5. Garantir que `is_superuser` e `is_admin_escritorio` continuem vendo tudo
6. Testar com dados reais no tenant demo

### Fase 2.10 — Opção B: Segurança de usuários e onboarding

- Redefinição de senha pela interface
- Desativação/reativação de usuários
- Edição do papel de usuário existente
- Convite por e-mail
- Auditoria de ações administrativas
