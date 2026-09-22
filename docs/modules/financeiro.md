# Módulo — Financeiro

Quatro áreas distintas, com regras e ciclos de vida próprios — nunca
tratar como um único tipo genérico de lançamento (PDR-0003). A
especificação não determina quantas tabelas existirão; modelagem física
é decisão de arquitetura/implementação.

## Financeiro geral

- Todo lançamento é único, parcelado ou recorrente.
- Parcelado: quantidade de parcelas + primeiro vencimento → gera
  ocorrências individuais vinculadas à mesma origem. O valor digitado é
  o total a parcelar; o sistema divide igualmente entre as parcelas
  (arredondado ao centavo), e a última parcela absorve o resíduo do
  arredondamento, para a soma bater exatamente com o total — mesma
  convenção do honorário contratual parcelado (PDR-0032). As parcelas
  seguintes vencem no mesmo dia dos meses seguintes (mês sem esse dia →
  último dia do mês, sem "derivar" nas parcelas posteriores: 31/01 →
  28/02 → 31/03). Só a 1ª pode nascer paga; as demais nascem sempre
  pendentes.
- Recorrente: periodicidade + primeiro vencimento, duração/data
  final/indeterminado. Cada ocorrência nasce como lançamento
  individual ligado à origem.
- Cancelar recorrência futura não apaga nem reescreve ocorrências já
  realizadas; confirmar/cancelar uma ocorrência não reescreve as demais.
- Custas processuais não são categoria do financeiro geral — têm área
  própria.
- Periodicidades disponíveis na primeira versão (PDR-0021): mensal ou
  anual para recorrente; parcelado sempre com periodicidade mensal
  entre parcelas. Semanal/quinzenal/trimestral/semestral/personalizada
  ficam fora desta versão.
