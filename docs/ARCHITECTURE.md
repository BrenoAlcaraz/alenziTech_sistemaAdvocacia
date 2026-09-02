# Arquitetura — Breno - LawSystem

Guardrail, não enciclopédia: como o sistema é estruturado, onde cada
tipo de regra deve morar, o que reutilizar, o que não quebrar. Detalhe
de classe/função/endpoint se descobre no código.

## Estilo

Monólito modular Django — uma única aplicação, um único processo de
deploy. Módulos internos são apps Django, não microserviços; não usar
esse termo para descrever um app. PostgreSQL via `django-tenants`.
Server-side rendering (templates Django); sem API REST nem SPA
instaladas.

## Camadas e schemas

**Schema público** (`SHARED_APPS`) — plataforma SaaS compartilhada:
- `saas_tenants`: `Escritorio` (tenant), `Dominio`, `ConfiguracaoVisual`
  (white label).
- `saas_billing`: `Plano`, `Assinatura`. Lido (nunca escrito) por
  `configuracoes`/`dashboard` para exibir nome do plano — não gera
  lançamento no Financeiro do tenant (ver PDR-0003).

**Schema de cada tenant** (`TENANT_APPS`) — um schema PostgreSQL por
escritório, criado automaticamente (`auto_create_schema=True`):
`accounts`, `dashboard`, `clientes`, `processos`, `tarefas`,
`notificacoes`, `financeiro`, `agenda`, `chat`, `modelos`,
`laboratorio`, `configuracoes`. `django.contrib.auth` está em SHARED e
TENANT — cada tenant tem sua própria tabela `auth_user`.

**Resolução do tenant**: `TenantMainMiddleware` (primeiro middleware)
resolve o schema a partir do domínio (`Dominio → Escritorio`) antes de
qualquer view rodar. `ROOT_URLCONF` é único, compartilhado entre
público e tenant.

## Dependências entre módulos de negócio (direção permitida)

```
processos   → clientes, accounts (equipe)
tarefas     → processos, clientes (opcional), notificacoes
agenda      → processos, clientes (opcional)
financeiro  → clientes, processos (opcional)
dashboard   → clientes, processos, tarefas, agenda, financeiro (agregação, sem model próprio)
configuracoes → accounts
```

Nenhuma dependência circular. `apps.dashboard` não tem `models.py` —
é camada de agregação sobre os demais. Um módulo funcional de produto
não precisa corresponder a um único app (ex.: Dashboard é só views).

## Onde cada tipo de regra mora

| Tipo de regra | Local |
|---|---|
| Regra de negócio / validação de domínio | `apps/<app>/models.py`, `apps/<app>/forms.py` — nunca em template |
| Acesso a dados | `apps/<app>/views.py` via `QuerySet` do model — sem SQL bruto |
| Autorização e escopo | backend, nas views, via o kernel de `apps/accounts` (abaixo) — nunca só ocultando elemento de interface |
| Isolamento entre tenants | resolvido pelo schema ativo (middleware); nunca filtro manual de tenant dentro de uma query de negócio |

## Autorização — padrão a reutilizar

Kernel dinâmico em `apps/accounts`: `PapelAcesso`, `UsuarioPapel`,
`PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`,
`HabilitacaoUsuario`. Resolvido por `apps/accounts/permissoes.py`:

- `tem_permissao_modulo(user, "modulo")` — módulo está aberto para o
  usuário? Sempre a primeira checagem de qualquer view operacional.
- `tem_habilitacao(user, "modulo", "item")` — item específico dentro do
  módulo já aberto está habilitado?
- `nivel_acesso_modulo(user, "modulo")` — resolve `somente_seus`/
  `todos` (ou `solicitacoes`/`dados` em Financeiro). Só é escopo de
  fato quando uma view efetivamente filtra o `QuerySet` por ele — o
  valor sozinho não prova nada.
- Precedência: admin do escritório (acesso total) → `PermissaoUsuario`
  individual → união dos `PapelAcesso` ativos do usuário (maior nível
  entre eles) → fallback legado por `auth.Group` (só quando o usuário
  não tem nenhum `UsuarioPapel`) → nega.
- `usuario_admin_escritorio(user)` (`apps/accounts/decorators.py`) —
  único caminho: `PerfilUsuario.is_admin_escritorio=True` +
  `is_active=True`. Sem atalho por `is_superuser` ou grupo.

**Padrão de escopo de dados** (referência: `apps/clientes/views.py`,
`apps/processos/views.py`): leitura e mutação usam `QuerySet`s
distintos.
- Leitura (`lista`/`detalhe`) filtra pelo escopo efetivo do usuário
  (`somente_seus` → `responsavel == request.user`; `todos` → sem
  filtro adicional). Escopo nunca amplia acima do nível máximo
  autorizado do usuário.
- Mutação (`editar`/`desativar`/etc.) usa um `QuerySet` **separado**,
  restrito ao Administrador ou a `responsavel == request.user` — um
  nível de leitura `todos` nunca autoriza mutação fora da própria
  responsabilidade.
- Objeto é carregado já dentro do `QuerySet` autorizado
  (`get_object_or_404(<queryset>, pk=pk)`); nunca `Model.objects.get`
  seguido de checagem de posse depois. Fora do escopo → 404, não 403
  (não revela existência do registro a quem não tem escopo).

## Limites que não podem ser quebrados

- **Backend é a autoridade.** Toda verificação relevante deve ser
  reproduzível no servidor, independente da interface.
- **Isolamento de tenant nunca é ORM manual.** Não filtrar tenant à mão
  numa query — o schema ativo já garante isso; uma `ForeignKey`
  nunca cruza schemas.
- **Migration aplicada é imutável.** Correção é sempre nova migration,
  nunca edição da existente.
- **IA nunca amplia escopo.** Resposta/sugestão de IA nunca concede
  acesso que o usuário não teria diretamente.
- **Sem dependência circular entre apps de negócio.**
- **Sem framework novo por conveniência local** — antes de introduzir
  fila, cache, bundler JS ou ORM alternativo, checar se já resolve com
  o que existe (Django puro, PostgreSQL, Tailwind CLI).

## Riscos arquiteturais conhecidos

- Sem estratégia de segregação de arquivo por tenant (`MEDIA_ROOT` não
  particionado); nenhum model de negócio tem `FileField` hoje.
- Sem cache configurado, sem fila assíncrona (Celery/Redis/Channels) —
  qualquer introdução futura precisa carregar contexto de tenant
  explicitamente.
- Platform Admin não tem mecanismo de autorização dedicado — hoje é
  só superuser do Django Admin padrão.

## Referências

- Estado real de aplicação destes padrões, módulo a módulo: [STATUS.md](STATUS.md)
- Decisões arquiteturais duráveis: [decisions/](decisions/)
