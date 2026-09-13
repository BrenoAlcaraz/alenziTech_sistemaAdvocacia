# Spec — Financeiro: visão gráfica e navegação temporal

## Objetivo

Fechar os gaps visuais do módulo Financeiro identificados contra o
protótipo (`docs/prototipos/financeiro-prototipo.html`): navegação por
mês, aba de gráfico, card de saldo em destaque, classificação
Única/Recorrente, anexos, tag de origem de solicitação com ação
inline, drill-down de custas por cliente, e recebimento parcial/
correção de honorários.

Duas decisões de produto que bloqueavam parte disso foram tomadas nesta
rodada e já estão registradas em PDR: periodicidades da recorrência
([PDR-0021](../docs/decisions/PDR-0021-periodicidades-financeiras.md))
e recebimento parcial/correção monetária de honorários
([PDR-0022](../docs/decisions/PDR-0022-honorarios-recebimento-parcial-correcao.md)).
`docs/modules/financeiro.md` e `docs/STATUS.md` já foram atualizados
com essas decisões.

## Comportamento esperado

### 1. Navegador de mês
- Pill fixo no topo da aba "Lançamentos": ◀ / rótulo "Mês de ano" / ▶,
  com tag "Mês atual" quando o mês exibido é o mês real de hoje.
- Estado `mes_referencia` (ano+mês) controla cards de resumo, lista de
  lançamentos e filtros — todos passam a filtrar por
  `data_vencimento`/data de ocorrência dentro do mês referência, não
  mais a visão consolidada de todos os períodos.

### 2. Aba "Gráfico"
- Nova aba ao lado de "Lançamentos"/"Custas Judiciais"/"Honorários".
- Gráfico de barras receita × despesa por mês (`status='pago'`,
  agregado por `data_pagamento`), com toggle "Últimos 6 meses" /
  "Últimos 12 meses" / "Exercício &lt;ano atual&gt;" mudando só o
  intervalo da mesma agregação.
- Cálculo de agregação no backend (view/service), nunca só no template.

### 3. Card "Saldo atual do mês" em destaque
- É o "saldo realizado" já definido em PDR-0004 (recebido no mês −
  pago no mês), exibido como card destacado entre os já existentes —
  não é um número novo, é apresentação.
- Grid de cards passa de 5 para 6, mantendo os já existentes (a
  receber, a pagar, recebido no mês, pago no mês, saldo previsto).

### 4. Classificação Única/Recorrente (PDR-0021)
- Bloco no formulário de lançamento: toggle Única/Recorrente.
- Recorrente exibe periodicidade (mensal/anual), dia de
  vencimento/mês de referência e duração (nº de ocorrências, data
  final, ou indeterminado) — conforme já descrito em
  `docs/modules/financeiro.md`.
- Cancelar a recorrência futura não apaga nem reescreve ocorrências já
  geradas (regra já registrada em PRODUCT, agora com UI).

### 5. Upload de anexo (boleto/comprovante)
- `LancamentoFinanceiro` ganha campo de anexo (boleto e/ou comprovante,
  storage protegido por tenant — mesmo padrão de
  `SolicitacaoFinanceira.anexo`), exibido/anexável na lista.
- `CustaJudicial` ganha o mesmo campo — gap já previsto em PDR-0005
  ("boleto e comprovante, quando aplicável") e ainda não implementado.
- Confirmar pagamento de uma solicitação (`avancar_para("paga")`)
  passa a poder anexar comprovante no mesmo passo.

### 6. Tag de origem "SOLICITADO POR [nome]" + ação inline
- Lançamento originado de `SolicitacaoFinanceira` (via
  `solicitacao_origem`) exibe a tag "SOLICITADO POR &lt;solicitante&gt;"
  na lista de lançamentos.
- Ação inline: anexar comprovante/boleto direto da linha do
  lançamento, sem navegar para tela de detalhe da solicitação.