- Navegação por mês: a lista de lançamentos e os cards de resumo são
  sempre referentes a um mês por vez (navegador ◀▶ + indicação de "mês
  atual"), nunca a visão consolidada de todos os períodos.
- Filtros da aba Lançamentos (reunião de 13/09): Todos, Receitas,
  Despesas, Pagos (despesas pagas), Recebidos (receitas pagas), A pagar
  (despesas pendentes), A receber (receitas pendentes), Atrasados,
  Pagamentos solicitados (lançamento originado de uma Solicitação
  Financeira) — mesmo conjunto do protótipo.

- Categoria acompanha o tipo; o backend recusa a combinação inválida.
  Receita: honorários, honorários de sucumbência, reembolso, consultoria,
  comissão, auditoria, acordo, capacitação, outros. Despesa: aluguel,
  condomínio, água, luz, internet, salário, bonificação, impostos/taxas,
  cursos, equipamentos, material, software/assinatura, outros.
  Categorias geradas só pelo sistema (custa judicial, solicitação de
  pagamento, êxito etc.) não aparecem no dropdown manual e mantêm o
  rótulo na listagem; lançamento existente com uma delas continua
  editável sem trocar de categoria.
- Formulário de lançamento: "Classificação" (Única/Parcelado/Recorrente)
  logo abaixo de valor e categoria. Data de pagamento e comprovante só
  existem com status Pago (backend descarta a data e recusa o
  comprovante nos demais status); com Pago, o comprovante é opcional e,
  em parcelado/recorrente, vale só para a 1ª ocorrência.
- Saldo previsto = a receber + recebido − a pagar − pagos (PDR-0029).
- Reembolso de cliente e custas do cliente não são receita/despesa —
  ver [PDR-0029](../decisions/PDR-0029-financeiro-liquido-de-custas-e-honorario-calculado.md).

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

- Área separada do caixa geral. Tela inicial lista **todo cliente
  ativo** (mesmo sem nenhum lançamento ainda — corrigido na reunião de
  13/09; antes só listava quem já tinha `CustaJudicial`), com nome e
  documento (CPF/CNPJ ou outro, se estrangeiro), e o saldo de custas de
  cada um.

```
saldo de custas = créditos depositados pelo cliente − custas pagas pelo escritório
```

- Custa paga diretamente pelo cliente aparece no histórico do cliente
  mas não reduz o crédito nem altera o saldo calculado.
- Cálculo do saldo deve ser feito e testado no backend, nunca só
  no template.
- Lançar débito (custa adiantada pelo escritório ou paga diretamente
  pelo cliente) e Creditar (depósito do cliente) são dois formulários
  distintos na interface (reunião de 13/09) — o formulário de débito
  nunca oferece "Depósito do cliente" como tipo; o de Creditar não
  expõe Cliente nem Tipo como campo, os dois vêm do próprio contexto da
  rota (`financeiro/custas/cliente/<id>/creditar/`), nunca do que foi
  submetido. O model `CustaJudicial` continua único por trás dos dois.
- **Grupos de clientes** ([PDR-0031](../decisions/PDR-0031-custas-por-grupo-de-clientes.md)):
  grupo com nome e membros, saldo próprio pela mesma fórmula. Cliente em
  no máximo um grupo, só entra com saldo individual zero, some da lista
  individual e aparece dentro do grupo (extrato, Creditar, Membros).
  Débito no grupo exige o membro (processo opcional, só de membro) e
  aparece na ficha do membro como "pago pelo saldo do Grupo X", sem
  afetar o saldo individual. Remover membro/apagar grupo só sem
  lançamentos vinculados.
- Tela de custas: busca (cliente, documento, grupo, membros) e filtro de
  saldo (com crédito / em débito / sem saldo pendente). Formulário de
  débito "Adiantado pelo escritório" mostra saldo atual e após o débito,
  inclusive negativo (informativo).

## Solicitações financeiras (PDR-0006, fluxo em PDR-0015)

- Pagamento: descrição, valor, cliente, processo, vencimento, boleto
  obrigatório, observação.
- Reembolso: descrição, valor, cliente/processo quando aplicável,
  comprovante obrigatório, data do gasto, observação.
- Fluxo: `solicitada → em análise → aprovada → paga`, ou
  `solicitada → em análise → rejeitada` — sem pular etapa.
- Cor do estado, igual em todas as telas que mostram a solicitação
  (lista e detalhe do Financeiro, aba "Custas Judiciais" do processo):
  solicitada e em análise amarelo, aprovada azul, rejeitada vermelho,
  paga verde. Os cards de lista/aba levam também uma faixa lateral na
  cor do estado.
- "Vencida": etiqueta vermelha ao lado do estado quando a solicitação
  está aberta (`solicitada`, `em_analise` ou `aprovada`) e o vencimento
  é anterior a hoje. Vencimento é opcional — sem data nunca é vencida;
  vencimento hoje não é vencida; `paga` e `rejeitada` nunca são vencidas.
- Contagem na barra de abas: "Solicitações (n)" mostra o total do
  escritório (todos os solicitantes, pagamento e reembolso) em estado
  aberto (`solicitada`, `em_analise` ou `aprovada`); `rejeitada` e `paga`
  não contam. Sempre exibida — cinza quando 0, amarelo quando maior que 0.
  A barra só existe para quem tem acesso ao caixa geral, então o número
  nunca chega a quem só tem nível `solicitacoes`.
- Criar solicitação não gera despesa realizada; só o pagamento
  efetivamente processado altera o saldo realizado.
- Reabrir lançamento pago exige habilitação própria; ao reabrir, o
  advogado responsável pela solicitação original é notificado.
- Solicitação vinculada a um processo também aparece na aba "Custas
  Judiciais" do detalhe desse processo (`docs/modules/processos.md`),
  visível a qualquer usuário do processo — sem o filtro por
  `solicitante` que a aba "Solicitações" deste módulo aplica para quem
  não tem `dados_proprios`/`dados_todos`. É a mesma linha de
  `SolicitacaoFinanceira`, só uma segunda visão sem esse filtro.
- Solicitação nascida do "+ Nova solicitação" da aba Custas Judiciais de
  um processo (`?processo=<id>`) sempre nasce `tipo="pagamento"` —
  campo travado, sem opção de virar reembolso — e com processo/cliente
  pré-preenchidos a partir do processo de origem, também travados (só
  ficam escolhíveis entre os clientes do próprio processo quando ele tem
  mais de um vinculado). O formulário sem esse parâmetro continua livre
  (pagamento ou reembolso, qualquer cliente/processo), igual ao "+ Nova
  solicitação" do próprio módulo Financeiro. Nesse caminho o link carrega
  a origem (`next`, mesmo mecanismo genérico de retorno já usado entre
  `processos` e `tarefas`); voltar, cancelar ou salvar com sucesso
  devolvem ao processo de origem (`processos/<id>/?aba=custas`) em vez
  da lista geral de solicitações. Sem essa origem, o formulário continua
  voltando/cancelando/salvando para `financeiro/solicitacoes`, como
  antes.
- Solicitação editável (descrição, valor, tipo, cliente, processo,
  vencimento, data do gasto, anexo, observação) enquanto `status` for
  `solicitada` ou `em análise` — a partir de `aprovada`, `rejeitada` ou
  `paga`, edição bloqueada (inclusive por URL direta, não só escondendo o
  botão). Reaproveita o mesmo formulário e trava de tipo/processo/cliente
  da criação a partir da aba Custas Judiciais; essa trava só se aplica se
  o cliente já salvo ainda pertencer ao processo (o processo pode ter
  perdido esse cliente depois de a solicitação criada — nesse caso o
  formulário volta a ficar livre em vez de reatribuir o cliente
  silenciosamente).
- Marcar uma solicitação de `tipo="pagamento"` como "paga" exige
  informar se a custa foi paga pelo escritório ou diretamente pelo
  cliente, e anexar o comprovante de pagamento (campo próprio, separado
  do anexo enviado na criação da solicitação, que serve de boleto).
  Reembolso não passa por essa exigência. Ao confirmar, o pagamento é
  replicado como um `CustaJudicial` do cliente (PDR-0005, abaixo): "paga
  pelo escritório" vira `adiantamento` (débito que entra no saldo a
  cobrar do cliente), "paga pelo cliente" vira `paga_pelo_cliente`
  (só histórico, sem afetar o saldo) — mesmo efeito do lançamento manual
  equivalente na aba Custas Judiciais do Financeiro.

