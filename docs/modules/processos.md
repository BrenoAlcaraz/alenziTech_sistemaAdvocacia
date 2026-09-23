# Módulo — Processos

Processos judiciais e casos extrajudiciais: dados, participantes,
documentos, andamentos, vínculos, prazos, apensos. Arquivo próprio por
volume real de decisão (PDR-0001, 0010, 0012, 0013, 0014, 0023, 0024) —
ver [PRODUCT.md](../PRODUCT.md) para o padrão dos módulos mais simples.

## Autorização e responsabilidade (PDR-0010, PDR-0014, PDR-0017)

- Módulo `processos` habilitado é pré-requisito para todas as
  operações existentes. Além disso, `processos_criar`,
  `processos_editar` e `processos_andamento_adicionar` já são
  habilitações granulares aplicadas (PDR-0017), condicionando
  respectivamente `novo`, `editar` e `adicionar_movimentacao`.
  `processos_usar_laboratorio` condiciona a aba "Laboratório Jurídico"
  da tela de Processos (`processos:lista?aba=laboratorio`, módulo
  `processos` mais a habilitação, mesmo padrão de duas camadas); sem a
  habilitação a aba não aparece e o acesso direto é negado. A rota
  antiga `/laboratorio/` só redireciona para a aba. `processos_usar_ia`
  continua sem nenhum ponto de aplicação (PDR-0010, PDR-0008); arquivar,
  reabrir, apensos e partes seguem regidos apenas pela autorização de
  módulo.
- Escopo por `Processo.responsavel` (`somente_seus`/`todos`) e
  responsabilidade obrigatória são a direção vigente. Equipe não
  concede acesso nem filtra Processos.
- Cada processo tem um único responsável principal obrigatório —
  responsável pelos Prazos gerados na Agenda Jurídica (e quem os recebe
  quando o responsável muda) e referência dos indicadores. Pode ter N
  integrantes habilitados além dele, que não recebem prazos
  automaticamente.
- Atribuir/reatribuir responsável exige a habilitação
  `processos_atribuir_responsavel` ou a autoridade do Administrador do
  escritório. Gerenciar integrantes habilitados exige
  `gerir_habilitar_usuario_processos`.
- Equipe serve só de atalho para selecionar integrantes habilitados
  (ver "Equipe como atalho de seleção" em [PRODUCT.md](../PRODUCT.md),
  PDR-0028): só as pessoas ficam gravadas — não é o mesmo mecanismo
  do parágrafo acima ("Equipe não concede acesso nem filtra Processos"
  continua valendo para `Processo.equipe`/escopo; isto é só sobre a
  lista de integrantes habilitados, PDR-0014).

## Partes (PDR-0013 — modelo vigente; catálogo estendido por PDR-0023/PDR-0027)