### 7. Custas Judiciais: drill-down por cliente
- Linha de cliente na lista de custas passa a ser clicável, abrindo
  extrato/conta-corrente do cliente: abas "Lançamentos" (custas pagas,
  por escritório ou pelo próprio cliente) e "Creditar" (depósitos do
  cliente), com o saldo (PDR-0005) em destaque no topo.
- Reaproveita `CustaJudicial` e o modelo de crédito do cliente já
  previsto em PDR-0005 — sem tabela nova de "extrato", é a mesma
  listagem já filtrada por cliente.

### 8. Honorários: recebimento parcial + correção (PDR-0022)
- Ver critérios de aceite funcionais do PDR-0022 — cadastro de
  `taxa_mensal`/`data_termo` opcionais, múltiplas confirmações de
  recebimento parcial, `valor_recebido` acumulado, autorização
  inalterada (Administrador do escritório).

## Regras de negócio relevantes

- PDR-0004 (previsto/realizado), PDR-0005 (saldo de custas por
  cliente), PDR-0006/PDR-0015 (fluxo de solicitações), PDR-0007/
  PDR-0022 (honorários), PDR-0021 (periodicidades) — nenhuma regra
  nova além do que já está nesses documentos; esta spec é só o plano de
  UI/implementação que fecha o gap contra eles.

## Fora do escopo

- Integração com índice externo (INPC/Selic) para correção de
  honorários — PDR-0022 já registra como direção futura.
- Qualquer perfil de acesso novo ("mestre" ou equivalente) — termo
  depreciado, não usado.
- Exportação Excel, relatórios além do gráfico receita×despesa,
  integração bancária/conciliação — continuam fora de escopo
  (`docs/modules/financeiro.md`).
- Geração automática de prazo/andamento — módulo Agenda, spec própria.

## Critérios de aceite

- Navegar entre meses atualiza cards, lista e filtros sem recarregar
  dados de outros meses; tag "Mês atual" só aparece no mês real.
- Aba Gráfico mostra barras receita/despesa por mês e o toggle de
  período muda o intervalo sem alterar a query base.
- Grid de cards mostra 6 cards, incluindo "Saldo atual do mês" em
  destaque, com o mesmo valor de "saldo realizado" (PDR-0004).
- Lançamento recorrente com periodicidade mensal/anual gera ocorrências
  futuras individuais; cancelar a recorrência não afeta ocorrências já
  geradas; periodicidade fora de mensal/anual/parcelamento mensal é
  rejeitada.
- É possível anexar boleto/comprovante a um lançamento e a uma custa
  judicial; anexo é acessível só via storage protegido do tenant.
- Lançamento originado de solicitação exibe "SOLICITADO POR
  &lt;nome&gt;" e permite anexar comprovante direto da lista.
- Clicar num cliente na lista de custas abre o extrato com saldo,
  histórico de custas e de créditos; saldo bate com a fórmula do
  PDR-0005 e é calculado no backend.
- Honorário aceita duas ou mais confirmações parciais até
  `valor_recebido` atingir `valor_efetivo`; sem `usuario_admin_escritorio`,
  confirmar parcial e editar correção são bloqueados; honorário sem
  taxa/data-termo não sofre correção (comportamento anterior
  preservado).

## Plano de execução sugerido (tickets)

Unidades independentes o suficiente para tickets separados — sequência
sugerida, sem dependência forte entre elas exceto onde indicado:

1. Navegador de mês (depende de nada; toca cards e lista existentes).
2. Card "Saldo atual do mês" em destaque (trivial, pode ir junto do 1).
3. Classificação Única/Recorrente (PDR-0021) — migration em
   `LancamentoFinanceiro`.
4. Anexo em `LancamentoFinanceiro`/`CustaJudicial` + ação inline de
   anexar em solicitação paga.
5. Tag "SOLICITADO POR" (depende do anexo do item 4 para a ação
   inline, mas a tag em si não depende).
6. Aba "Gráfico" (independente, só precisa da agregação mensal já
   existente nos cards).
7. Custas Judiciais: drill-down por cliente (independente).
8. Honorários: recebimento parcial + correção monetária (PDR-0022) —
   migration em `Honorario`.
