# Plano Fase 2.8 — Usuários, papéis e permissões iniciais

**Status**: concluído em nível básico  
**Data de conclusão**: 2026-07-10

---

## Objetivo do módulo

Criar a base de controle de acesso por papel dentro de cada tenant: grupos Django representando papéis reais, decorator reutilizável para proteger views administrativas, e fluxo de criação de usuários pelo Administrador do Escritório.

---

## Funcionalidades entregues

| Funcionalidade | Status |
|---|---|
| Migration de grupos padrão (`accounts.0002_criar_grupos_padroes`) | ✅ |
| Arquivo `apps/accounts/decorators.py` com helpers e constantes | ✅ |
| Helper `usuario_admin_escritorio` com três caminhos de verificação | ✅ |
| Decorator `requer_admin_escritorio` | ✅ |
| Administrador inicial do tenant `demo` formalizado | ✅ |
| View `/configuracoes/usuarios/novo/` protegida por `requer_admin_escritorio` | ✅ |
| Form `CriarUsuarioEscritorioForm` com papéis `gerente`, `advogado`, `financeiro` | ✅ |
| Template `templates/configuracoes/novo_usuario.html` | ✅ |
| Exibição de papel real (auth.Group) na lista de usuários | ✅ |
| Botão "Novo usuário" oculto para não-admins | ✅ |
| Botão "Editar dados do escritório" oculto para não-admins | ✅ |
| Proteção backend de `/configuracoes/escritorio/` por `requer_admin_escritorio` | ✅ |
| `/configuracoes/` mantido acessível para todos os usuários logados | ✅ |
| Edição de perfil mantida acessível para todos os usuários logados | ✅ |

---

## Grupos criados

Migration: `apps/accounts/migrations/0002_criar_grupos_padroes.py`

| Slug | Nome legível |
|---|---|
| `administrador_escritorio` | Administrador do Escritório |
| `gerente` | Gerente |
| `advogado` | Advogado |
| `financeiro` | Financeiro |

Criados com `Group.objects.get_or_create(name=nome)` — idempotente.  
Não apaga grupos no reverse migration (`noop_reverse`).  
Dependências: `accounts.0001_initial` e `auth.0012_alter_user_first_name_max_length`.

> **Evolução — Fase 2.11B (2026-07-19):** os grupos `gerente` e `advogado` foram depreciados como papéis técnicos ativos. O papel técnico `limitado` foi introduzido pelas migrations `accounts.0005_criar_grupo_limitado` e `accounts.0006_migrar_papeis_legados`. Usuários nesses grupos foram migrados para `limitado`. Os objetos `Group` legados permanecem no banco sem usuários ativos. Ver seção "Fase 2.11B — Transição de papéis técnicos" abaixo.

---

## Helpers e constantes (`apps/accounts/decorators.py`)

### Constantes

Estado original (Fase 2.8):

```python
GRUPO_ADMINISTRADOR_ESCRITORIO = "administrador_escritorio"
GRUPO_GERENTE = "gerente"
GRUPO_ADVOGADO = "advogado"
GRUPO_FINANCEIRO = "financeiro"

GRUPOS_PADROES = [...]        # todos os 4 grupos
GRUPOS_CRIACAO_USUARIO = [    # grupos permitidos na tela de criação comum
    GRUPO_GERENTE,
    GRUPO_ADVOGADO,
    GRUPO_FINANCEIRO,
]
NOMES_GRUPOS = {...}           # slug → nome legível
```

Estado atual (pós Fase 2.11B):

```python
# Slugs dos grupos — papéis técnicos ativos
GRUPO_ADMINISTRADOR_ESCRITORIO = "administrador_escritorio"
GRUPO_LIMITADO = "limitado"
GRUPO_FINANCEIRO = "financeiro"

# Slugs legados — mantidos para referência em migrations e fallback de exibição
GRUPO_GERENTE = "gerente"
GRUPO_ADVOGADO = "advogado"

GRUPOS_PADROES = [
    GRUPO_ADMINISTRADOR_ESCRITORIO,
    GRUPO_LIMITADO,
    GRUPO_FINANCEIRO,
]

GRUPOS_CRIACAO_USUARIO = [
    GRUPO_LIMITADO,
    GRUPO_FINANCEIRO,
]

NOMES_GRUPOS = {
    GRUPO_ADMINISTRADOR_ESCRITORIO: "Administrador do Escritório",
    GRUPO_LIMITADO: "Limitado",
    GRUPO_FINANCEIRO: "Financeiro",
    # Legado — exibido enquanto houver registros históricos
    GRUPO_GERENTE: "Gerente (legado)",
    GRUPO_ADVOGADO: "Advogado (legado)",
}
```

### Funções

