---
id: PDR-0027
title: Partes — sugestão automática de contraparte e novos papéis em Outros
status: accepted
owner: product-and-engineering
decision_date: 2026-09-16
last_reviewed: 2026-09-16
supersedes: []
complements:
  - PDR-0023
source_files: []
---

# PDR-0027 — Partes: sugestão automática de contraparte e novos papéis em Outros

## Contexto

PDR-0023 estendeu o catálogo de `papel` (`ParteProcesso.PAPEL_CHOICES`)
com 10 pares novos por tipo de ação, mas manteve a escolha do papel
inteiramente manual — nada no sistema relaciona os pares entre si nem
ajuda quem cadastra a lembrar de lançar o lado oposto. Isso é fonte
comum de esquecimento: cadastrar o Exequente e esquecer o Executado, por
exemplo.

## Decisão

### Sugestão automática de contraparte

- Os 12 pares Polo Ativo/Polo Passivo do catálogo (Autor↔Réu,
  Embargante↔Embargado, Recorrente↔Recorrido, Exequente↔Executado,
  Requerente↔Requerido, Reclamante↔Reclamado, Agravante↔Agravado,
  Impugnante↔Impugnado, Reconvinte↔Reconvindo, Excipiente↔Excepto,
  Impetrante↔Impetrado, Inventariante↔Inventariado) passam a ter uma
  relação formal no código (`ParteProcesso.PAPEL_CONTRAPARTE`).
- Ao selecionar, no formulário de cadastro de Parte, um papel com
  contraparte mapeada, um segundo mini-formulário aparece
  dinamicamente na mesma tela (JS, sem reload), com o papel oposto
  pré-selecionado. Os dois continuam sendo **envios/POSTs
  independentes** — mesmo endpoint (`adicionar_parte`), sem transação
  conjunta.
- Sugestão é dispensável (usuário pode ignorar/fechar) e não aparece se
  a contraparte correspondente já estiver cadastrada no processo.
- Papéis do grupo "Outros" nunca entram em `PAPEL_CONTRAPARTE` e nunca
  disparam a sugestão.
- **Esta decisão não contradiz o PDR-0023**: a inferência é a partir da
  parte já selecionada/cadastrada no próprio formulário, nunca a partir
  de um campo do processo (área, tipo de ação, fase) — o PDR-0023
  continua vigente para a proibição de inferir o papel a partir do
  processo.

### Novos papéis em Outros

- Adiciona `Perito`, `Testemunha` e `Assistente de Acusação` ao grupo
  "Outros" do catálogo — sem polo, sem contraparte, disponíveis para
  qualquer processo sem filtro por área do direito (mesmo padrão de
  todo o catálogo atual).
- Resolve parcialmente o ponto em aberto de
  `docs/modules/processos.md` ("Autoridades além de juiz — relator,
  desembargador, perito"), só para **Perito**, e só como valor simples
  de `papel` em Outros — não introduz modelagem própria de
  "autoridade". Relator e desembargador continuam em aberto.

## Consequências

- `docs/modules/processos.md`, seção "Partes", passa a registrar os 3
  papéis novos em Outros e a existência da sugestão de contraparte;
  "Pontos em aberto" atualizado para refletir Perito resolvido.
- `docs/STATUS.md`, linha Processos, passa a registrar a feature como
  implementada.

## Fora do escopo desta decisão

- Inferência de papel a partir de área do direito ou fase do processo
  — continua proibida pelo PDR-0023.
- Envio conjunto (parte + contraparte num único POST/transação).
- Filtro de papéis disponíveis por área do processo.
- Obrigatoriedade de cadastrar a contraparte — a sugestão nunca
  bloqueia salvar só um lado.
- Modelagem de "autoridade" (relator, desembargador) além do valor
  simples "Perito" em Outros.

## Critérios de aceite funcionais

- Selecionar, no formulário de cadastro, um papel com contraparte
  mapeada exibe automaticamente, sem reload, um segundo formulário com
  o papel oposto pré-selecionado.
- A sugestão pode ser dispensada sem preencher o segundo formulário e
  sem impedir o salvamento do primeiro.
- Se a contraparte já existe cadastrada no processo, a sugestão não
  aparece.
- Selecionar qualquer papel de "Outros" nunca dispara a sugestão.
- Perito, Testemunha e Assistente de Acusação aparecem no optgroup
  "Outros" do formulário, disponíveis para qualquer processo.

## Fontes

- `specs/partes-sugestao-contraparte-papeis-outros.md` (apagada após a
  promoção deste PDR, conforme
  [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
