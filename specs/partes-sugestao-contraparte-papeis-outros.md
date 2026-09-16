# Spec — Sugestão automática de contraparte + novos papéis em "Outros"

## Objetivo

Ao cadastrar uma Parte num processo, sugerir automaticamente o cadastro
da contraparte correspondente (ex.: cadastrar Exequente sugere
Executado), reduzindo o esquecimento de lançar o polo oposto. Também
adiciona três novos valores ao grupo "Outros" do catálogo de papéis:
Perito, Testemunha e Assistente de Acusação.

## Comportamento esperado

### Relação de pares (contraparte)

- Mapear os 12 pares abaixo como relação formal no código (ex.:
  dicionário `PAPEL_CONTRAPARTE` em `apps/processos/models.py`, ao lado
  de `GRUPO_POR_PAPEL`), cobrindo exatamente esta lista, sem inferir
  pares adicionais:
  - Autor ↔ Réu
  - Embargante ↔ Embargado
  - Recorrente ↔ Recorrido
  - Exequente ↔ Executado
  - Requerente ↔ Requerido
  - Reclamante ↔ Reclamado
  - Agravante ↔ Agravado
  - Impugnante ↔ Impugnado
  - Reconvinte ↔ Reconvindo
  - Excipiente ↔ Excepto
  - Impetrante ↔ Impetrado
  - Inventariante ↔ Inventariado
- A relação é simétrica (A→B implica B→A) e cobre só os 12 pares
  Polo Ativo/Polo Passivo já existentes — nenhum papel do grupo
  "Outros" entra nesse mapa.

### Sugestão via JS, sem reload

- Ao selecionar, no formulário de cadastro de Parte, um papel que tenha
  contraparte mapeada, um segundo mini-formulário aparece dinamicamente
  na mesma tela — sem recarregar a página — com o papel oposto
  já pré-selecionado (ex.: selecionar "Exequente" no primeiro formulário
  exibe um segundo formulário com "Executado" pré-selecionado, pronto
  para preencher nome/CPF-CNPJ/advogado).
- Os dois formulários continuam sendo **envios independentes**: cada um
  com seu próprio botão salvar, cada um um POST tradicional separado
  (fluxo atual de form inline server-rendered + reload). O JS só
  controla a exibição/pré-preenchimento do papel no segundo formulário,
  não agrupa os dois num único POST nem antecipa o envio do primeiro.
- A sugestão é dispensável: o usuário pode ignorar ou fechar o segundo
  formulário sem preenchê-lo, e isso não bloqueia nem altera o envio do
  primeiro.

### Não repetir sugestão já satisfeita

- Se o processo já tem uma Parte cadastrada com o papel de contraparte
  correspondente, a sugestão não aparece (nem ao carregar a tela, nem
  ao selecionar novamente o papel pareado) — o servidor expõe ao
  template/JS quais papéis de contraparte já existem no processo atual
  para essa checagem.

### Papéis sem contraparte

- Selecionar qualquer papel do grupo "Outros" (existente ou novo) nunca
  dispara a sugestão, porque nenhum papel de "Outros" entra em
  `PAPEL_CONTRAPARTE`.

### Novos papéis em "Outros"

- Adicionar `("perito", "Perito")`, `("testemunha", "Testemunha")` e
  `("assistente_acusacao", "Assistente de Acusação")` a
  `ParteProcesso.PAPEL_CHOICES`, com `GRUPO_POR_PAPEL` apontando os três
  para `"outros"`.
- Replicar os três em `ParteProcessoForm.GRUPOS_PAPEL` (optgroup
  "Outros"), na mesma posição/agrupamento visual dos já existentes.
- Sem polo, sem contraparte, disponíveis sempre para qualquer processo
  — sem filtro por área do direito, mesmo comportamento que todo o
  catálogo atual (nenhum papel hoje é filtrado por área).
- Isso resolve parcialmente o ponto em aberto de
  `docs/modules/processos.md` ("Autoridades além de juiz — relator,
  desembargador, perito") apenas para Perito, e só como valor simples
  de `papel` em "Outros" — não introduz modelagem própria de
  "autoridade" nem afeta Testemunha/Assistente de Acusação, que nunca
  fizeram parte desse ponto em aberto.

## Regras de negócio relevantes

- Esta feature **não contradiz o PDR-0023** (que mantém a escolha de
  papel manual, sem inferir a partir de área/fase do processo): a
  sugestão aqui infere a partir da **outra parte já selecionada/
  cadastrada no mesmo formulário/processo**, nunca a partir de um campo
  do processo (área, tipo de ação, fase). Deve ser registrada, ao
  final da implementação, como PDR complementar ao PDR-0023 (`complements:
  [PDR-0023]`), não como substituição.
- A sugestão é auxiliar de digitação, não validação: o usuário continua
  livre para cadastrar só um lado do par, cadastrar papéis repetidos do
  mesmo polo, ou ignorar a sugestão — nenhuma regra de obrigatoriedade
  de par é introduzida.

## Fora do escopo

- Inferência de papel a partir de área do direito ou fase do processo
  (mantém PDR-0023 como está).
- Envio conjunto — parte e contraparte num único POST/transação.
- Filtro de papéis disponíveis por área do processo.
- Qualquer obrigatoriedade de cadastrar a contraparte (a sugestão nunca
  bloqueia salvar só um lado).
- Modelagem de "autoridade" (relator, desembargador) além do valor
  simples "Perito" em Outros — ponto em aberto de
  `docs/modules/processos.md` continua registrado para o restante.

## Critérios de aceite

- Selecionar, no primeiro formulário, um papel com contraparte mapeada
  (um dos 12 pares) exibe automaticamente, sem reload, um segundo
  formulário com o papel oposto pré-selecionado.
- O segundo formulário é um envio (POST) independente do primeiro, com
  botão salvar próprio.
- A sugestão pode ser dispensada sem preencher o segundo formulário e
  sem impedir o salvamento do primeiro.
- Se a contraparte já existe cadastrada no processo, a sugestão não
  aparece (nem ao carregar a tela nem ao reselecionar o papel).
- Selecionar qualquer papel do grupo "Outros" (Terceiro Interessado,
  Ministério Público, Juiz, Perito, Testemunha, Assistente de Acusação)
  nunca dispara a sugestão.
- Perito, Testemunha e Assistente de Acusação aparecem no optgroup
  "Outros" do formulário, disponíveis para qualquer processo sem
  filtro por área.