| Função | Descrição |
|---|---|
| `usuario_pertence_ao_grupo(user, nome)` | Verifica se o usuário está em um grupo específico |
| `usuario_admin_escritorio(user)` | Verifica se é administrador (três caminhos) |
| `nome_legivel_grupo(nome_grupo)` | Retorna nome humanizado do grupo |
| `obter_papel_principal_usuario(user)` | Retorna o primeiro grupo padrão do usuário |
| `requer_admin_escritorio` | Decorator para proteger views |

### Regra de verificação de administrador

`usuario_admin_escritorio(user)` retorna `True` por qualquer um dos três caminhos:

1. **`is_superuser=True`** — bypass para desenvolvimento e suporte técnico
2. **`PerfilUsuario.is_admin_escritorio=True`** — escape hatch para o primeiro admin do tenant e recuperação de acesso sem depender de grupos
3. **Grupo `administrador_escritorio`** — papel real de Administrador do Escritório

`PerfilUsuario.cargo` não é verificado aqui — é apenas descritivo.

---

## Administrador inicial do tenant demo

Ajuste feito no banco de desenvolvimento (não é alteração de código):

- `PerfilUsuario.is_admin_escritorio = True` para o usuário `admin`
- Usuário `admin` adicionado ao grupo `administrador_escritorio`
- `usuario_admin_escritorio(admin)` retorna `True` por todos os três caminhos

---

## Views implementadas / alteradas

| View | URL | Proteção |
|---|---|---|
| `index` | `/configuracoes/` | `@login_required` |
| `editar_perfil` | `/configuracoes/perfil/editar/` | `@login_required` |
| `novo_usuario` | `/configuracoes/usuarios/novo/` | `@requer_admin_escritorio` |
| `editar_escritorio` | `/configuracoes/escritorio/` | `@requer_admin_escritorio` |

---

## Form de criação de usuário (`CriarUsuarioEscritorioForm`)

Base: `UserCreationForm` do Django.

Campos:

| Campo | Tipo | Observação |
|---|---|---|
| `username` | CharField | único no tenant |
| `email` | EmailField | validado como único no tenant |
| `nome_completo` | CharField | salvo em `PerfilUsuario.nome_completo` |
| `cargo` | CharField | salvo em `PerfilUsuario.cargo` (descritivo) |
| `grupo` | `GrupoPapelChoiceField` | apenas `gerente`, `advogado`, `financeiro` (Fase 2.8); atualizado para `limitado`, `financeiro` na Fase 2.11B |
| `password1` | CharField | validado pelo Django |
| `password2` | CharField | confirmação |

Comportamento no `save()`:

- `is_active=True`, `is_staff=False`, `is_superuser=False`
- `PerfilUsuario.objects.get_or_create(user=user)` — garante perfil
- `user.groups.clear()` + `user.groups.add(grupo)` — atribui papel

O papel `administrador_escritorio` não aparece como opção — criação de admins é feita por fluxo administrativo separado.

UX de senha:

- Botão "Mostrar/Ocultar senha" alterna `type="password"` / `type="text"` em `password1` e `password2`
- Texto de orientação discreto abaixo dos campos

---

## Exibição de papel na lista de usuários

A view `index` monta `usuarios_contexto`, uma lista de dicionários:

```python
{
    "usuario": usuario,
    "papel": grupo.name if grupo else "",
    "papel_nome": nome_legivel_grupo(grupo.name) if grupo else "Sem papel definido",
}
```

Exibido no template com nome humanizado (estado original, Fase 2.8):
- Administrador do Escritório
- Gerente
- Advogado
- Financeiro
- Sem papel definido

Estado atual (pós Fase 2.11B):
- Administrador do Escritório
- Limitado
- Financeiro
- Gerente (legado) — exibido para usuários ainda no grupo antigo, se houver
- Advogado (legado) — idem
- Sem papel definido

`PerfilUsuario.cargo` continua exibido separadamente como campo descritivo.

---

## Ajuste visual de permissões

Botões ocultos para não-admins em `/configuracoes/`:

- **Novo usuário** — oculto com `{% if usuario_e_admin_escritorio %}`
- **Editar dados do escritório** — oculto com `{% if usuario_e_admin_escritorio %}`

Visível para todos os usuários logados:
- Card do usuário logado
- Botão "Editar perfil"
- Lista de usuários com papéis
- Dados do escritório em modo leitura

A proteção backend nas rotas permanece independente do ajuste visual.

---

## Decisões técnicas

