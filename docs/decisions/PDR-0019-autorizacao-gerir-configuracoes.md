---
id: PDR-0019
title: Autorização do módulo Gerir aplicada às views administrativas de Configurações
status: accepted
owner: product-and-engineering
decision_date: 2026-09-04
last_reviewed: 2026-09-04
supersedes: []
complements: []
source_files: []
---

# PDR-0019 — Autorização do módulo Gerir aplicada às views administrativas de Configurações

## Contexto

O kernel de autorização já define `MODULO_GERIR` e quatro habilitações
granulares: `gerir_criar_usuario`, `gerir_habilitar_usuario_processos`,
`gerir_criar_equipe`, `gerir_habilitar_terceiros`. A primeira das
quatro já tem efeito prático — `apps/processos/views.py` já usa
`gerir_habilitar_usuario_processos` para controlar quem gerencia
integrantes habilitados de um processo (PDR-0014).

As views administrativas do app `apps/configuracoes` — criar usuário,
gerenciar equipes (e suas sub-rotas de membros/gerente) e configurar
permissões por tipo de conta — continuam restritas exclusivamente a
`@requer_admin_escritorio`, sem consultar o kernel. Isso é inconsistente
com o padrão já aplicado em Clientes, Processos, Tarefas, Financeiro,
Agenda, Chat e Modelos, e é o gap que `docs/STATUS.md` já identifica
como próximo passo, condicionado a esta decisão.

## Problema

Sem consultar o kernel para essas três telas, não é possível delegar
nenhuma dessas capacidades administrativas a um usuário que não seja
Administrador do escritório — mesmo que o kernel já preveja
habilitações prontas para isso. Mantém-se também uma inconsistência
arquitetural: `ITENS_POR_MODULO[MODULO_GERIR]` referencia três
habilitações (`gerir_criar_usuario`, `gerir_criar_equipe`,
`gerir_habilitar_terceiros`) sem nenhum ponto de aplicação real.

## Decisão

Mapeamento entre view e habilitação — usa somente o que já existe no
kernel, nenhuma habilitação nova é criada:

| View(s) | Habilitação |
|---|---|
| `novo_usuario` | `gerir_criar_usuario` |
| `equipes`, `nova_equipe`, `editar_equipe`, `equipe_membros`, `remover_membro_equipe`, `alternar_gerente_equipe` | `gerir_criar_equipe` |
| `permissoes` | `gerir_habilitar_terceiros` |

- `gerir_criar_equipe` cobre leitura (listar) e todas as mutações de
  equipe (criar, editar, gerenciar membros, alternar gerente) — não
  existe, e não é criada, uma habilitação separada de "editar equipe"
  ou "gerenciar membros". Mesmo padrão de PDR-0017 (arquivar reaproveita
  a autorização de editar, sem habilitação própria).
- `permissoes` (tela que define, por tipo de conta Limitado/Financeiro,
  quais módulos e níveis ficam ativos) usa `gerir_habilitar_terceiros`
  — configurar o que outros papéis podem acessar é, em essência,
  habilitar terceiros.
- `editar_escritorio` (identidade visual/dados cadastrais do
  escritório) permanece exclusivo de `@requer_admin_escritorio` — não
  há habilitação granular correspondente no kernel, e criar uma está
  fora do escopo desta decisão (busca antes de criar: sem necessidade
  concreta registrada para delegar especificamente essa tela agora).
- `index`, `editar_perfil`, `alterar_senha` (ações sobre o próprio
  perfil do usuário logado) continuam apenas `@login_required`, sem
  alteração — não são ações administrativas sobre terceiros.
- Cada view passa a checar `tem_habilitacao(user, MODULO_GERIR, <item>)`
  no lugar de `@requer_admin_escritorio` — a checagem já implica módulo
  `Gerir` ativo (regra interna do kernel: habilitação só é avaliada se
  o módulo estiver ativo). Mesmo padrão de chamada única já usado em
  `apps/processos/views.py::_pode_gerenciar_integrantes`.
- Administrador do escritório mantém acesso total às seis rotas e a
  `editar_escritorio` via bypass já existente no kernel
  (`habilitacao_efetiva`/`ctx.is_admin`) — nenhuma lógica nova é
  necessária para isso.
- Falta de habilitação bloqueia no backend (GET e POST), inclusive
  tentativa direta por POST — não é suficiente ocultar link/botão na UI.
- Conceder a habilitação a um papel ou usuário continua exigindo Django
  Admin (`HabilitacaoPapel`/`HabilitacaoUsuario`) — não existe, e esta
  decisão não cria, UI própria para isso. Ativar o módulo `Gerir` em si
  por tipo de conta já é possível pela tela de Permissões existente
  (`_MODULOS_CONFIG` já lista `"gerir"`).

## Consequências

- `docs/STATUS.md` passa a registrar Configurações com autorização do
  kernel aplicada nas três telas administrativas listadas, mantendo
  como gap conhecido a ausência de UI própria para papéis dinâmicos e
  habilitações granulares por item (segue só via Django Admin) e a
  não-delegação de `editar_escritorio`.
- Um Administrador que ativa o módulo `Gerir` para um papel sem
  conceder as habilitações granulares (via Django Admin) não delega
  nada de fato — comportamento esperado, consistente com os demais
  módulos já wireados ao kernel.
- `editar_escritorio` permanece um gap de delegação conhecido e
  registrado, não resolvido por esta decisão.

## Fora do escopo desta decisão

- `editar_escritorio`.
- Qualquer habilitação nova no kernel.
- UI própria para conceder `HabilitacaoPapel`/`HabilitacaoUsuario` ou
  papéis dinâmicos (`PapelAcesso`) além dos dois tipos de conta fixos —
  continua só via Django Admin.
- `gerir_habilitar_usuario_processos` — já aplicada em Processos,
  fora do escopo desta decisão.
- `index`, `editar_perfil`, `alterar_senha`.

## Critérios de aceite funcionais

- Usuário com módulo `gerir` ativo mas sem `gerir_criar_usuario` não
  acessa `novo_usuario` (GET nem POST).
- Usuário sem módulo `gerir` ativo não acessa nenhuma das seis rotas
  administrativas de Configurações cobertas por esta decisão.
- Usuário com módulo `gerir` ativo mas sem `gerir_criar_equipe` não
  acessa `equipes`, `nova_equipe`, `editar_equipe`, `equipe_membros`,
  `remover_membro_equipe` nem `alternar_gerente_equipe`.
- Usuário com módulo `gerir` ativo mas sem `gerir_habilitar_terceiros`
  não acessa `permissoes` (GET nem POST).
- Administrador do escritório continua acessando as seis rotas e
  `editar_escritorio` sem depender de nenhuma habilitação.
- `editar_escritorio` continua exclusivo de Administrador, sem
  regressão.

## Fontes

- [docs/STATUS.md](../STATUS.md) — gap identificado em "Próximos
  passos".
- Precedente de aplicação: [PDR-0017](PDR-0017-habilitacoes-criar-editar-andamento-processos.md).
