---
title: Financeiro
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
related_pdrs:
  - PDR-0003
  - PDR-0004
  - PDR-0005
  - PDR-0006
  - PDR-0007
  - PDR-0009
---

# Financeiro

## Objetivo

Controlar as operações financeiras do escritório, distinguindo caixa
operacional, custas judiciais, solicitações financeiras e honorários,
com separação entre valores previstos e realizados.

## Escopo funcional

O Financeiro reúne quatro áreas funcionais relacionadas entre si, mas
distintas:

1. financeiro geral do escritório;
2. custas judiciais;
3. solicitações de pagamento e reembolso;
4. honorários advocatícios.

As áreas podem compartilhar vínculos com cliente, processo, documentos
e eventos de realização financeira, mas mantêm regras e ciclos de vida
próprios, e não devem ser tratadas como um único tipo genérico de
lançamento. Conforme [PDR-0003](../decisions/PDR-0003-areas-funcionais-financeiro.md),
esta especificação não determina quantas tabelas ou models existirão
para representar essas áreas; a modelagem física pertence à
arquitetura e à implementação.

## Atores e expectativas de acesso

- Administrador do escritório possui expectativa de supervisão do
  Financeiro dentro do tenant.
- Usuários com habilitação financeira podem acessar e processar as
  áreas autorizadas.
- Usuários sem acesso ao caixa geral possuem visão limitada,
  restrita às suas próprias solicitações de pagamento e reembolso.
- Usuários sem autorização financeira não podem visualizar receitas,
  despesas ou resultados completos do escritório.
- O alcance exato dos papéis e habilitações financeiras será definido
  na futura matriz de autorização, em `docs/security/`, ainda não
  criado.
- Autorização deve ser aplicada no backend; ocultar ou exibir
  elementos de interface não substitui essa verificação.

Esta especificação não cria um papel de acesso fixo dedicado
exclusivamente ao Financeiro: a habilitação financeira é aplicada por
papel de acesso, habilitação e escopo, não como um grupo predefinido.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Financeiro": financeiro
geral, custa judicial, solicitação de pagamento, solicitação de
reembolso, honorário, lançamento único, lançamento parcelado,
lançamento recorrente, ocorrência, competência, vencimento, previsto,
realizado, saldo realizado, saldo previsto e crédito de custas. Este
documento não redefine esses termos.

## Regras funcionais

### Financeiro geral

- Representa receitas e despesas operacionais do escritório.
- Custas processuais não são uma categoria comum do financeiro geral;
  pertencem à área específica de custas judiciais.
- As categorias de receita e de despesa disponíveis são condicionadas
  ao tipo do lançamento: categorias de despesa não aparecem para um
  lançamento de receita, e vice-versa.
- Todo lançamento segue uma das três modalidades:
  - único;
  - parcelado;
  - recorrente.
- Um lançamento parcelado possui quantidade de parcelas, periodicidade
  e primeiro vencimento; o sistema gera ocorrências individuais
  vinculadas à mesma origem.
- Um lançamento recorrente possui periodicidade e primeiro vencimento,
  e pode ter duração determinada, data final ou prazo indeterminado.
- Cada ocorrência recorrente nasce como um lançamento individual
  ligado à mesma origem, inicialmente pendente, salvo quando registrada
  como já realizada, conforme a seção "Previsto e realizado" abaixo.
- Cancelar uma recorrência impede apenas as gerações futuras.
- Cancelar uma recorrência não apaga nem reescreve ocorrências já
  realizadas.
- A confirmação ou o cancelamento de uma ocorrência não reescreve as
  demais ocorrências da mesma origem.

As periodicidades específicas disponíveis na primeira versão não são
definidas por esta especificação; ver
[OPEN-001](../open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão).

### Previsto e realizado

- Uma pendência entra em contas a pagar ou a receber, conforme o tipo
  do lançamento.