- **`auth.Group`** é o mecanismo de papel nesta fase. `auth.Permission` fica para fase futura.
- **`PerfilUsuario.cargo`** não controla acesso — é apenas texto livre para exibição.
- **`PerfilUsuario.is_admin_escritorio`** é uma flag de segurança/recuperação de acesso, não o mecanismo principal de papel.
- **`/configuracoes/` não foi bloqueado inteiro** — manter acessível para que todos os usuários possam editar o próprio perfil.
- **Escopo de dados por equipe** exigirá aplicação de filtros nos módulos operacionais em fase futura.
- **Módulos operacionais** (Clientes, Processos, Tarefas, Agenda, Financeiro, Dashboard) não receberam restrições por papel nesta fase.

---

## Limitações conhecidas

- Sem bloqueio por papel nos módulos operacionais
- Sem `auth.Permission` granular por model/ação
- Sem equipes ou subgrupos
- Sem edição do papel de um usuário existente
- Sem exclusão/desativação de usuários pela interface
- Sem redefinição de senha pela interface
- Sem convite por e-mail
- Sem confirmação real de e-mail
- Sem auditoria de criação/edição de usuários

---

## Pendências futuras

### Fase 2.9 — Equipes e estrutura organizacional (concluída ✅)

- ✅ Criar model `Equipe` (tenant-scoped)
- ✅ Associar usuários a equipes via `MembroEquipe`
- ✅ Definir gerente/responsável por equipe (`eh_gerente`)
- ✅ Constantes de escopo: `ESCOPO_TUDO`, `ESCOPO_EQUIPES_GERENCIADAS`, `ESCOPO_EQUIPE`, `ESCOPO_PROPRIOS_ITENS`, `ESCOPO_NENHUM`
- Filtros por escopo nos módulos operacionais — fase futura (2.10D+)

### Fase 2.11B — Transição de papéis técnicos (concluída ✅)

- ✅ Grupo `limitado` criado; `gerente` e `advogado` depreciados como papéis técnicos ativos
- ✅ Usuários migrados para `limitado`; objetos `Group` legados preservados
- ✅ `decorators.py`, formulário de criação e template atualizados

---

## Fase 2.11B — Transição de papéis técnicos — Concluída

**Data**: 2026-07-19
**Commit**: `f5abb86 refactor(accounts): substituir papeis legados por limitado`

### Migrations

**`accounts.0005_criar_grupo_limitado`**

- Cria o grupo `limitado` com `Group.objects.get_or_create(name="limitado")`
- Idempotente — seguro reexecutar
- Dependências: `accounts.0004_rename_departamento_equipe`, `auth.0012_alter_user_first_name_max_length`
- Reverse deliberadamente vazio (noop)

**`accounts.0006_migrar_papeis_legados`**

- Move usuários não-administradores dos grupos `advogado` e `gerente` para `limitado`
- Administrador protegido pelos três mecanismos: `is_superuser`, `is_admin_escritorio`, grupo `administrador_escritorio`
- Não altera equipes nem `MembroEquipe.eh_gerente`
- Não exclui os objetos `Group` legados
- Reverse deliberadamente vazio — não é possível reconstruir o grupo anterior com segurança

### Separação conceitual documentada

Um mesmo usuário pode ter simultaneamente:

- Tipo de conta técnico: `limitado` (`auth.Group`)
- Cargo profissional: "Advogada Sênior" (`PerfilUsuario.cargo` — texto livre)
- Função de gerente: `MembroEquipe.eh_gerente=True` para a equipe "Cível"

`PerfilUsuario.cargo = "Advogado"` continua válido — é cargo profissional descritivo.
Gerente de equipe não é `auth.Group` técnico ativo; não cria usuários; não cria grupos Django nesta fase.
Futuramente, gerente poderá administrar permissões individuais apenas dos membros das equipes que gerencia.

### Formulário de criação de usuários (pós Fase 2.11B)

Papéis disponíveis na criação comum: `limitado` e `financeiro`.
Administrador continua sendo criado por fluxo administrativo separado.
O campo `cargo` continua como texto livre descritivo (placeholder: "Ex.: Advogado, Financeiro, Gerente").

### Resultado validado no tenant demo

| Usuário | Grupo antes | Grupo depois |
|---|---|---|
| `admin` | `administrador_escritorio` | `administrador_escritorio` (inalterado) |
| `advogado` | `advogado` | `limitado` |

- Zero usuários ativos associados aos grupos legados
- Equipes e gerências inalteradas

### Fase 2.11C — Modelagem de Permissões e Habilitações (próxima etapa)

Ainda não implementado:

- `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`, `HabilitacaoUsuario`
- Constantes de módulos, níveis e habilitações
- Seeds padrão por papel
- Helpers de resolução (papel → permissão efetiva)
- Telas de Permissões e Habilitações
- Sobrescritas individuais por usuário
- Acesso de gerente de equipe a dados dos membros
- Filtros nos módulos operacionais

### Fase futura — Permissões granulares

- `auth.Permission` por model/ação (`add_processo`, `change_cliente`, etc.)
- Perfis de permissão customizados por tenant