- Reembolso de custa adiantada pelo escritório: botão na custa, com
  comprovante; gera o crédito do cliente e a custa fica "reembolsada".
- Extrato do cliente filtra por processo e "pago por" (escritório ou
  cliente).
- Solicitações: lista dividida em Pendentes/Pagas/Rejeitadas, com
  filtros de cliente, processo, solicitado por e pagamento realizado
  por (só para quem vê todos os dados) e datas de solicitação/pagamento.
  Reembolso não tem vencimento, pagamento não tem data do gasto, e o
  processo é opcional nos dois.

## Honorários (PDR-0007, recebimento parcial e correção em PDR-0022)

- Cadastro manual, anterior a qualquer IA. Campos: tipo, valor
  estimado, valor efetivo, processo, cliente (quando aplicável), data
  prevista, data recebida, status, observações.
- IA jurídica futura pode sugerir honorário identificado em documento —
  sugestão nunca vira registro sem confirmação humana.
- Confirmar recebimento é exclusivo do Administrador do escritório; ao
  confirmar, o advogado responsável pelo processo é notificado (não
  confirma ele mesmo). Regra vale igualmente para confirmação parcial.
- Recebimento pode ser parcial: cada confirmação soma em
  `valor_recebido`, gera seu próprio lançamento de receita realizada, e
  o honorário só passa a `recebido` quando `valor_recebido` atingir
  `valor_efetivo`.
