# Spec — Modelos de Peça: filtros, download, e peças repetitivas

## Objetivo

Ajustar nomenclatura e ações da listagem de Modelos, viabilizar
exportação de peça em PDF/DOCX, alinhar a aba "Meu Estilo" ao protótipo,
e construir a geração de peças em lote a partir de um mesmo modelo (fase
manual, com IA reservada para depois).

## Comportamento esperado

### Listagem

- Filtros conforme protótipo (`docs/prototipos/modelos-prototipo.html`)
  — já existem busca textual, categoria, área do direito, responsável e
  data; conferir o que falta.
- Rótulo "Categoria" renomeado para "Tipo de Peça" em toda a interface
  (o catálogo por trás, `CategoriaModeloPeca`, não muda de estrutura).
- Cada item da lista ganha dois botões: **visualizar** (abre a peça para
  leitura) e **baixar** (oferece PDF e DOCX).

### Meu Estilo

- Ajustar layout conforme o protótipo, mantendo os campos e regras já
  existentes (cabeçalho/rodapé/marca d'água/assinatura, fonte/cor,
  formatação de endereçamento/número/partes/jurisprudência/citação).

### Peças repetitivas — Fase 1 (sem IA)

- Nova aba/fluxo: usuário escolhe uma peça base (do acervo ou nova) e
  define quantos casos vai gerar.
- Para cada caso, pode selecionar um **Cliente já cadastrado** — o
  sistema pré-preenche automaticamente os dados já conhecidos desse
  cadastro (nome, CPF/CNPJ e demais campos do cliente).
- Campos sensíveis que não vêm do cadastro do Cliente (valor, endereço
  do caso, particularidades) ficam num editor manual, por caso.
- Ao concluir, o sistema gera as N peças e disponibiliza todas para
  download.

## Regras de negócio relevantes

- A exportação em PDF/DOCX é capacidade nova — hoje o sistema só
  importa/lê esses formatos (extração de texto na importação de um
  modelo), não gera documento a partir do conteúdo salvo.
- Peças repetitivas Fase 1 não depende de nenhum pipeline de IA — pode
  ser implementada e usada de forma independente do módulo de
  IA/Laboratório.

## Fora de escopo (Fase 2 — depende do PDR-0008)

- Identificação automática, pela IA, dos campos variáveis da peça base.
- Extração automática dos campos sensíveis de cada caso a partir de
  documento anexado.
- Qualquer preenchimento automático que não passe por revisão manual
  antes de gerar a peça.

## Critérios de aceite

- Listagem exibe "Tipo de Peça" em vez de "Categoria" em todos os textos
  e filtros.
- Cada item da lista tem botão de visualizar e botão de baixar (PDF e
  DOCX).
- Fluxo de peças repetitivas gera N peças a partir de uma base, cada uma
  com os dados do cliente selecionado já preenchidos e os campos
  sensíveis editáveis manualmente antes de gerar.
