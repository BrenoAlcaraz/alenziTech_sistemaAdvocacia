---
name: Breno - LawSystem
description: Ferramenta jurídica de trabalho diário, densa e precisa, que veste a marca de cada escritório.
colors:
  tinta-nanquim: "#1a1a1a"
  tinta-nanquim-hover: "#2a2a2a"
  bronze-envelhecido: "#8b7355"
  bronze-claro: "#c4a882"
  papel-quente: "#f5f3ef"
  areia: "#ede8e0"
  folha-branca: "#ffffff"
  texto-principal: "#111827"
  texto-secundario: "#374151"
  texto-apoio: "#5f6773"
  texto-apagado: "#9ca3af"
  borda-campo: "#e5e7eb"
  borda-card: "#f3f4f6"
  credito: "#166534"
  credito-fundo: "#dcfce7"
  alerta: "#991b1b"
  alerta-fundo: "#fee2e2"
  urgente: "#c2410c"
  urgente-fundo: "#ffedd5"
typography:
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: "2rem"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: "1.75rem"
  section:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: "1.25rem"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.25rem"
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: "1rem"
  eyebrow:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: "1rem"
    letterSpacing: "0.025em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "24px"
  3xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.tinta-nanquim}"
    textColor: "{colors.folha-branca}"
    typography: "{typography.body}"
    rounded: "{rounded.xl}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.tinta-nanquim-hover}"
  button-secondary:
    backgroundColor: "{colors.folha-branca}"
    textColor: "{colors.texto-secundario}"
    rounded: "{rounded.xl}"
    padding: "8px 16px"
  button-danger:
    backgroundColor: "{colors.folha-branca}"
    textColor: "{colors.alerta}"
    rounded: "{rounded.xl}"
    padding: "8px 16px"
  card:
    backgroundColor: "{colors.folha-branca}"
    rounded: "{rounded.xl}"
    padding: "20px"
  input:
    backgroundColor: "{colors.folha-branca}"
    textColor: "{colors.texto-principal}"
    typography: "{typography.body}"
    rounded: "{rounded.xl}"
    padding: "8px 12px"
  search-bar:
    backgroundColor: "{colors.areia}"
    textColor: "{colors.texto-apagado}"
    rounded: "{rounded.xl}"
    padding: "8px 12px"
  sidebar:
    backgroundColor: "{colors.tinta-nanquim}"
    width: "212px"
  sidebar-item:
    textColor: "{colors.texto-apagado}"
    rounded: "{rounded.lg}"
    height: "40px"
    padding: "0 12px"
  badge-area:
    backgroundColor: "{colors.areia}"
    textColor: "{colors.texto-secundario}"
    typography: "{typography.eyebrow}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
  badge-urgente:
    backgroundColor: "{colors.urgente-fundo}"
    textColor: "{colors.urgente}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "2px 8px"
---

# Design System: Breno - LawSystem

## Overview

**Creative North Star: "O Braço Direito"**

O sistema é o braço direito do advogado: carrega o trabalho pesado de
vários profissionais para que a pessoa foque a energia onde ela
importa. A interface não disputa atenção com o trabalho. É uma
ferramenta de uso diário, o dia inteiro, no computador, que precisa
fazer o escritório fluir leve, organizado e preciso. A densidade é
alta de propósito (a maior parte do texto está entre 12px e 14px),
mas a ordem vem de hierarquia clara, espaço regular e cor contida, não
de caixas e ornamentos.

A identidade é emprestada: a cor principal e o acento vêm da marca de
cada escritório (white label). O sistema só fornece a moldura (papel
quente, folhas brancas, tinta escura) e garante que qualquer marca
continue legível sobre ela. Por isso a cor principal é tratada como
tinta, não como decoração: preenche a barra lateral e a ação principal,
e mais nada.

O visual rejeita explicitamente quatro caminhos: painel SaaS genérico
(gradientes, roxo/azul de startup, grade de cards com ícone colorido),
sistema público/legado (cinza, tabelas cruas, sem hierarquia),
escritório de luxo caricato (dourado em excesso, serifas ornamentais,
mármore, balança da justiça) e cara de "feito tudo por IA" (padrões
genéricos sem decisão, simetria vazia, enfeite sem função).

