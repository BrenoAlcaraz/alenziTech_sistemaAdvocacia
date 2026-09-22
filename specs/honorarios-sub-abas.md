# Spec — Sub-abas Contratuais/Sucumbência em Honorários

## Objetivo

Organizar a aba "Honorários" do Financeiro em duas sub-abas —
**Contratuais** e **Sucumbência** — para reduzir a lista misturada
atual e facilitar achar um honorário pelo tipo. É reorganização de
interface, não redesenho do modelo de honorários.

## Comportamento esperado

- A aba "Honorários" (dentro de `{% abas_financeiro %}`) ganha duas
  sub-abas client-side, no mesmo padrão já usado em
  `templates/financeiro/extrato_custas_cliente.html` (`data-tab` /
  `data-tab-panel` / `data-tab-group`, troca sem reload de página):
  - **Contratuais** — honorários com `tipo == "contratual"`, e também
    os tipos legados `exito`/`outro` (não são mais criáveis, mas
    seguem editáveis conforme `docs/STATUS.md`) — decisão registrada
    nesta spec: entram em Contratuais, sem sub-aba própria.
  - **Sucumbência** — honorários com `tipo == "sucumbencia"`.
- Cada card de honorário continua exatamente como é hoje em
  `honorarios_lista.html` (valores, status, badges, ações de
  confirmar/cancelar, aviso de êxito, cálculo de sucumbência
  corrigida) — só muda o agrupamento visual em duas listas.
- "+ Novo honorário" continua único, abrindo o mesmo formulário atual
  (`form_honorario.html`), que já pergunta o tipo — sem duplicar botão
  por sub-aba.
- `honorarios_lista` (view) passa a separar a lista já carregada em
  duas listas de contexto (ex. `honorarios_contratuais` e
  `honorarios_sucumbencia`) em vez de uma lista única — sem alterar a
  query/escopo (`_honorarios_no_escopo`) nem o cálculo por item já
  existente.
- Sub-aba inicial ativa: Contratuais (primeira da esquerda), mesmo
  padrão do extrato de custas.
- Estado vazio (`components/empty_state.html`) por sub-aba, com
  mensagem própria de cada uma, não uma mensagem genérica só quando as
  duas estiverem vazias.

## Regras de negócio relevantes

- Nenhuma regra de negócio nova. Reaproveita integralmente
  `Honorario.tipo` (PDR-0032) e todo o comportamento de
  `docs/modules/financeiro.md#honorários` (recebimento parcial,
  confirmação exclusiva do Administrador, correção monetária,
  sucumbência calculada, aviso de êxito).

## Fora do escopo

- Precatório (novo tipo/fluxo de honorário).
- Extração de contrato por IA.
- Análise de sentença/acórdão por IA.
- Qualquer mudança no ciclo de confirmação de recebimento (parcial,
  exclusividade do Administrador, notificação do advogado).
- Qualquer outra alteração de regra financeira ainda não decidida
  (ex.: mudar o que é `confirmavel`, mudar cálculo de correção,
  mudar categorias de receita geradas).
- Filtros adicionais dentro de cada sub-aba (processo, cliente,
  status) — não pedido, mantém o comportamento atual de listar tudo
  no escopo.

## Critérios de aceite

- Abrir "Honorários" mostra as sub-abas Contratuais e Sucumbência,
  Contratuais ativa por padrão, troca sem reload de página.
- Todo honorário com `tipo == "contratual"`, `"exito"` ou `"outro"`
  aparece em Contratuais; todo `tipo == "sucumbencia"` aparece em
  Sucumbência — nenhum honorário existente some da listagem.
- Conteúdo de cada card permanece idêntico ao atual (nenhuma
  informação, ação ou cálculo removido ou alterado).
- "+ Novo honorário" continua funcionando igual, um único botão,
  independente da sub-aba ativa.
- Testes de `apps/financeiro/tests/test_honorarios*.py` continuam
  passando sem alteração de asserts sobre dados/regra — só ajuste se
  algum teste ler a lista pelo nome de contexto antigo da view.
