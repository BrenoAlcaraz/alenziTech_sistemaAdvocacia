---
id: PDR-0022
title: Honorários — recebimento parcial e correção monetária/juros
status: accepted
owner: product-and-engineering
decision_date: 2026-09-13
last_reviewed: 2026-09-13
supersedes: []
complements:
  - PDR-0007
source_files: []
---

# PDR-0022 — Honorários: recebimento parcial e correção monetária/juros

## Contexto

PDR-0007 define o cadastro manual de honorários (tipo, valor estimado,
valor efetivo, processo, cliente, datas prevista/recebida, status,
observações) e deixa a confirmação de recebimento como ação única e
exclusiva do Administrador do escritório. Ele não trata dois casos
reais do dia a dia: valores recebidos em parte (ex.: execução que
penhora só uma fração do total devido) e a correção monetária/juros que
incide sobre um valor que fica pendente por meses ou anos.

## Problema

Sem recebimento parcial, o Administrador só pode confirmar tudo de uma
vez, mesmo quando só uma fração do valor efetivamente entrou — forçando
a esperar o valor total para registrar o que já é receita real. Sem
correção monetária, o valor pendente exibido fica desatualizado em
relação ao tempo decorrido.

## Decisão

Um honorário passa a admitir **múltiplas confirmações de recebimento**
até atingir o valor total, e pode opcionalmente ter **correção
monetária/juros** habilitada, com taxa mensal informada manualmente no
cadastro — sem integração com índice externo (INPC/Selic) nesta versão.

### Recebimento parcial

- O honorário passa a acumular `valor_recebido` (soma de todas as
  confirmações já feitas), distinto de `valor_efetivo` (valor total a
  receber, corrigido quando aplicável).
- Cada confirmação registra o valor recebido naquele momento e gera, na
  mesma operação, um `LancamentoFinanceiro` de receita (`pago`) só com
  aquele valor parcial — segue a mesma regra de PDR-0004: só a
  confirmação altera o saldo realizado.
- O honorário permanece em `previsto` enquanto `valor_recebido` for
  menor que `valor_efetivo`; passa a `recebido` só quando
  `valor_recebido >= valor_efetivo`.
- Cada confirmação (parcial ou final) notifica o advogado responsável
  pelo processo, exatamente como já ocorre hoje (PDR-0007) — sem
  distinção entre confirmação parcial e final para esse efeito.

### Correção monetária/juros

- Campo opcional no cadastro: `taxa_mensal` (percentual informado
  manualmente) e `data_termo` (data a partir da qual a correção passa a
  incidir). Quando não preenchido, o honorário se comporta exatamente
  como hoje, sem correção.
- O valor pendente (`valor_efetivo − valor_recebido`) é recalculado a
  cada confirmação de recebimento, aplicando `taxa_mensal` sobre o
  tempo decorrido desde `data_termo` ou da confirmação anterior, o que
  for mais recente.
- Sem integração com índice externo (INPC, Selic ou qualquer outro) —
  fica registrado como direção futura desejada, não descartada, caso
  surja demanda real (exigiria novo PDR por trazer dependência externa
  e job periódico).

### Autorização

- Recebimento parcial segue a **mesma restrição já existente** para
  confirmação de recebimento em PDR-0007: exclusiva de quem passa
  `usuario_admin_escritorio` (Administrador do escritório) — sem
  habilitação granular delegável.
- Habilitar/editar a correção monetária de um honorário (taxa mensal,
  data-termo) segue a mesma restrição: exclusiva do Administrador do
  escritório, pelo mesmo motivo já registrado em STATUS.md para outros
  dados sensíveis de acesso pouco frequente e sem gargalo operacional
  que justifique delegação (mesmo padrão usado para identidade visual
  do escritório, `editar_escritorio`).
- Visualização da lista de honorários e dos valores (inclusive valor
  pendente corrigido) **não muda**: continua sob a autorização padrão
  do módulo Financeiro já em vigor (`MODULO_FINANCEIRO` +
  `_exige_nivel_dados`), sem novo gate de visibilidade.

## Regras obrigatórias

- Confirmar recebimento parcial sem `usuario_admin_escritorio` é
  bloqueado — mesma checagem hoje aplicada à confirmação total.
- Confirmação parcial nunca deixa `valor_recebido` exceder
  `valor_efetivo`.
- Cálculo de correção deve ser feito e testado no backend, nunca só no
  template — mesmo padrão já exigido para saldo de custas (PDR-0005).
- Honorário sem `taxa_mensal`/`data_termo` preenchidos não sofre
  nenhuma correção — comportamento idêntico ao anterior a este PDR.

## Consequências

- `docs/modules/financeiro.md`, seção Honorários, passa a registrar
  recebimento parcial e correção monetária/juros configurável.
- `docs/STATUS.md`, linha Financeiro, passa a registrar esse gap como
  resolvido.
- Migration em `Honorario` para os campos novos (`valor_recebido`,
  `taxa_mensal`, `data_termo`) e para o histórico de confirmações
  parciais — modelagem física é decisão de implementação.

## Fora do escopo desta decisão

- Integração com índice externo (INPC via IBGE, Selic via Bacen) —
  direção futura desejada, exige novo PDR.
- Qualquer distinção entre devedor pessoa física/jurídica comum e ente
  estatal para fins de fórmula de correção — não existe nesta versão,
  já que não há integração de índice externo.
- Qualquer novo perfil de acesso ("mestre" ou equivalente) — termo
  depreciado (`docs/PRODUCT.md`); a autorização usada é a já existente
  (`usuario_admin_escritorio`, `MODULO_FINANCEIRO`).
- Identificação automática de honorário por IA — PDR-0008.

## Critérios de aceite funcionais

- É possível confirmar dois ou mais recebimentos parciais do mesmo
  honorário até atingir o valor total, cada um gerando seu próprio
  lançamento de receita realizado.
- Um honorário com recebimento parcial permanece com status `previsto`
  até `valor_recebido` atingir `valor_efetivo`.
- Usuário sem `usuario_admin_escritorio` não consegue confirmar
  recebimento parcial nem alterar taxa/data-termo de correção, mesmo
  tendo acesso normal ao módulo Financeiro.
- Honorário com `taxa_mensal`/`data_termo` preenchidos exibe valor
  pendente corrigido; sem esses campos, comportamento idêntico ao
  anterior a este PDR.
- Cálculo de correção tem cobertura de teste automatizado no backend.

## Fontes

- Conversa desta sessão (protótipo `docs/prototipos/financeiro-prototipo.html`
  usado como referência de comportamento esperado, com o gate de
  visibilidade "mestre" e a integração INPC/Selic descartados por
  decisão desta sessão); spec
  `specs/financeiro-visao-grafica-navegacao-temporal.md` (apagada após a
  promoção deste PDR, conforme
  [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