**Key Characteristics:**
- Moldura neutra e quente; a marca do escritório é a única voz de cor.
- Denso e preciso: 14px no corpo, 12px em metadados, títulos curtos.
- Plano por padrão: folhas brancas com borda fina sobre papel quente.
- Cantos gentis e consistentes (12px em controles e cards).
- Cor de estado só com significado (crédito, alerta, prazo urgente).

## Colors

Uma paleta de papel e tinta, em que só a cor da marca do escritório e
os estados carregam saturação.

### Primary
- **Tinta Nanquim** (`tinta-nanquim`; padrão de fábrica, substituído
  pela cor principal do escritório via `--cor-primaria-rgb`): fundo da
  barra lateral, botão primário, anel de foco de campos e sublinhado
  da aba ativa. A cor que o escritório escolhe é escurecida
  automaticamente até luminância relativa ≤ 0,105
  (`apps/saas_tenants/cores.py`), para que texto branco sobre ela —
  inclusive o branco a 80% dos itens inativos da barra lateral —
  fique ≥ 4,5:1 em qualquer matiz.
- **Tinta Nanquim Hover** (`tinta-nanquim-hover`): hover do botão
  primário e dos itens da barra lateral; também derivada da cor do
  escritório.

### Secondary
- **Bronze Envelhecido** (`bronze-envelhecido`; padrão de fábrica,
  substituído pela cor secundária do escritório via
  `--cor-secundaria-rgb`): acento discreto de marca, badge de plano,
  realces pontuais e links de ação ("Ver →", "Limpar filtros"). Como
  vira texto, a cor do escritório é escurecida até luminância ≤ 0,14,
  o que garante 4,5:1 sobre branco, papel quente e areia (escurecer
  foi preferido a tirar a secundária dos links, que perderiam a marca).
- **Bronze Claro** (`bronze-claro`): borda do badge de plano. Fixo,
  não segue a cor do escritório.

### Neutral
- **Papel Quente** (`papel-quente`): fundo de toda a área de trabalho.
- **Areia** (`areia`): fundos secundários: barra de busca, badge de
  área do direito, moldura de ícone em cards de métrica e estado vazio.
- **Folha Branca** (`folha-branca`): cards, cabeçalho, campos,
  dropdowns.
- **Texto principal / secundário / de apoio / apagado**
  (`texto-principal`, `texto-secundario`, `texto-apoio`,
  `texto-apagado`): títulos e valores; labels e títulos de seção;
  descrições, metadados e placeholders; ícones decorativos. O texto
  de apoio é mais escuro que o gray-500 do Tailwind para passar de
  4,5:1 também sobre papel quente e areia; o cinza apagado
  (`texto-apagado`) nunca é usado em texto, só em ícone decorativo.
- **Borda de campo / de card** (`borda-campo`, `borda-card`): contorno
  de inputs e selects; contorno e divisores de cards.

### Estados
- **Crédito** sobre **fundo de crédito**: valores de entrada, sucesso.
- **Alerta** sobre **fundo de alerta**: despesa, erro, contador de
  notificações.
- **Urgente** sobre **fundo urgente**: prazo curto.

### Named Rules
**A Regra da Tinta Emprestada.** A cor principal é do escritório, não
do sistema. Ela aparece só na barra lateral, na ação primária, no foco
e na aba ativa. Nunca em fundos grandes, gráficos decorativos ou
texto corrido.

**A Regra do Estado com Sentido.** Verde, vermelho e laranja só
aparecem quando significam crédito, alerta/despesa ou prazo urgente.
Nunca como enfeite ou categoria.

## Typography

**Body Font:** Inter (com system-ui, sans-serif)

**Character:** uma única família, neutra e muito legível em tamanho
pequeno. A hierarquia vem de peso e cor, não de troca de fonte.

### Hierarchy
- **Headline** (700, 24px, 32px): título de página principal.
- **Title** (700, 20px, 28px): título de página de detalhe e de
  formulário.