- Uma pendência não altera o caixa realizado.
- Somente a confirmação efetiva de pagamento ou recebimento altera o
  saldo realizado.
- O painel financeiro apresenta, no mínimo, os seguintes indicadores:
  - a receber;
  - a pagar;
  - recebido no período;
  - pago no período;
  - saldo realizado;
  - saldo previsto.
- Todo lançamento possui data de competência.
- Um lançamento pendente, uma parcela e uma ocorrência recorrente
  possuem vencimento.
- Um item pago possui data de pagamento; um item recebido possui data
  de recebimento.
- O vencimento pode não se aplicar a um item já realizado, desde que
  existam competência e data de realização suficientes para
  posicioná-lo corretamente nos períodos.

### Custas judiciais

- Área separada do caixa geral do escritório.
- A tela inicial lista os clientes e o saldo de custas de cada um.
- Cada cliente possui histórico de créditos depositados e de
  lançamentos de custas.
- Um lançamento de custa pode relacionar cliente e processo, e
  registra descrição, valor, data, responsável pelo pagamento, boleto
  e comprovante, quando aplicável.
- O responsável pelo pagamento de uma custa pode ser o escritório ou
  o cliente.

A fórmula do saldo de custas é:

```
saldo de custas =
  créditos depositados pelo cliente
  − custas pagas pelo escritório
```

- Uma custa paga diretamente pelo cliente aparece no histórico do
  cliente, para fins de controle.
- Uma custa paga diretamente pelo cliente não reduz o crédito mantido
  pelo escritório.
- Uma custa paga diretamente pelo cliente não altera o saldo entre
  cliente e escritório.
- O cálculo do saldo de custas deve ser feito e testado no backend,
  não apenas apresentado ou calculado no template.

### Solicitações financeiras

**Solicitação de pagamento** — campos: descrição, valor, cliente,
processo, vencimento, boleto obrigatório, observação.

**Solicitação de reembolso** — campos: descrição, valor, cliente e
processo quando aplicáveis, comprovante obrigatório, data do gasto,
observação.

Fluxo de referência:

```
solicitada → em análise → aprovada ou rejeitada → paga
```

- O detalhamento final desse fluxo depende de
  [OPEN-002](../open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras);
  esta especificação não resolve esse ponto.
- O solicitante acompanha o status da própria solicitação.
- Após o pagamento, o solicitante visualiza o comprovante anexado
  pelo Financeiro.
- Administrador do escritório e usuário com habilitação financeira
  podem processar solicitações.
- A criação de uma solicitação não gera automaticamente uma despesa
  realizada.
- O saldo realizado só se altera quando o pagamento é efetivamente
  processado.
- O momento exato em que uma solicitação passa a compor o indicador
  "a pagar" não é decidido por esta especificação.

### Honorários

- Cadastro manual, anterior a qualquer funcionalidade de IA.
- Um honorário pode se relacionar a processo e, quando aplicável, a
  cliente.
- Campos: tipo, valor estimado, valor efetivo, processo, cliente
  (quando aplicável), data prevista, data recebida, status e
  observações.
- A IA jurídica futura pode identificar honorários em documentos e
  sugerir um cadastro correspondente, conforme
  [inteligencia-artificial.md](inteligencia-artificial.md).
- A sugestão de IA não substitui a confirmação humana do cadastro.

## Fluxos principais

1. Registrar lançamento único.
2. Registrar lançamento parcelado.
3. Registrar recorrência.
4. Confirmar pagamento ou recebimento.
5. Cancelar recorrência futura.
6. Creditar saldo de custas de um cliente.
7. Registrar custa paga pelo escritório.
8. Registrar custa paga diretamente pelo cliente.
9. Criar solicitação de pagamento.
10. Criar solicitação de reembolso.
11. Processar solicitação.
12. Cadastrar honorário manualmente.

## Integrações e dependências

- Depende do módulo Clientes para relacionar custas, solicitações e
  honorários a um cliente, conforme [clientes.md](clientes.md).
