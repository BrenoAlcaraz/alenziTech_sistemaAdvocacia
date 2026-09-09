# Arquitetura — Breno - LawSystem

Guardrail, não enciclopédia: como o sistema é estruturado, onde cada
tipo de regra deve morar, o que reutilizar, o que não quebrar. Detalhe
de classe/função/endpoint se descobre no código.

## Estilo

Monólito modular Django — uma única aplicação, um único processo de
deploy. Módulos internos são apps Django, não microserviços; não usar
esse termo para descrever um app. PostgreSQL via `django-tenants`.
Server-side rendering (templates Django); sem API REST nem SPA
instaladas — exceção pontual: endpoints utilitários que devolvem JSON
para alimentar um único campo dependente de formulário (ver "Campos
dependentes em formulário", abaixo); não é uma superfície de API, não
versionar nem expor fora do próprio formulário que o consome.

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

**Storage de arquivos**: uploads usam namespaces
`tenants/<schema>/<publico|protegido>/...`. Arquivos protegidos usam um
storage sem URL pública e são entregues somente por views que carregam o
objeto pelo `QuerySet` autorizado. Ativos públicos de identidade visual
são resolvidos pelo domínio/tenant da requisição em rota própria. Não
servir `MEDIA_ROOT` por `MEDIA_URL`, inclusive em desenvolvimento.

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
  `todos` (ou `solicitacoes`/`dados_proprios`/`dados_todos` em
  Financeiro — `dados_proprios`/`dados_todos` funcionam como o
  `somente_seus`/`todos` dos demais módulos, mas só sobre
  `LancamentoFinanceiro`; `SolicitacaoFinanceira` permanece com escopo
  próprio por `solicitante`, igual para os dois). Só é escopo de fato
  quando uma view efetivamente filtra o `QuerySet` por ele — o valor
  sozinho não prova nada.
- Precedência: admin do escritório (acesso total) → `PermissaoUsuario`
  individual → união dos `PapelAcesso` ativos do usuário (maior nível
  entre eles) → fallback legado por `auth.Group` (só quando o usuário
  não tem nenhum `UsuarioPapel`) → nega.
- `usuario_admin_escritorio(user)` (`apps/accounts/decorators.py`) —
  único caminho: `PerfilUsuario.is_admin_escritorio=True` +
  `is_active=True`. Sem atalho por `is_superuser` ou grupo.

**Adicionar um item novo em `ITENS_POR_MODULO`** (`apps/accounts/permissoes_constants.py`)
não basta sozinho: o `CheckConstraint` de `modulo`/`item` em
`HabilitacaoPapel.Meta` e `HabilitacaoUsuario.Meta`
(`apps/accounts/models.py`) usa uma lista literal própria por módulo,
não derivada de `ITENS_POR_MODULO` — ambas precisam ser atualizadas
juntas, com uma migration nova (`AlterField` de `item` +
`Remove`/`AddConstraint`, gerada por `makemigrations`), no formato de
`0015_adicionar_habilitacao_reabrir_lancamento_pago.py`. Sem isso, o
banco rejeita a gravação da habilitação nova com violação de
`chk_habilitacaopapel_modulo_item`/`chk_habilitacaousuario_modulo_item`.

**Gravar em `PermissaoPapel`/`HabilitacaoPapel`**: filtrar e gravar
sempre por um único identificador por vez — `tipo_conta` OU `papel`,
nunca os dois juntos no mesmo `filter`/`update_or_create`. A migration
`0011_migrar_papeis_e_presets` associou `papel` a linhas legadas de
`tipo_conta` ('limitado'/'financeiro' apontam também para os presets
'Advogado Associado'/'Gestor Financeiro') sem zerar o `tipo_conta`
original — essas linhas ficam com os dois campos preenchidos ao mesmo
tempo. Um lookup pelos dois campos juntos não encontra essa linha e
tenta inserir uma duplicata, violando a `UniqueConstraint`. Referência:
`apps/configuracoes/views.py::_build_modulos_permissao`/`_salvar_permissoes`.

**Efeito colateral em Processos ao mudar permissão de um usuário**:
qualquer código que grave `PermissaoPapel`/`HabilitacaoPapel` (por
papel ou tipo de conta) ou `PermissaoUsuario`/`HabilitacaoUsuario`
(override individual) e que possa remover acesso ao módulo Processos
deve chamar `transferir_processos_de_usuarios_sem_acesso`
(`apps/processos/services.py`) na mesma transação — sem isso, o
`responsavel` de um Processo fica "órfão" (aponta para alguém sem
`tem_permissao_modulo`). Referência: `apps/configuracoes/views.py::_salvar_permissoes`/`usuario_overrides`.

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

Exceção deliberada em `LancamentoFinanceiro` (`apps/financeiro/views.py`):
`dados_todos` amplia leitura **e** mutação (sem QuerySet separado) —
não é um nível de coordenação de equipe como `todos` nos demais
módulos, é um nível de confiança mais alto dentro do próprio módulo
Financeiro. `dados_proprios` usa o mesmo `QuerySet` filtrado por
`responsavel` tanto para leitura quanto mutação.

Consequência a ter em mente ao configurar permissões: em `reabrir_lancamento`,
o escopo é checado antes da habilitação `financeiro_reabrir_lancamento_pago`
— com `dados_proprios`, essa habilitação nunca alcança um lançamento cujo
`responsavel` é outro usuário (404 antes de chegar na checagem da
habilitação). Um usuário pensado para reabrir lançamento pago de terceiros
precisa de `dados_todos`, não `dados_proprios` + a habilitação.

## Campos dependentes em formulário (ex.: Cliente → Processo) — padrão a reutilizar

Quando um campo `ModelChoiceField` deve ser restrito pelo valor de
outro campo do mesmo formulário (hoje: Processo restrito ao Cliente
selecionado, em `LancamentoFinanceiroForm`, `CustaJudicialForm`,
`HonorarioForm`, `SolicitacaoFinanceiraForm` — `apps/financeiro/forms.py`;
`TarefaForm` — `apps/tarefas/forms.py`; `CompromissoForm` —
`apps/agenda/forms.py`):

- **Filtro inicial no `__init__` do form**: o queryset do campo
  dependente já nasce restrito ao valor do campo "pai" conhecido no
  momento (`self.data`, `self.initial` ou `self.instance`) — cobre
  reenvio após erro de validação e edição, sem depender de JS.
- **Atualização em tela sem reload**: o campo pai leva o atributo
  `data-cliente-filtro` e o campo dependente leva `data-processos-url`
  apontando para o endpoint JSON do próprio app (`reverse(...)` no
  `__init__` do form). O JS genérico em `static/js/main.js` (seção
  "Filtro de Processo por Cliente") liga os dois por esses atributos —
  nenhuma template precisa de alteração, os `data-*` já saem no widget
  renderizado por `{{ form.<campo> }}`.
- **Endpoint por app, não compartilhado entre apps**: cada app expõe
  sua própria rota (`<app>/processos-por-cliente/`) que reaproveita a
  mesma checagem de `tem_permissao_modulo` já usada pela view que
  renderiza o formulário — nunca uma autorização nova ou mais ampla só
  para o endpoint. A consulta em si vem de um helper único e
  compartilhado, `apps/processos/services.py::processos_do_cliente`.
- **Validação no backend é sempre obrigatória**, independente do JS, e
  mora no `clean()` do **model** (não do form):
  `apps/processos/services.py::processo_pertence_ao_cliente` usado no
  `clean()` de `LancamentoFinanceiro`, `CustaJudicial`, `Honorario`,
  `SolicitacaoFinanceira`, `Tarefa` e `Compromisso` — rejeita salvar
  uma combinação inconsistente por qualquer via, incluindo o Django
  Admin desses models (que usa `ModelForm` automático, sem o form
  customizado do app). Colocar a mesma checagem só no `clean()` do
  form deixaria o Admin descoberto.

## Tempo real (WebSocket / Channels) — padrão a reutilizar

Único uso de WebSocket no projeto até aqui: entrega em tempo real de
mensagem nova no Chat (`apps/chat/consumers.py`). Runtime ASGI
(`channels` + `daphne`) roda ao lado do WSGI já existente —
`config/asgi.py` expõe um `ProtocolTypeRouter` com o caminho HTTP
inalterado e um caminho `websocket` próprio (rotas em
`config/routing.py`).

- **Resolução de tenant e usuário**:
  `apps/saas_tenants/channels_middleware.py::TenantWebsocketMiddleware`
  é o equivalente, para WebSocket, de `TenantMainMiddleware` (schema
  pelo domínio) + `AuthenticationMiddleware` (usuário pela sessão) no
  caminho HTTP — resolve os dois numa única chamada síncrona, sem
  `await` no meio.
- **Regra crítica, não óbvia**: o schema resolvido no `connect()` não
  pode ser tratado como ambiente para o resto da vida da conexão —
  `channels`/`asgiref` serializam chamadas síncronas de conexões
  concorrentes numa única thread compartilhada, sem contexto
  thread-sensitive próprio por conexão; outra conexão pode trocar o
  schema dessa mesma thread entre duas chamadas do mesmo consumer. Toda
  operação de banco dentro de um consumer passa por
  `tenant_database_sync_to_async` (mesmo módulo), que troca o schema e
  roda a consulta numa única chamada síncrona — nunca em chamadas
  separadas.
- **Grupo do channel layer sempre prefixado por `tenant.schema_name`**
  (`apps/chat/realtime.py`) — nunca um identificador de conversa/usuário
  sozinho, já que o mesmo pk existe em schemas diferentes.
- **Mensagem trafega como fragmento HTML renderizado no backend**
  (`render_to_string`, reaproveitando o mesmo template do envio por
  HTTP), nunca como JSON interpretado por lógica no cliente — mantém o
  padrão de renderização no servidor da seção "Estilo".
- Autorização para entrar num grupo replica exatamente a checagem já
  feita na view HTTP equivalente (`tem_permissao_modulo` + posse) —
  nunca uma regra nova ou mais ampla só para o consumer.

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

- Sem cache configurado, sem fila assíncrona de jobs (Celery/Redis) —
  qualquer introdução futura precisa carregar contexto de tenant
  explicitamente. Primeiro job periódico do projeto (PDR-0016, lembrete
  de Agenda) segue esse padrão via management command (`python manage.py
  enviar_lembretes_agenda`, `apps/agenda/management/commands/`),
  iterando `Escritorio` ativo e entrando no schema de cada um com
  `schema_context`; disparo periódico real (cron do SO, Task Scheduler)
  é externo ao código. Reutilizar esse padrão antes de criar um novo
  para qualquer próximo job por tenant.
- Channel layer do WebSocket (Chat) roda em `InMemoryChannelLayer` —
  só serve um único processo. Produção com mais de um worker exige um
  backend compartilhado (ex.: Redis); decisão ainda não tomada (ver
  `docs/STATUS.md`, módulo Chat).
- Platform Admin não tem mecanismo de autorização dedicado — hoje é
  só superuser do Django Admin padrão.

## Referências

- Estado real de aplicação destes padrões, módulo a módulo: [STATUS.md](STATUS.md)
- Decisões arquiteturais duráveis: [decisions/](decisions/)