- **Section** (600, 14px, 20px): título de seção dentro de card, em
  texto secundário.
- **Body** (400, 14px, 20px): texto de trabalho, campos, botões,
  itens de lista.
- **Label** (500, 12px, 16px): metadados, badges, datas, valores
  auxiliares. É o tamanho mais usado do sistema.
- **Eyebrow** (600, 12px, tracking 0.025em, maiúsculas): rótulo de
  grupo acima de listas e badge de área do direito.

### Named Rules
**A Regra do Peso, não do Tamanho.** A densidade é alta, então a
hierarquia sobe por peso (400 → 500 → 600 → 700) e por tom de cinza
antes de subir de tamanho. Não há display gigante: o maior título da
tela tem 24px.

## Layout

Shell fixo em três partes: barra lateral à esquerda (212px expandida,
60px recolhida, só ícones com nome no tooltip), cabeçalho branco de
56px com borda inferior e área de conteúdo rolável sobre papel quente.
O conteúdo ocupa até 1600px, com margem lateral de 16px (32px a partir
de 640px) e 24px no topo. Abaixo de 1024px a barra lateral começa
recolhida, e a escolha do usuário fica lembrada no navegador.

O ritmo é curto e regular: 8px e 12px entre itens relacionados, 16px
entre grupos, 20px de padding interno de card, 24px entre blocos. O
uso é desktop-first. No celular a tela precisa funcionar para consulta
rápida, sem layout próprio.

Texto livre em card de detalhe quebra linha e nunca fica escondido
(`.texto-quebra`). Em listas compactas, trunca com o texto completo no
`title`.

## Elevation & Depth

Plano por padrão, com camadas tonais: papel quente (fundo) → folha
branca (card) → areia (elemento secundário dentro do card). A
separação vem de borda de 1px e de uma sombra quase invisível, não de
elevação.

### Shadow Vocabulary
- **Repouso** (`box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05)`): todo card.
- **Flutuante** (`box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)`):
  só dropdowns e menus que se sobrepõem ao conteúdo.

### Named Rules
**A Regra da Folha sobre a Mesa.** Card é uma folha branca apoiada no
papel: borda fina e sombra de repouso. Sombra forte só existe para o
que flutua sobre a página (menus, dropdowns), nunca para destacar card.

## Shapes

Cantos gentis e consistentes. Controles e contêineres (botões, campos,
cards, alertas, dropdowns) usam 12px. Itens de navegação e pequenos
botões de ícone usam 8px. Badges de estado e avatares são pílulas ou
círculos. O badge de área do direito é a exceção quase reta (4px),
como etiqueta de pasta. Bordas são sempre de 1px e em cinza claro.

## Components

### Buttons
Contidos e precisos: texto de 14px peso 500, ícone opcional à
esquerda, nunca em caixa alta.
- **Shape:** cantos gentis (12px).
- **Primary:** tinta do escritório com texto branco, padding 8px 16px.
  Uma ação primária por contexto.
- **Hover:** a tinta de hover, com transição de cor.
- **Secondary:** fundo branco, borda cinza de 1px, texto secundário;
  hover em cinza muito claro.
- **Danger:** mesmo formato do secundário, com borda e texto em
  vermelho; hover em vermelho muito claro. Ação destrutiva nunca é um
  botão cheio.

### Chips / Badges
- **Área do direito:** etiqueta em areia, texto secundário, 12px
  semibold, cantos quase retos.
- **Estado:** pílula com fundo claro e texto do estado (urgente,
  prazo normal em cinza, plano em bronze).
- **Prioridade do cliente:** pílula indicativa (idoso em âmbar, menor
  de idade em azul), só visual.
- **Tipo de compromisso (Agenda):** etiqueta de 6px de raio nos tokens
  `tipo-*` (`.badge-tipo-<tipo>`). É categoria, não estado: nenhum tom
  repete verde, vermelho ou laranja (audiência em índigo, reunião em
  bronze).