- Correção monetária/juros é opcional por honorário, com taxa mensal e
  data-termo informadas manualmente no cadastro (sem integração com
  índice externo nesta versão) — editar essa configuração é exclusivo
  do Administrador do escritório, mesma restrição da confirmação de
  recebimento.

- Honorário sucumbencial (PDR-0029, ajustado pelo PDR-0032): valor fixo,
  percentual sobre a condenação ou fixo + percentual; devedor pessoa/ente
  estatal; índice (INPC, IGP-M, Selic, IPCA) com taxa mensal informada à
  mão; juros e correção com data inicial e final de incidência (final
  vazia = até hoje); total recalculado a cada leitura.
- Tipos ([PDR-0032](../decisions/PDR-0032-honorarios-contratual-sucumbencia-ipca.md)):
  só Contratual e Sucumbência se criam; `exito`/`outro` antigos seguem
  editáveis.
- Contratual: "valor", "por êxito" ou "valor + êxito" no mesmo registro.
  Valor único, parcelado ou recorrente; parcelado e recorrente geram
  receitas pendentes (categoria Honorários) vinculadas ao honorário, pelo
  gerador do PDR-0021 — recebidas nos lançamentos, não pela confirmação
  do honorário. Êxito: percentual + base (pelo ganho/pela economia),
  processo obrigatório, só anotação (sem lançamento nem valor calculado).
- Aviso de êxito: a sucumbência mostra "Você tem X% de êxito a receber"
  por contrato "pelo ganho" do mesmo processo, sobre a condenação
  corrigida, somado ao total a receber; "pela economia" não entra.

## Relação com billing SaaS

`saas_billing` (Plano/Assinatura) e o Financeiro do tenant são domínios
distintos (PDR-0003) — sem espelhamento automático da assinatura como
despesa. Integração futura mais ampla exigiria novo PDR.

## Análise de dados (antes "Visão gráfica")

- Aba "Análise de dados": gráfico de barras receita × despesa por mês, com
  toggle de período (últimos 6 meses, últimos 12 meses, exercício
  corrente) — mesma fonte de dados dos cards de resumo, agregada por
  mês em vez de por lançamento individual. Abaixo, fontes de receita, fontes
  de despesa (somadas por categoria, só o realizado, respeitando o escopo
  `dados_proprios`/`dados_todos`), receita por área de atuação (área do processo) e por cliente,
  filtráveis por Sempre / Últimos 12 meses / Exercício deste ano.

## Fora de escopo imediato

- identificação automática de honorário por IA antes dos pré-requisitos
  de PDR-0008;
- integração automática billing↔financeiro do tenant;
- exportação Excel opcional;
- relatórios além do painel mínimo e do gráfico receita×despesa;
- integração bancária, boleto por API, conciliação automatizada;
- integração com índice externo (INPC/Selic/IPCA) para correção monetária
  de honorários (PDR-0022, PDR-0032).

## Referências

- [PDR-0003](../decisions/PDR-0003-areas-funcionais-financeiro.md) — áreas funcionais
- [PDR-0004](../decisions/PDR-0004-previsto-e-realizado.md) — previsto/realizado
- [PDR-0005](../decisions/PDR-0005-custas-por-cliente.md) — custas por cliente
- [PDR-0006](../decisions/PDR-0006-solicitacoes-financeiras.md) — solicitações
- [PDR-0007](../decisions/PDR-0007-honorarios-manuais-antes-ia.md) — honorários
- [PDR-0015](../decisions/PDR-0015-fluxo-aprovacao-solicitacoes-financeiras.md) — fluxo de aprovação
- [PDR-0021](../decisions/PDR-0021-periodicidades-financeiras.md) — periodicidades da recorrência
- [PDR-0022](../decisions/PDR-0022-honorarios-recebimento-parcial-correcao.md) — honorários: parcial e correção
- [PDR-0032](../decisions/PDR-0032-honorarios-contratual-sucumbencia-ipca.md) — honorários: contratual, sucumbência, êxito e IPCA
- [STATUS.md](../STATUS.md#financeiro) para o estado real de implementação