- Cada parte tem um único campo de papel processual, agrupado
  visualmente em Polo Ativo / Polo Passivo / Outros — forma do modelo
  definida por PDR-0013, catálogo de valores estendido por
  PDR-0023/PDR-0027:
  - Polo Ativo: Autor, Embargante, Recorrente, Exequente, Requerente,
    Reclamante, Agravante, Impugnante, Reconvinte, Excipiente,
    Impetrante, Inventariante.
  - Polo Passivo: Réu, Embargado, Recorrido, Executado, Requerido,
    Reclamado, Agravado, Impugnado, Reconvindo, Excepto, Impetrado,
    Inventariado.
  - Outros: Terceiro Interessado, Ministério Público, Juiz, Perito,
    Testemunha, Assistente de Acusação (PDR-0027 — sem polo, sem
    contraparte, disponíveis para qualquer área do direito). ("Amicus
    Curiae" removido do catálogo por PDR-0023.)
  - Autor/Réu seguem válidos para o caso genérico; os pares por tipo de
    ação (execução, trabalhista, recurso, agravo, impugnação,
    reconvenção, exceção, mandado de segurança, inventário) são
    escolha manual de quem cadastra a Parte — nada infere o par a
    partir de outro campo do processo.
- Sugestão automática de contraparte (PDR-0027): os 12 pares Polo
  Ativo/Polo Passivo estão mapeados em `ParteProcesso.PAPEL_CONTRAPARTE`.
  Ao selecionar, no formulário de cadastro, um papel pareado, um
  segundo mini-formulário aparece via JS (sem reload) com o papel
  oposto pré-selecionado — envio continua sendo dois POSTs
  independentes para `adicionar_parte`. Sugestão é dispensável e não
  aparece se a contraparte já estiver cadastrada no processo; papéis de
  "Outros" nunca disparam a sugestão. Não contradiz o PDR-0023: a
  inferência é a partir da parte já selecionada no formulário, nunca a
  partir de um campo do processo.
- Parte que corresponde a um dos Clientes do processo reaproveita o
  cadastro (sem redigitação); campos de advogado pré-preenchidos quando
  a parte bate com um dos Clientes por CPF/CNPJ.
- Advogado é texto livre (nome + OAB) associado à parte, no máximo um
  por parte — nunca uma parte em si do processo.
- Parte pode ser marcada como ente público, por esfera (Federal,
  Estadual/DF, Municipal; autarquias e fundações seguem o ente a que
  pertencem). Opcional e manual, sem inferência por nome/CNPJ. Usado
  hoje pela sub-aba Precatório de Honorários.
- PDR-0013 substitui PDR-0001/PDR-0011 (modelo de três dimensões:
  vínculo/posição estrutural/qualificação processual, representantes
  normalizados, histórico de classificação). O modelo antigo não deve
  ser reintroduzido.

## Clientes

- Um processo pode ter **mais de um Cliente vinculado**
  (`Processo.clientes`, N:N) — regra de produto já registrada em
  [PRODUCT.md](../PRODUCT.md), implementada a partir da reunião de
  13/09. Card superior do detalhe do processo lista todos os clientes
  vinculados, cada um linkando para sua própria página.
- Outros módulos que referenciam "o cliente do processo" para
  pré-preenchimento automático (Agenda Jurídica, Financeiro) usam o
  primeiro cliente vinculado como melhor esforço — esses módulos
  continuam com cliente único no próprio cadastro.
- Criação cruzada Cliente↔Processo: aba Processos do Cliente tem botão
  "Novo processo" (`processos:novo?cliente=<id>`, mesmo padrão de
  pré-preenchimento por querystring do `?processo=` de Custas
  Judiciais; id inválido/inativo é ignorado sem erro). No formulário de
  novo Processo, "+ Novo cliente" guarda um rascunho local
  (`sessionStorage`, nunca vira registro no banco, some ao fechar o
  navegador) de tudo já preenchido, abre `clientes:novo?next=<url>` e,
  ao salvar (ou cancelar) o Cliente, volta e restaura o rascunho — o
  cliente recém-criado chega por `?cliente_criado=<id>` e é
  pré-selecionado por cima do rascunho. Nenhuma autorização nova: cada
  atalho reusa a checagem de módulo/habilitação já existente da tela de
  destino.

## Comarca e Vara

- `vara` e `comarca` são dois campos de texto livre separados (antes um
  único campo `vara_juizo`) — reunião de 13/09. Alimentam, junto com
  `estado`/`cidade`, o agrupamento hierárquico por localidade do
  Dashboard: Estado → Cidade → Comarca → Vara — ver
  [dashboard.md](dashboard.md).

## Exclusão definitiva (PDR-0024)

- Distinta de Arquivar. Exige a habilitação `processos_excluir` mais o
  mesmo escopo de mutação de Arquivar (Administrador ou responsável).
- Remove o Processo e o que é intrínseco a ele — Documentos, Partes,
  Andamentos, vínculos de Apenso, Intimações (cascata já existente no
  modelo) — e, com os Andamentos, os Prazos que eles geraram na Agenda
  Jurídica. Lançamentos financeiros e demais itens da Agenda Jurídica
  vinculados **não são apagados** — só perdem a referência
  (`on_delete=SET_NULL`, já era o padrão).
- Ação definitiva nesta versão — sem lixeira, sem desfazer.

## Faixa de status, Integrantes e Agenda do processo (detalhe do processo)

- Abaixo do card superior, uma faixa somente informativa mostra Fase
  atual (tipo do andamento mais recente), Parado há X dias (dias desde
  o último andamento, ou desde a distribuição sem nenhum andamento) e
  Tempo médio entre andamentos — todos recalculados a cada carregamento
  a partir dos Andamentos, nunca campos próprios do Processo.
- Integrantes habilitados e "Agenda do processo" aparecem como cards
  funcionais abaixo do card superior, fora do sistema de abas — reunião
  de 13/09. O card da agenda lista os itens em aberto de qualquer tipo
  vinculados ao processo, no escopo de leitura da Agenda Jurídica do
  usuário (sem o módulo, o card não aparece); clicar num item abre o
  formulário dele para quem pode editá-lo, ou a Agenda Jurídica
  filtrada para quem só o enxerga; "Ver todos" filtra a agenda por este
  processo (`agenda:index?processo=<id>`); "+ Novo" escolhe o tipo e
  abre o formulário padrão (`agenda:novo`) com o Processo
  pré-preenchido, sem travar o campo. O detalhe do Cliente tem o mesmo
  card ("Agenda do cliente").

## Custas Judiciais (aba do processo)

- Aba própria no detalhe do processo, reaproveitando as Solicitações
  Financeiras (PDR-0006/PDR-0015) filtradas por este processo —
  **visível a qualquer usuário que abra o processo**, sem o filtro por
  solicitante que a aba "Solicitações" do Financeiro aplica para quem
  não tem acesso amplo a dados. Evita que dois advogados solicitem a
  mesma custa em duplicidade. "+ Nova solicitação" pré-preenche **e
  trava** tipo (sempre Pagamento, nunca Reembolso), processo e cliente
  do processo de origem — sem opção de trocar por outro processo/cliente
  no meio do caminho (só fica escolhível entre os clientes do próprio
  processo quando ele tem mais de um vinculado); exige acesso ao módulo
  Financeiro para criar (a leitura da aba não exige). Status seguem o
  fluxo já aprovado (PDR-0015) — solicitada → em análise → aprovada →
  paga, ou rejeitada. Ao marcar como paga, ver
  [financeiro.md](financeiro.md#solicitações-financeiras-pdr-0006-fluxo-em-pdr-0015)
  para a exigência de comprovante + quem pagou e o reflexo no saldo de
  custas do cliente (PDR-0005).
- Solicitação com status "paga" mostra também, só leitura, quem pagou e
  o comprovante de pagamento anexado ao confirmar o pagamento — sem
  opção de editar/anexar a partir daqui (isso continua exclusivo do
  Financeiro). Download do comprovante usa endpoint próprio de
  Processos (`baixar_comprovante_custa`), escopado pela mesma
  visibilidade da aba (`_processos_no_escopo`) — não reaproveita o
  endpoint de Financeiro porque aquele é restrito por
  dados_próprios/dados_todos, mais estreito que a visibilidade da aba.

## Situação por decisão judicial

- `status` do processo: ativo, suspenso, sobrestado, arquivado (e
  `encerrado`, legado sem uso). Suspenso/sobrestado/retomada (volta a
  ativo) são lançados por quem adiciona o andamento, num campo opcional
  do formulário; processo arquivado não muda por aqui (arquivar/
  desarquivar seguem seu fluxo).

## Apensos (PDR-0012)

- Relação simétrica entre dois Processos existentes, sem hierarquia.
- Ambos mantêm identidade própria; nada é copiado, fundido, herdado ou
  propagado (cliente, responsável, equipe, status, fase, participantes,
  andamentos, prazos, documentos).
- Remover a relação não exclui nenhum processo. A↔B e B↔C não inferem
  A↔C. "Menor"/"maior" na persistência é só normalização técnica do
  par — não significa principal/pai/filho.

## Arquivamento e andamentos

- Arquivar muda `status` para `arquivado`; processo some das listas
  operacionais mas continua disponível em análise de dados. Reaproveita
  a mesma autorização de edição — sem habilitação separada para
  arquivar.
- Andamentos em ordem cronológica, com anexo opcional e autor
  identificável. Data do último andamento é a referência de inatividade.
- Fase processual, status processual e andamento processual são
  conceitos distintos (não usar como sinônimos).
- `resultado_sentenca` saiu do formulário de criação/edição do processo
  (reunião de 13/09) — passa a ser definido a partir de um Andamento,
  com um campo opcional no formulário de "Adicionar andamento"
  ("atualizar resultado da sentença"). O campo continua existindo em
  `Processo` e alimentando o indicador "Julgados" do Dashboard.
- `fase_andamento_atual` (`Processo.FASE_ANDAMENTO_CHOICES`,
  specs/painel-novos-recortes-analise.md, já apagada) segue o mesmo
  padrão de `resultado_sentenca`: campo opcional no formulário de
  "Adicionar andamento" ("atualizar fase do andamento atual"),
  preenchido manualmente por quem lança o andamento — nunca no
  formulário de criação/edição do processo. **Sem sugestão automática
  por tipo de andamento nesta versão**: o mapeamento tipo→fase precisa
  ser validado pelo sócio advogado antes de ativar (mesma exigência já
  usada para o catálogo legal de prazos — ver OPEN item
  correspondente em [STATUS.md](../STATUS.md)). Alimenta o bloco "Fase
  do andamento atual" da Análise de dados do Dashboard.

### Catálogo de tipo de andamento, por área do direito

- `tipo` do andamento não é mais uma lista genérica única — é um
  catálogo agrupado pela área do processo (`Processo.area_direito`):
  Civil, Trabalhista e Penal têm listas próprias; todas as demais áreas
  do catálogo (Consumidor, Sucessões, Administrativo, Tributário,
  Família, Empresarial, Médico, Previdenciário, Digital,
  Propriedade Intelectual, Imobiliário, Desportivo, Direito
  Internacional, Outro) caem no catálogo Civil como padrão (sem
  catálogo próprio) — decisão deliberada para manter o escopo pequeno;
  catálogo específico para alguma dessas áreas é spec futura própria,
  não extensão silenciosa. Um grupo "Genéricos" (Despacho, Decisão
  interlocutória, Perícia) aparece sempre, em qualquer área.
- "Eleitoral" não faz parte do catálogo de área do direito (removido na
  revisão do sócio de 2026-09-17); processos e peças que a tinham foram
  convertidos para "Outro".
- A área gravada como `CÍVEL` é exibida como "Civil" (não "Cível"),
  em Processos e em Modelos; o valor gravado no banco não mudou.

### Criação automática por IA (reservada)

- `processos:novo` exibe o botão "Criar automaticamente" desabilitado
  ("em breve"), só na criação. É ponto de entrada reservado para a IA
  jurídica (PDR-0008): inerte, sem endpoint e sem gate por
  `processos_usar_ia`. A criação manual é o único caminho hoje.
- `Processo.AREAS_CHOICES` é a fonte única do catálogo de área do
  direito — Modelo de Peças (`apps/modelos/forms.py`) reusa a mesma
  lista em vez de manter um catálogo próprio divergente.
- Valores legados (`andamento`, `decisao`, `audiencia`, `outro`)
  continuam válidos só para exibir o texto de andamentos já existentes
  — não aparecem mais como opção no formulário de novos andamentos.
- `MovimentacaoProcessual.catalogo_por_area(processo)` é a fonte única
  do agrupamento; `MovimentacaoProcessualForm` exige `processo=` no
  construtor para montar o catálogo certo e escopar `origem_prazo` ao
  mesmo processo — POST com um valor de `tipo` fora do catálogo da área
  do processo é rejeitado pela validação do form (defesa contra POST
  forjado, não só UX).

### Prazo como atributo do andamento (não mais um tipo)

- "Prazo" não é mais um valor de `tipo` — é um atributo
  (`MovimentacaoProcessual.data_prazo`, opcional) que qualquer
  andamento, de qualquer tipo/catálogo, pode ter preenchido.
- `origem_prazo` (FK opcional auto-referenciada) permite apontar, só
  para rastreabilidade/exibição, qual andamento anterior do mesmo
  processo originou aquele prazo — ex.: o Despacho que determinou "5
  dias", vinculado à Intimação que efetivamente disparou a contagem.
  Sem nenhum cálculo automático de data nesta versão — quem lança
  digita a data final já calculada; ver
  `specs/agenda-prazos-processuais-automaticos.md` (evolução futura
  sobre a Agenda Jurídica) para o
  cálculo automático futuro.
- `Processo.prazo_proximo` deixou de ser editado manualmente
  ("atualizar próximo prazo" saiu do formulário de Adicionar andamento)
  e passa a ser recalculado automaticamente
  (`services.recalcular_prazo_proximo`) a cada andamento adicionado: o
  `data_prazo` futuro mais próximo entre os andamentos do processo ou,
  se todos já venceram, o vencido mais recente; `None` sem nenhum
  `data_prazo` marcado. Cada `data_prazo` também gera o item Prazo da
  Agenda Jurídica (ver [PRODUCT.md](../PRODUCT.md#agenda-jurídica)),
  que é o que alimenta "Prazos a vencer" do Dashboard.
- Aba "Prazos" do detalhe do processo agrega automaticamente todos os
  andamentos com `data_prazo`, em timeline cronológica, com estado
  vazio quando não há nenhum; cada prazo leva ao item gerado na Agenda
  Jurídica quando ele está no escopo do usuário. O prazo também aparece (discreto) na aba
  "Andamentos", sem ser o foco ali.

## Documentos

- Arquivo anexado a um Processo (`Documento`), com storage protegido por
  tenant — mesmo padrão de `Mensagem.anexo` (Chat) e
  `SolicitacaoFinanceira.anexo` (Financeiro): sem URL pública, entrega
  só por view que carrega o objeto pelo `QuerySet` autorizado.
- Vínculo é direto com o Processo — não com um andamento específico.
  Documento pertence a um único Processo, sem reuso entre processos.
- Tipo (petição, decisão, procuração, prova, contrato, outro) é
  catálogo fixo em código, não gerenciável por tenant — diferente do
  catálogo de categorias de Modelos (`CategoriaModeloPeca`, PDR-0018).
- Visualizar/baixar segue o mesmo escopo de leitura do detalhe do
  processo (`somente_seus`/`todos`); anexar e excluir exigem estar no
  escopo de mutação (Administrador ou responsável do processo) mais
  habilitação granular própria — `processos_documento_adicionar` e
  `processos_documento_excluir`, respectivamente.
- Excluir um documento é definitivo nesta versão — sem histórico de
  versão nem lixeira. Excluir o Processo remove também seus documentos.

## Localidade e resultado de sentença

- `estado` (UF) e `cidade` são campos opcionais, em branco por padrão;
  alimentam o agrupamento hierárquico por localidade do Dashboard junto
  com `comarca`/`vara` (ver seção "Comarca e Vara" acima) — ver
  [dashboard.md](dashboard.md).
- `resultado_sentenca` (procedente/parcialmente procedente/
  improcedente) é opcional e sempre preenchido manualmente nesta
  versão — sem detecção automática por IA a partir do andamento de
  sentença. Alimenta o indicador "Julgados" da aba Análise de dados do
  Dashboard.

## Intimações

- `Intimacao` (processo, motivo, prazo_manifestacao, status
  pendente/manifestada, origem manual/email) sempre vinculada a um
  Processo existente, dentro do escopo de mutação de quem cria. Criação
  e vínculo são manuais nesta versão — sem leitura automática de
  e-mail. Alimenta o painel "Intimações" da Visão geral do Dashboard —
  ver [dashboard.md](dashboard.md).

## Fora de escopo imediato

- Assistente/Laboratório (condicionado a PDR-0008);
- OCR de documentos, integração com API de tribunal;
- determinação automática de status por IA.

## Pontos em aberto

- Lista canônica definitiva de valores de status processual.
- Autoridades além de juiz (relator, desembargador) — Perito já
  resolvido como valor simples em Outros pelo PDR-0027, sem modelagem
  própria de "autoridade".
- Mecanismo exato de criação rápida de cliente durante o fluxo de
  processo.
- Materialização automática do Cliente como Parte ao vincular o
  Processo (PDR-0013, ponto em aberto) — implementação atual usa só o
  fluxo manual de adicionar parte, com nome/CPF-CNPJ reaproveitáveis
  por atalho no formulário, sem criação automática.

## Referências

- [PDR-0001](../decisions/PDR-0001-participantes-processuais.md) (parcialmente substituído)
- [PDR-0010](../decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [PDR-0012](../decisions/PDR-0012-relacao-simetrica-processos-apensos.md)
- [PDR-0013](../decisions/PDR-0013-partes-processo-modelo-simplificado.md)
- [PDR-0014](../decisions/PDR-0014-responsavel-integrantes-processos.md)
- [PDR-0017](../decisions/PDR-0017-habilitacoes-criar-editar-andamento-processos.md)
- [PDR-0023](../decisions/PDR-0023-partes-catalogo-pares-por-tipo-acao.md)
- [PDR-0024](../decisions/PDR-0024-exclusao-definitiva-processo.md)
- [PDR-0027](../decisions/PDR-0027-sugestao-contraparte-e-papeis-outros.md)
- [STATUS.md](../STATUS.md#processos) para o estado real de implementação