### Diálogo de confirmação
Folha branca de até 384px sobre véu escuro: pergunta em 16px semibold,
registro afetado em 14px médio, o que acontece em texto secundário e o
que não é perdido em 12px de apoio. Confirmar à esquerda (contorno
vermelho; primário quando a ação não é destrutiva), Cancelar à direita
e com o foco ao abrir. Esc fecha e o foco volta ao botão de origem.

### Mensagens de resultado
Faixa de 12px de raio no par de estado (sucesso em crédito, erro em
alerta, aviso em urgente, informação em areia), ícone de 20px à
esquerda e botão de fechar rotulado à direita.

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** folha branca sobre papel quente.
- **Shadow Strategy:** repouso (ver Elevation & Depth).
- **Border:** 1px no cinza mais claro.
- **Internal Padding:** 20px (24px em formulários maiores).
- **Card de métrica:** ícone de 20px dentro de quadrado de 40px em
  areia, valor em 24px bold e rótulo em 14px de apoio.

### Inputs / Fields
- **Style:** fundo branco, borda cinza de 1px, 12px de raio, texto de
  14px, padding 8px 12px. Label de 14px peso 500 acima, 4px de
  distância.
- **Focus:** anel de 2px na tinta do escritório, a borda some.
- **Label:** sempre associado ao campo (`for`/`id`); rótulo de grupo
  (botões, rádios, checkboxes) é `<p class="label">`.
- **Error:** borda vermelha e label vermelho, acionados pela presença
  da mensagem de erro do campo.

### Navigation
- **Barra lateral:** fundo na tinta do escritório, logo no topo. Itens
  de 40px com ícone de 20px e rótulo de 14px em branco a 80%. Hover
  clareia o texto e aplica a tinta de hover. O item ativo ganha um
  véu branco de 10%, texto branco médio e `aria-current="page"`, sem
  bloco claro nem dourado.
- **Abas:** sublinhado de 2px na tinta do escritório na ativa; inativas
  em texto de apoio, sem sublinhado. Abas-link dentro de
  `<nav aria-label="Abas">` com `aria-current="page"` na ativa; abas
  trocadas por JS são `<button>` com `aria-pressed`.
- **Foco por teclado:** todo elemento interativo mostra anel de 2px na
  tinta do escritório com recuo de 2px (`:focus-visible`); na barra
  lateral o anel é branco. "Pular para o conteúdo" é o primeiro
  elemento focável de toda tela autenticada.
- **Cabeçalho:** Voltar só em telas secundárias. Badge de plano,
  notificações e menu do usuário à direita.

### Estado vazio
Círculo de 56px em areia com ícone de linha em cinza, mensagem curta
em 14px e, quando houver, uma ação primária logo abaixo.

## Do's and Don'ts

### Do:
- **Do** usar a cor do escritório só na barra lateral, ação primária,
  foco e aba ativa (A Regra da Tinta Emprestada).
- **Do** montar hierarquia com peso e tom de cinza antes de aumentar
  tamanho; o maior título é 24px.
- **Do** apoiar conteúdo em folhas brancas com borda de 1px e sombra de
  repouso sobre o papel quente.
- **Do** manter 12px de raio em botões, campos e cards, e 8px em itens
  de navegação.
- **Do** testar qualquer tela nova com uma cor de escritório clara e uma
  saturada; ela precisa continuar legível e coerente com as duas.

### Don't:
- **Don't** parecer painel SaaS genérico: sem gradientes, sem roxo/azul
  de startup, sem grade de cards com ícone colorido.
- **Don't** parecer sistema público/legado: sem tabelas cruas cinzentas
  sem hierarquia.
- **Don't** parecer escritório de luxo caricato: sem dourado em
  excesso, serifas ornamentais, mármore ou balança da justiça.
- **Don't** parecer "feito por IA": nada de enfeite sem função,
  simetria vazia ou padrão genérico que não resolve uma tarefa real.
- **Don't** usar verde, vermelho ou laranja sem significado de estado.
- **Don't** comunicar estado só por cor: faixa, ponto ou marcador
  colorido acompanha texto visível ou texto para leitor de tela.
- **Don't** usar sombra forte em card; ela é só para o que flutua.
- **Don't** fazer botão destrutivo cheio; destrutivo é contorno
  vermelho.
