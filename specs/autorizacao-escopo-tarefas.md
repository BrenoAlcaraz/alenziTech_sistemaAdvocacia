# Spec — Autorização e escopo no módulo Tarefas

## Objetivo

Aplicar ao módulo Tarefas (`apps/tarefas`) o mesmo padrão de autorização
e escopo de dados já implementado e testado em Clientes e Processos
(kernel `apps/accounts`, documentado em
[ARCHITECTURE.md#autorização--padrão-a-reutilizar](../docs/ARCHITECTURE.md#autorização--padrão-a-reutilizar)).

Gap atual (`apps/tarefas/views.py`): toda view usa somente
`@login_required`. Nenhuma chama `tem_permissao_modulo`, nenhuma filtra
`QuerySet` por responsável, e a atribuição de tarefa a outro usuário
(campo "Atribuir a" em `TarefaForm`/`ReatribuirForm`) não checa a
habilitação `tarefas_atribuir_outros`, que já existe no kernel
(`apps/accounts/permissoes_constants.py`) mas nunca é consultada. É um
gap real da implementação atual, não uma exposição em produção — o
sistema ainda não está em produção.

O kernel já está preparado para este módulo: `MODULO_TAREFAS` está
registrado, com níveis `somente_seus`/`todos`
(`NIVEIS_POR_MODULO`) e a habilitação `HAB_TAREFAS_ATRIBUIR_OUTROS`
("Atribuir tarefa a outros usuários") já definida em `ITENS_POR_MODULO`.
Não é preciso criar nada no kernel — só passar a consultá-lo nas views,
reutilizando literalmente o desenho já usado em
`apps/clientes/views.py`.

## Comportamento esperado

- Toda view de `apps/tarefas/views.py` passa a checar
  `tem_permissao_modulo(request.user, MODULO_TAREFAS)` antes de
  qualquer ação. Módulo fechado → `PermissionDenied` (403), inclusive
  por acesso direto à URL.
- Leitura (`quadro`, `lista`) filtra pelo escopo efetivo do usuário:
  `somente_seus` → `responsavel == request.user`; `todos` → sem filtro
  adicional. Resolução do parâmetro `?escopo=` segue o mesmo contrato
  já validado em Clientes: ausente usa o nível máximo como padrão;
  presente com valor inválido (incluindo string vazia) ou acima do
  nível máximo autorizado → 403.
- Mutação (`editar`, `reatribuir`, `concluir`, `reabrir`, `iniciar`,
  `cancelar`, `excluir`) usa um `QuerySet` separado do de leitura,
  restrito ao Administrador do escritório ou a
  `responsavel == request.user`. Nível de leitura `todos` nunca
  autoriza mutação fora da própria responsabilidade — mesma regra já
  aplicada a Clientes/Processos.
- O objeto é sempre carregado dentro do `QuerySet` autorizado
  correspondente (`get_object_or_404(<queryset>, pk=pk)`). Fora do
  escopo → 404, nunca 403 (não revela a existência do registro a quem
  não tem escopo sobre ele).
- Criar uma tarefa atribuída a outro usuário (campo "Atribuir a"
  diferente de si mesmo, em `nova`) ou reatribuir uma tarefa para um
  responsável diferente do usuário atual (`reatribuir`) exige
  `tem_habilitacao(request.user, MODULO_TAREFAS, HAB_TAREFAS_ATRIBUIR_OUTROS)`
  ou ser Administrador do escritório. Sem isso, o usuário só pode criar
  tarefas para si mesmo e só pode reatribuir tarefa já sua de volta
  para si mesmo (não para terceiros).
- Administrador do escritório (`usuario_admin_escritorio`) mantém
  acesso irrestrito a todas as ações do módulo, independentemente de
  escopo ou da habilitação acima — mesma precedência já usada em
  Clientes/Processos.
- Consequência direta de aplicar escopo de mutação a uma UI que já
  renderizava um botão por ação por tarefa (quadro/lista): os botões de
  mutação (Iniciar/Concluir/Reabrir/Cancelar/Reatribuir/Editar/Excluir)
  só aparecem para quem pode de fato executá-los (Administrador ou
  `responsavel` atual). Sem isso, qualquer usuário com nível de leitura
  `todos` veria botões de ação em tarefas alheias que resultam em 404
  ao clicar. A autorização real permanece exclusivamente no backend —
  isto é reforço de UX, não um mecanismo de autorização.

## Regras de negócio relevantes

- Escopo de leitura (`somente_seus`/`todos`) é sempre resolvido por
  `nivel_acesso_modulo`; nunca inferido do parâmetro de URL sem
  validação contra o nível máximo do usuário.
- Escopo de mutação nunca é ampliado pelo nível de leitura — é sempre
  Administrador ou responsável atual da tarefa, mesmo que o usuário
  tenha nível `todos` para leitura.
- `criador`/`atribuidor` da tarefa, quando diferentes do `responsavel`
  atual, não ganham por si só direito de mutação — a regra de mutação
  olha exclusivamente para `responsavel` atual (ou Administrador),
  consistente com o padrão já usado para `Cliente.responsavel`.
- A habilitação `tarefas_atribuir_outros` controla exclusivamente a
  capacidade de direcionar uma tarefa a outro usuário (criação ou
  reatribuição) — não controla leitura nem as demais mutações
  (editar conteúdo, concluir, reabrir, iniciar, cancelar, excluir).

## Fora do escopo

- Autorização/escopo do módulo Agenda — depende da mesma lógica, mas é
  trabalho separado (gap distinto listado em STATUS.md).
- Notificação de conclusão de tarefa (PDR-0016).
- Novas habilitações granulares em Tarefas além de
  `tarefas_atribuir_outros`, que já existe no kernel.
- Alterações no modelo `Tarefa`/`ReatribuicaoTarefa` ou em
  `TarefaForm`/`ReatribuirForm` além do necessário para consultar a
  habilitação existente.
- Redesenho de UI do quadro/lista além do mínimo para refletir escopo
  (ex.: seletor de escopo, que replica o padrão visual já usado em
  Clientes; e ocultação dos botões de mutação por tarefa não autorizada
  ao usuário atual, consequência direta de aplicar escopo de mutação a
  uma UI que já exibia essas ações por item — ver "Comportamento
  esperado").
- Qualquer mudança no padrão de autorização em si (`apps/accounts`) —
  é reutilizado como está.

## Critérios de aceite

- Usuário sem acesso ao módulo Tarefas recebe 403 em qualquer view do
  módulo, inclusive por acesso direto via URL.
- Usuário com nível `somente_seus` só vê, em `quadro`/`lista`, tarefas
  cujo `responsavel` é ele mesmo.
- Usuário com nível `todos` vê todas as tarefas do escritório em
  `quadro`/`lista`.
- Parâmetro `?escopo=` ausente usa o nível máximo do usuário; presente
  com valor inválido (incluindo vazio) ou acima do nível máximo
  autorizado retorna 403.
- Editar, reatribuir, concluir, reabrir, iniciar, cancelar e excluir
  uma tarefa só são permitidos ao Administrador do escritório ou ao
  `responsavel` atual da tarefa.
- Tentativa de mutação sobre tarefa fora do escopo autorizado (URL
  direta) retorna 404, não 403.
- `?escopo=` inválido também é rejeitado (403) nas rotas de mutação,
  mesmo sem influenciar o `QuerySet` de mutação — mesmo padrão de
  `apps/clientes/views.py` (editar/desativar/reativar).
- Criar tarefa com "Atribuir a" diferente de si mesmo exige
  `tarefas_atribuir_outros` ou ser Administrador; sem isso, a
  atribuição a terceiros é rejeitada (tarefa só pode ser criada para
  si mesmo).
- Reatribuir tarefa para responsável diferente do usuário atual exige
  `tarefas_atribuir_outros` ou ser Administrador.
- Administrador do escritório mantém acesso irrestrito a todas as
  ações do módulo, independentemente de escopo/habilitação.
- Testes de autorização existentes para Clientes/Processos continuam
  passando (nenhuma mudança no kernel `apps/accounts`).
