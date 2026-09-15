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
Excluir o registro que referencia um `FileField` remove também o
arquivo do storage via signal `post_delete` no próprio app dono do
model (`apps/<app>/signals.py`, conectado em `AppConfig.ready()` —
mesmo padrão já usado por `apps/accounts/signals.py`) — cobre exclusão
direta, cascata e Django Admin, não só uma view específica. Padrão a
reutilizar em qualquer model novo com `FileField`/`StorageProtegido`
(referência: `apps/processos/signals.py`, `apps/chat/signals.py`,
`apps/financeiro/signals.py`).

**Substituir (não excluir) um `FileField` já preenchido — ex.: usuário
envia uma imagem nova para um campo que já tinha uma**: capturar o
`FieldFile` atual **antes** de vincular o `ModelForm` à instância —
`form.is_valid()` já sobrescreve o atributo em memória com o arquivo
novo (via `construct_instance` em `_post_clean`), então chamar
`FieldFile.delete()` depois disso apaga o valor novo, não o antigo,
porque `FieldFile.delete()` também faz
`setattr(self.instance, campo, None)` no mesmo objeto de instância.
Apagar o arquivo antigo do disco deve usar
`arquivo_antigo.storage.delete(arquivo_antigo.name)` diretamente (só
storage, sem tocar a instância) — nunca `FieldFile.delete()` nesse
cenário. Referência: `apps/modelos/views.py`
(`_arquivos_estilo_documento_atuais`/`_substituir_arquivos_estilo_documento`).

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

## Seletor de Processo com busca — padrão a reutilizar

Todo campo que referencia um Processo (Intimações, Apensos, e os
campos dependentes de Cliente listados acima) usa
`ProcessoChoiceField` (`apps/processos/forms.py`), nunca
`forms.ModelChoiceField` puro:

- **Label padrão "Título — Número"**: `label_from_instance` delega em
  `apps/processos/services.py::rotulo_processo` — mesma função usada
  pelos três endpoints `processos-por-cliente` (financeiro, agenda,
  tarefas) ao montar o `label` do JSON, para o rótulo não regredir
  para só o título depois que o filtro por Cliente reconstrói as
  opções via fetch.
- **Widget com busca (combobox)**: usar `PROCESSO_SELECT_ATTRS`
  (mesmo módulo) como `attrs` do `forms.Select` — o
  `data-processo-busca` liga o campo ao JS genérico em
  `static/js/main.js` (seção "Busca em campo de Processo"), que
  substitui o `<select>` simples por um campo de texto com filtro em
  tempo real. Em `ModelForm`, quando o campo `processo` vem do
  `Meta.fields` (não declarado explicitamente na classe), trocar a
  classe do campo via `Meta.field_classes = {"processo":
  ProcessoChoiceField}` — só o widget não muda o `label_from_instance`.
- **Nenhuma template precisa de alteração** — mesmo princípio da seção
  anterior, os `data-*` já saem no widget renderizado.
- O `<select>` original continua no DOM (oculto via `sr-only`, nunca
  `display:none`/`hidden`) para não quebrar o foco por Tab; o JS
  também zera `required` nele porque a validação nativa do navegador
  não alcança um campo oculto e bloqueia o submit em silêncio — a
  obrigatoriedade real continua garantida em `form.is_valid()` no
  servidor.

## Campos condicionados a um `<select>` — padrão a reutilizar

Quando um bloco do formulário só faz sentido para certos valores de um
`<select>` (hoje: classificação Única/Parcelado/Recorrente e duração
Quantidade/Data final/Indeterminado em `LancamentoFinanceiroForm`,
`apps/financeiro/forms.py`; template `form_lancamento.html`):

- O `<select>` leva `data-toggle-select="<grupo>"` no widget
  (`forms.Select(attrs={"data-toggle-select": "..."})`); cada bloco
  condicional leva `data-toggle-panel="<grupo>"
  data-toggle-values="valor1,valor2"` e a classe `hidden` por padrão.
- O JS genérico em `static/js/main.js` (seção "Campos condicionados a
  um `<select>`") mostra/esconde cada painel do grupo conforme o valor
  atual do select, tanto no carregamento quanto em `change` — nenhuma
  lógica nova por formulário, só os atributos `data-*` no template.
- Pode aninhar grupos independentes na mesma tela (ex.: duração dentro
  de recorrente) — cada `<select>` só enxerga os painéis do seu próprio
  `data-toggle-select`.
- **Validação no backend é sempre obrigatória**, independente do JS —
  mora no `clean()` do form (`LancamentoFinanceiroForm.clean()`),
  reaplicada mesmo se o campo escondido chegar preenchido via POST
  manual.

## Editor de texto embutido (contenteditable) — padrão a reutilizar

Usado nas folhas estilo Word de `apps/modelos` (`templates/modelos/
_estilo_editor_js.html`, `_nova_peca_editor_js.html`) — vanilla JS,
sem biblioteca de rich-text. Duas armadilhas reais, encontradas testando
manualmente no navegador (não aparecem em teste automatizado, que não
executa JS de verdade):

- **Botão de formatação (negrito/itálico/alinhamento) que chama
  `document.execCommand` não funciona sem `mousedown` →
  `preventDefault()` no próprio botão.** O `mousedown` do clique
  colapsa a seleção de texto da área `contenteditable` antes do `click`
  rodar — `execCommand` então executa sobre seleção vazia/errada, sem
  efeito visível e sem erro no console. Todo botão de ribbon que
  depende da seleção atual do `contenteditable` (não os que inserem
  numa posição já recalculada via `Range`/`Selection`, como os botões
  de "+ Inserir jurisprudência/citação") precisa desse
  `addEventListener("mousedown", e => e.preventDefault())`.
- **Campo real do form escondido (`display:none`) sincronizado por JS
  só no `submit` — se for `required`, a validação HTML5 bloqueia o
  envio antes do listener de `submit` rodar, silenciosamente** (campo
  invisível não mostra a mensagem de erro nativa; nenhum evento
  `submit` chega a disparar). Duas saídas, usadas juntas: `novalidate`
  no `<form>` (validação de obrigatoriedade continua acontecendo no
  servidor via `form.is_valid()`) e sincronizar o campo a cada `input`
  do `contenteditable`, não só no `submit` (mantém o valor sempre
  válido, não só na hora de enviar).
- Inserir HTML no fim do conteúdo via `execCommand("insertHTML")` com
  `Range`/`Selection` recalculados na hora funciona; já colapsar a
  seleção no fim do último elemento existente e confiar que o navegador
  cria um irmão novo não é garantido — o Chrome pode mesclar o HTML
  inserido dentro do último bloco em vez de criar um novo. Preferir
  `document.createElement`/`appendChild` direto no DOM para inserir um
  bloco novo no fim de um `contenteditable`.

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
- **Origem do handshake validada antes de tudo**: o mesmo middleware
  recusa a conexão (`4403`) se o host do header `Origin` não bater com
  o `Host` da própria conexão — proteção contra Cross-Site WebSocket
  Hijacking, já que a autenticação depende só do cookie de sessão, sem
  CSRF token no handshake. Por ser checagem de middleware compartilhado,
  cobre automaticamente qualquer consumer novo, sem repetir a checagem
  por consumer.
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
