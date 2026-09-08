# Spec — Geração automática de prazos processuais na Agenda

Status: **parada aguardando validação jurídica externa** — não implementar até
o critério de aceite de validação do catálogo ser cumprido. Pesquisa de apoio
em [docs/research/prazos-processuais-brasil.md](../docs/research/prazos-processuais-brasil.md)
(rascunho, não é aconselhamento jurídico).

## Objetivo

Quando um andamento processual com prazo é lançado, o sistema calcula e cria
automaticamente o compromisso de prazo correspondente na Agenda do
responsável pelo processo — sem depender de IA jurídica e sem exigir aceite
de quem recebe. Reduz o risco de perda de prazo por esquecimento de
lançamento manual na Agenda.

## Comportamento esperado

### Origem do prazo — regra do sistema, não IA
- Ao lançar um andamento (`adicionar_movimentacao`, dentro de um processo já
  existente — não na criação do processo), quem lança escolhe um "tipo de
  ato processual" de um catálogo.
- Se o tipo já tem prazo fixo em lei, o número de dias é preenchido pelo
  sistema (catálogo).
- Se o tipo é de prazo definido pelo juiz no caso concreto (não fixo em
  lei), quem lança digita o número de dias — a pessoa já leu a decisão pra
  saber que precisa lançar o andamento, então já sabe o número.
- Em nenhum dos dois casos o sistema lê ou interpreta documento sozinho.
  "Abrir o PDF da decisão e extrair o número automaticamente" é IA
  jurídica (PDR-0008) — registrado como fase futura, fora desta spec.

### Responsável e ausência de aceite
- O compromisso de prazo gerado é sempre atribuído como `responsavel` ao
  `Processo.responsavel` (PDR-0014) — nunca como participante.
- Por isso nunca passa pelo fluxo de confirmação de presença (esse fluxo é
  só para participante convidado, ex. reunião). Resolve diretamente o
  receio de "aceite" levantado pelo sócio: prazo processual nunca precisa
  ser aceito, só compromisso social/interno com convidado.

### Model e apresentação
- Reaproveita `Compromisso` já existente com `tipo="prazo"` — não cria
  model paralelo de prazo.
- Compromisso gerado pelo sistema tem título e cor diferenciados do
  criado manualmente, para se destacar na lista (ex.: título prefixado
  "Andamento processual: <tópico>" vs. o título livre digitado à mão).
- Nasce direto na Agenda do responsável, sem etapa de confirmação — a
  correção de erro fica na facilidade de editar/cancelar depois, igual
  qualquer outro compromisso hoje.

### Termo inicial da contagem
- Usa a data do andamento (`MovimentacaoProcessual.data`, já preenchida
  por quem lança, pode ser retroativa) como termo inicial — não a data em
  que a pessoa salvou o registro no sistema.
- Contagem em dias úteis (art. 219, CPC) para os tipos cíveis do
  catálogo.

### Feriados e recesso forense
- Automatiza: feriados nacionais civis + recesso forense federal de fim
  de ano (20/12 a 20/1 — art. 220 CPC + Resolução CNJ 244/2016, regra
  federal única, sem variação por tribunal).
- Não automatiza feriado forense de comarca/município (aniversário de
  cidade, portaria local) — pesquisa confirmou que não existe fonte
  pública/API consolidada para isso; cada tribunal publica portaria
  anual própria em PDF, sem padrão nacional.
- Todo compromisso de prazo gerado automaticamente exibe um aviso visível
  no próprio card (mesmo local do destaque visual do tópico anterior):
  "Data calculada sem considerar feriado forense local — confirme na sua
  comarca." — não é um modal nem uma etapa extra, é texto sempre visível
  junto da data.

### Motor de cálculo — só o padrão comum
- Cobre só o padrão "N dias (úteis) contados a partir da data do
  andamento X". Casos que não seguem esse padrão (ex.: prazo com janela
  aberta sem contagem fixa — embargos de terceiro; prazo vinculado a uma
  audiência, não a uma contagem de dias — contestação trabalhista) ficam
  fora do motor automático nesta versão e continuam sendo lançados
  manualmente na Agenda, como hoje.

## Regras de negócio relevantes

- Catálogo do v1 cobre só a área **cível** (CPC) — é a única com
  contagem de dias úteis/corridos confirmada por texto literal de lei
  (art. 219, CPC) na pesquisa de apoio.
- Trabalhista e demais áreas do direito ficam fora até confirmação
  jurídica formal (ver "Fora do escopo").
- Cada linha do catálogo cível também precisa de validação por advogado
  antes de ativar — a pesquisa já identificou itens que dependem de
  inferência (regra geral de recurso, não remissão literal no artigo
  específico: agravo de instrumento, agravo interno, recurso especial/
  extraordinário) e não apenas de leitura direta.

## Fora do escopo

- Extração automática de prazo a partir de leitura de documento/PDF —
  IA jurídica, condicionada aos pré-requisitos do PDR-0008 (autorização,
  escopo de dados, acesso seguro a documentos, dados processuais
  estruturados, histórico e rastreabilidade). Registrado aqui como
  direção futura desejada, não descartada — só posterior a esta versão
  baseada em regra.
- Catálogo trabalhista e de outras áreas do direito além do cível —
  aguarda confirmação jurídica específica (a pesquisa não conseguiu
  confirmar por lei se a contagem trabalhista é em dias úteis ou
  corridos).
- Feriado forense de comarca/município automatizado — **direção futura
  desejada**, mesmo que exija curadoria manual (ingestão de portaria por
  tribunal, atualização anual) em vez de fonte automatizada única — não
  descartada, só fora desta primeira versão por falta de fonte
  consolidada disponível hoje.
- Casos de prazo fora do padrão "N dias após andamento" (janela aberta,
  vinculado a audiência) — continuam manuais.
- Qualquer alteração ao fluxo de participantes/confirmação de presença já
  implementado (issues #8/#9) — este prazo nunca usa esse fluxo.

## Critérios de aceite

- Nenhum prazo do catálogo cível vira regra ativa em produção sem
  confirmação item por item por advogado com OAB ativa — **bloqueante**,
  não é só "o código funciona".
- Lançar um andamento de tipo com prazo fixo em lei pré-preenche o
  número de dias; lançar um de prazo definido pelo juiz pede o número
  manualmente.
- Compromisso de prazo gerado aparece na Agenda do responsável do
  processo, nunca de um participante, sem etapa de aceite.
- Compromisso gerado é visualmente distinguível de um criado manualmente
  (título e cor próprios) e exibe o aviso sobre feriado forense local.
- Cálculo considera dias úteis, feriados nacionais civis e o recesso
  forense federal (20/12–20/1).
- Andamento de tipo trabalhista, de outra área do direito, ou fora do
  padrão "N dias após andamento" não gera prazo automático nesta versão.

## Retomada desta spec

Bloqueada em: validação jurídica do catálogo cível (ver pesquisa de
apoio). Ao retomar, atualizar o catálogo desta spec com o que o advogado
confirmar/corrigir antes de abrir tickets de implementação.
