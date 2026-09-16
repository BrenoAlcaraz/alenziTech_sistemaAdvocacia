# Spec — Edição de Solicitação Financeira (custas) enquanto pendente de aprovação

## Objetivo

Permitir editar uma `SolicitacaoFinanceira` enquanto ela ainda não foi
aprovada — hoje só existe transição de status (`processar_solicitacao`),
sem nenhuma view de edição de campos.

## Comportamento esperado

### Janela de edição
- Edição permitida enquanto `status` for `solicitada` ou `em_analise`.
- A partir de `aprovada`, `rejeitada` ou `paga`, edição bloqueada — são
  estados finais ou já em processamento pelo caixa (PDR-0015).
- Regra vale tanto no acesso à view (retornar `PermissionDenied` se fora
  da janela) quanto na visibilidade do botão na UI.

### Campos editáveis
- Mesmos campos do formulário de criação (`SolicitacaoFinanceiraForm`):
  tipo, descrição, valor, cliente, processo, vencimento, data_gasto,
  anexo, observação.
- Reaproveita `SolicitacaoFinanceiraForm` também na edição (mesmo form,
  agora com `instance=solicitacao`) — não cria form paralelo.
- Quando a solicitação nasceu com `processo_fixo` (aba Custas Judiciais
  de um processo, ver commit 2dae1fb), a edição preserva a mesma trava
  já aplicada na criação (`_travar_tipo_processo_cliente`): tipo fixo em
  "pagamento", processo e cliente não trocáveis. Como o form não guarda
  se nasceu travado, a view infere a partir do `processo` já salvo na
  instância (`solicitacao.processo`) e passa como `processo_fixo` ao
  reconstruir o form.

### UI
- Botão/link "Editar" no card de detalhe da solicitação
  (`detalhe_solicitacao.html`), visível apenas quando
  `status in {"solicitada", "em_analise"}`.
- Reaproveita o template `form_solicitacao.html` no modo edição (mesmo
  form, cabeçalho/texto ajustado para "Editar solicitação").

## Fora do escopo

- Exclusão de `SolicitacaoFinanceira` em qualquer estado — não existe
  hoje, não será criada nesta rodada. Retomar só se o usuário confirmar
  necessidade.
- Edição direta de `CustaJudicial` — continua gerada automaticamente ao
  atingir `paga`, sem edição própria.
- Qualquer mudança nas transições de status (`pode_transicionar_para`,
  `avancar_para`) — este trabalho é só sobre editar os campos, não o
  fluxo de aprovação.

## Critérios de aceite

- Solicitação em `solicitada`/`em_analise` mostra opção de editar; a
  partir de `aprovada`/`rejeitada`/`paga`, não mostra.
- Acessar a edição diretamente por URL fora da janela permitida retorna
  `PermissionDenied`, não só esconde o botão.
- Edição usa os mesmos campos e travas de cliente/processo do formulário
  de criação, inclusive quando a solicitação nasceu vinculada a um
  processo fixo.
- Salvar a edição atualiza a solicitação existente (mesmo `pk`), não
  cria uma nova.
