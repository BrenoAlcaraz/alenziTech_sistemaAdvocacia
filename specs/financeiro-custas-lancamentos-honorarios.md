# Spec — Financeiro: custas judiciais, lançamentos e honorários

## Objetivo

Corrigir a listagem de Custas Judiciais para mostrar todos os clientes,
separar os formulários de débito e crédito, padronizar a formatação
monetária, e alinhar a aba de Honorários ao protótipo.

## Comportamento esperado

- Filtros equivalentes aos do protótipo (`docs/prototipos/financeiro-prototipo.html`)
  em todas as listagens do módulo.
- Aba Custas Judiciais lista **todos os clientes ativos**, mesmo sem
  nenhum lançamento (hoje só aparece quem já tem histórico, porque a
  lista é montada a partir dos registros de `CustaJudicial` existentes) —
  saldo "sem saldo pendente" para quem ainda não tem nada.
- Card de saldo por cliente mostra nome + CPF/CNPJ (ou documento, se
  estrangeiro) — hoje mostra só o nome.
- Toda exibição de valor lançado no módulo segue o padrão `R$ 0.000,00`.
- Ação "Creditar" a partir do card de um cliente específico abre um
  formulário com Cliente pré-preenchido e Tipo travado em "Depósito do
  cliente" (sem permitir trocar).
- Formulário de "lançar débito" (nova custa) deixa de oferecer a opção
  "Depósito do cliente" no seletor de tipo — essa opção só existe pelo
  fluxo dedicado de "Creditar".
- Aba Honorários: revisar layout e comportamento para bater com
  `financeiro-prototipo.html`, mantendo o fluxo `previsto`/`recebido`/
  `cancelado` e as regras já aprovadas (PDR-0007/PDR-0022).

## Regras de negócio relevantes

- O cálculo do saldo de custas continua: `saldo = depósitos do cliente −
  custas adiantadas pelo escritório` (PDR-0005), sem mudança de fórmula —
  só de quais clientes aparecem na tela inicial.
- "Lançar débito" e "Creditar" passam a ser dois formulários distintos
  na interface (hoje reaproveitam o mesmo `CustaJudicialForm`); o model
  `CustaJudicial` continua único por trás dos dois.

## Fora de escopo

- Qualquer mudança no fluxo de aprovação de Solicitações Financeiras
  (PDR-0015).
- Integração bancária/conciliação automatizada.
- Exportação Excel.

## Critérios de aceite

- Aba Custas Judiciais lista todo cliente ativo, mesmo sem lançamento.
- Card de cliente na aba Custas Judiciais mostra nome e documento.
- Clicar em "Creditar" no card de um cliente abre o formulário com
  cliente e tipo já preenchidos e travados.
- Formulário de novo débito não mostra "Depósito do cliente" como opção
  de tipo.
- Nenhum valor monetário aparece sem o prefixo `R$` e a formatação
  brasileira em nenhuma tela do módulo.