- Depende do módulo Processos para relacionar custas, solicitações e
  honorários a um processo, conforme [processos.md](processos.md).
- Fornece indicadores financeiros consumidos pelo módulo Dashboard,
  conforme [dashboard.md](dashboard.md) e PDR-0004.
- A relação entre a assinatura da plataforma SaaS e o Financeiro do
  tenant depende de
  [OPEN-003](../open-decisions.md#open-003--espelhamento-da-assinatura-saas-no-financeiro),
  tratada também em [configuracoes.md](configuracoes.md).
- A integração futura entre honorários e IA jurídica depende dos
  pré-requisitos descritos em
  [inteligencia-artificial.md](inteligencia-artificial.md).

## Fora do escopo imediato

- Identificação automática de honorários por IA, até que os
  pré-requisitos de
  [PDR-0008](../decisions/PDR-0008-ia-apos-nucleo-funcional.md)
  estejam consolidados.
- Qualquer integração automática entre a cobrança da assinatura SaaS e
  o financeiro do tenant, enquanto OPEN-003 não for decidido.
- Gráficos, relatórios ou exportações financeiras além dos indicadores
  mínimos definidos em PDR-0004.
- Integrações bancárias, emissão de boletos por API ou conciliação
  bancária automatizada.

## Pontos em aberto

- [OPEN-001](../open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão)
  — periodicidades financeiras da primeira versão.
- [OPEN-002](../open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras)
  — fluxo final de aprovação das solicitações financeiras.
- [OPEN-003](../open-decisions.md#open-003--espelhamento-da-assinatura-saas-no-financeiro)
  — espelhamento da assinatura SaaS no Financeiro.
- Lista inicial de categorias de receita e de despesa.
- Regras detalhadas de anexos no financeiro geral.
- Alcance exato dos papéis e habilitações financeiras.
- Momento exato em que uma solicitação passa a compor o indicador "a
  pagar".

## Critérios de aceite funcionais

- O Financeiro trata financeiro geral, custas judiciais, solicitações
  de pagamento/reembolso e honorários como áreas funcionais distintas.
- Custas processuais não aparecem como opção de categoria dentro do
  financeiro geral.
- Um lançamento pode ser registrado como único, parcelado ou
  recorrente.
- Uma pendência não altera o saldo realizado; somente a confirmação de
  pagamento ou recebimento o altera.
- O painel financeiro exibe, no mínimo, a receber, a pagar, recebido
  no período, pago no período, saldo realizado e saldo previsto.
- O saldo de custas de um cliente é igual aos créditos depositados por
  ele menos as custas pagas pelo escritório em seu nome.
- Uma custa paga diretamente pelo cliente aparece no histórico do
  cliente, mas não altera o saldo de custas calculado.
- Um usuário sem acesso ao caixa geral consegue criar solicitação de
  pagamento ou de reembolso, sem visualizar receitas, despesas ou
  resultados completos do escritório.
- Criar uma solicitação não altera indicadores de despesa realizada; a
  despesa só se torna realizada quando o pagamento é efetivamente
  processado.
- É possível cadastrar um honorário manualmente, sem depender de
  nenhuma funcionalidade de IA.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0003 — Áreas funcionais do Financeiro](../decisions/PDR-0003-areas-funcionais-financeiro.md)
- [PDR-0004 — Previsto e realizado](../decisions/PDR-0004-previsto-e-realizado.md)
- [PDR-0005 — Custas por cliente](../decisions/PDR-0005-custas-por-cliente.md)
- [PDR-0006 — Solicitações financeiras](../decisions/PDR-0006-solicitacoes-financeiras.md)
- [PDR-0007 — Honorários manuais antes da IA](../decisions/PDR-0007-honorarios-manuais-antes-ia.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Decisões de produto em aberto](../open-decisions.md)
- [Política de terminologia](../../governance/terminology-policy.md)
