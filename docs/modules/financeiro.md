# Módulo — Financeiro

Quatro áreas distintas, com regras e ciclos de vida próprios — nunca
tratar como um único tipo genérico de lançamento (PDR-0003). A
especificação não determina quantas tabelas existirão; modelagem física
é decisão de arquitetura/implementação.

## Financeiro geral

- Todo lançamento é único, parcelado ou recorrente.
- Parcelado: quantidade de parcelas + periodicidade + primeiro
  vencimento → gera ocorrências individuais vinculadas à mesma origem.
- Recorrente: periodicidade + primeiro vencimento, duração/data
  final/indeterminado. Cada ocorrência nasce como lançamento
  individual ligado à origem.
- Cancelar recorrência futura não apaga nem reescreve ocorrências já
  realizadas; confirmar/cancelar uma ocorrência não reescreve as demais.
- Custas processuais não são categoria do financeiro geral — têm área
  própria.
- Periodicidades disponíveis na primeira versão: **em aberto**, ver
  [OPEN-001](../STATUS.md#decisões-em-aberto).

## Previsto e realizado (PDR-0004)

- Pendência entra em "a pagar"/"a receber" mas não altera o saldo
  realizado. Só a confirmação efetiva de pagamento/recebimento altera
  o saldo realizado.
- Painel mínimo: a receber, a pagar, recebido no período, pago no
  período, saldo realizado, saldo previsto.
- Todo lançamento tem competência; pendência/parcela/ocorrência tem
  vencimento (pode não se aplicar a item já realizado, se competência
  e data de realização já posicionam o item corretamente).

## Custas judiciais (PDR-0005)

- Área separada do caixa geral. Tela inicial lista clientes e saldo de
  custas de cada um.

```
saldo de custas = créditos depositados pelo cliente − custas pagas pelo escritório
```

- Custa paga diretamente pelo cliente aparece no histórico do cliente
  mas não reduz o crédito nem altera o saldo calculado.
- Cálculo do saldo deve ser feito e testado no backend, nunca só
  no template.

## Solicitações financeiras (PDR-0006, fluxo em PDR-0015)

- Pagamento: descrição, valor, cliente, processo, vencimento, boleto
  obrigatório, observação.
- Reembolso: descrição, valor, cliente/processo quando aplicável,
  comprovante obrigatório, data do gasto, observação.
- Fluxo: `solicitada → em análise → aprovada → paga`, ou
  `solicitada → em análise → rejeitada` — sem pular etapa.
- Criar solicitação não gera despesa realizada; só o pagamento
  efetivamente processado altera o saldo realizado.
- Reabrir lançamento pago exige habilitação própria; ao reabrir, o
  advogado responsável pela solicitação original é notificado.

## Honorários (PDR-0007)

- Cadastro manual, anterior a qualquer IA. Campos: tipo, valor
  estimado, valor efetivo, processo, cliente (quando aplicável), data
  prevista, data recebida, status, observações.
- IA jurídica futura pode sugerir honorário identificado em documento —
  sugestão nunca vira registro sem confirmação humana.
- Confirmar recebimento é exclusivo do Administrador do escritório; ao
  confirmar, o advogado responsável pelo processo é notificado (não
  confirma ele mesmo).

## Relação com billing SaaS

`saas_billing` (Plano/Assinatura) e o Financeiro do tenant são domínios
distintos (PDR-0003) — sem espelhamento automático da assinatura como
despesa. Integração futura mais ampla exigiria novo PDR.

## Fora de escopo imediato

- identificação automática de honorário por IA antes dos pré-requisitos
  de PDR-0008;
- integração automática billing↔financeiro do tenant;
- gráficos/relatórios além do painel mínimo e exportação Excel opcional;
- integração bancária, boleto por API, conciliação automatizada.

## Referências

- [PDR-0003](../decisions/PDR-0003-areas-funcionais-financeiro.md) — áreas funcionais
- [PDR-0004](../decisions/PDR-0004-previsto-e-realizado.md) — previsto/realizado
- [PDR-0005](../decisions/PDR-0005-custas-por-cliente.md) — custas por cliente
- [PDR-0006](../decisions/PDR-0006-solicitacoes-financeiras.md) — solicitações
- [PDR-0007](../decisions/PDR-0007-honorarios-manuais-antes-ia.md) — honorários
- [PDR-0015](../decisions/PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md) — fluxo de aprovação
- [STATUS.md](../STATUS.md#financeiro) para o estado real de implementação
