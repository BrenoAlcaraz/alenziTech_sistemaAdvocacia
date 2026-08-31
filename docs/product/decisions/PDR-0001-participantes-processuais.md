---
id: PDR-0001
title: Participantes processuais
status: accepted
partially_superseded_by: PDR-0013
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-31
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/product-vision-original.docx
  - docs/history/source-material/phase-1-functional-feedback.docx
  - docs/history/source-material/phase-2-consolidated-plan-v1.docx
---

# PDR-0001 — Participantes processuais

> **Parcialmente substituída por [PDR-0013](PDR-0013-partes-processo-modelo-simplificado.md)
> em 2026-08-31.** A exigência de três dimensões separadas (vínculo,
> posição estrutural, qualificação processual), a normalização do
> advogado como representante 1:N e a entidade própria de autoridade
> processual para juiz deixaram de ser a direção vigente — ver PDR-0013.
> As demais regras deste documento (multiplicidade de clientes, polos,
> terceiros e Ministério Público; reaproveitamento do cadastro de Cliente;
> apresentação em grupos dinâmicos) continuam válidas.

## Contexto

O cadastro de partes de um processo historicamente misturava três
conceitos diferentes em um único campo: o vínculo da pessoa com o
escritório, sua posição no processo e o nome jurídico que ela exerce
naquele caso. Essa mistura impedia representar corretamente situações
comuns na prática jurídica, como múltiplos clientes representados no
mesmo processo, múltiplas pessoas em um mesmo polo, terceiros,
Ministério Público e autoridades.

## Problema

Sem separar vínculo, posição estrutural e qualificação processual, o
sistema não consegue representar corretamente processos com mais de uma
parte por polo, não consegue evitar a duplicação de uma mesma pessoa
quando sua qualificação muda entre fases ou processos apensos, e não
consegue tratar adequadamente advogados, Ministério Público e
autoridades, que não são partes no sentido processual.

## Decisão

Um processo pode ter:

- mais de um cliente representado pelo escritório;
- mais de uma pessoa no polo ativo;
- mais de uma pessoa no polo passivo;
- terceiros;
- Ministério Público, admitindo pelo menos duas formas de atuação: como
  parte do processo ou como fiscal da ordem jurídica;
- um juiz ou outra autoridade, registrado separadamente das partes.

O cadastro deve separar obrigatoriamente três conceitos distintos:

1. **Vínculo com o escritório** — se a pessoa é cliente representado
   pelo escritório, parte contrária ou outro tipo de vínculo.
2. **Posição estrutural** — polo ativo, polo passivo, terceiro, ou
   atuação específica do Ministério Público. É a dimensão mais estável
   do vínculo.
3. **Qualificação processual** — o nome jurídico exercido pelo
   participante naquele processo ou fase, como requerente, requerido,
   exequente, executado, agravante, agravado, entre outros. É a
   dimensão que pode variar entre fases e recursos.

O advogado não é uma parte do processo. Ele é representante de um
participante. Cada participante pode possuir nenhum, um ou vários
representantes.

Advogados internos ao escritório devem reaproveitar o usuário ou membro
de equipe já cadastrado, sem criar uma ficha independente. Advogados
externos possuem nome, número da OAB, UF da OAB, telefone e e-mail como
dados principais; CPF não é obrigatório para esse cadastro.

Pessoas externas ao escritório (partes contrárias, terceiros e
representantes que não são clientes) podem ser pessoa física, pessoa
jurídica ou órgão público.

## Regras obrigatórias

- Um cliente já vinculado ao processo aparece automaticamente entre os
  participantes, sem exigir novo cadastro.
- O participante originado de um cliente reutiliza nome e CPF/CNPJ do
  cadastro de Cliente; esses dados não devem ser redigitados.
- No vínculo do processo, é registrada a posição estrutural, a
  qualificação processual e a indicação de representação pelo
  escritório para aquele cliente.
- Uma mudança de qualificação processual não duplica a pessoa: o mesmo
  participante mantém sua identidade e passa a refletir a qualificação
  atual no vínculo correspondente.
- Alterações relevantes de qualificação devem ser historicamente
  rastreáveis.
- Um outro processo, ou um processo apenso, pode registrar qualificação
  diferente para a mesma pessoa, sem que isso implique duplicidade de
  cadastro.
- Autoridades processuais são registradas separadamente das partes.
  O registro inicial de autoridade inclui: tipo (juiz), nome, vara ou
  órgão, e observação opcional.
- A apresentação dos participantes deve usar grupos dinâmicos por
  posição estrutural (por exemplo: polo ativo, polo passivo, terceiros,
  Ministério Público, autoridades), com adaptação responsiva para telas
  menores.

## Consequências

- A modelagem de participantes passa a exigir três dimensões
  relacionadas (vínculo, posição estrutural, qualificação processual)
  em vez de um único campo de "parte".
- Clientes vinculados ao processo deixam de exigir redigitação de dados
  pessoais já cadastrados.
- Advogados internos deixam de gerar fichas duplicadas em relação ao
  usuário ou membro de equipe já existente.
- A interface de participantes deixa de depender de um layout fixo de
  colunas e passa a depender de agrupamento dinâmico por posição.
- Fica estabelecida a necessidade de rastreabilidade histórica para
  mudanças relevantes de qualificação processual, o que impacta a
  modelagem de dados e não apenas a interface.

## Alternativas ou regras substituídas

O material de visão inicial (`product-vision-original.docx`) e o
feedback funcional pós-Fase 1 (`phase-1-functional-feedback.docx`)
descreviam uma abordagem baseada em colunas fixas de "autor" e "réu",
com o juiz eventualmente tratado como uma parte adicional dentro dessa
mesma listagem. Essa abordagem é substituída pela decisão consolidada
posterior: apresentação em grupos dinâmicos por posição estrutural, com
autoridades — incluindo o juiz — registradas em uma seção separada das
partes, e não como uma parte ou coluna adicional.

O plano técnico consolidado (`phase-2-consolidated-plan-v1.docx`) já
recomendava a apresentação em colunas ou grupos dinâmicos, sem limitar a
quantidade de participantes, o que é compatível com esta decisão e não
gera conflito.

## Fora do escopo desta decisão

- Suporte a relator, desembargador, perito e outras autoridades ou
  auxiliares além de juiz: mencionado nas fontes como evolução futura da
  seção de Autoridades, não como obrigação desta decisão.
- Desenho técnico dos models, tabelas ou migrations que implementarão
  esta decisão: pertence à arquitetura e à implementação, não a este
  PDR.
- Regras de permissão sobre quem pode cadastrar, editar ou visualizar
  participantes: tratadas como decisão de autorização, fora do escopo
  deste PDR de produto.
- Estrutura técnica detalhada do histórico de alterações de
  qualificação: este PDR exige rastreabilidade, mas não define o
  mecanismo técnico que a implementa.

## Critérios de aceite funcionais

- É possível registrar, em um mesmo processo, mais de um cliente
  representado pelo escritório, mais de uma pessoa no polo ativo, mais
  de uma no polo passivo, terceiros e o Ministério Público,
  simultaneamente.
- Um cliente já vinculado ao processo aparece automaticamente na lista
  de participantes, com nome e CPF/CNPJ preenchidos a partir do
  cadastro de Cliente, sem exigir nova digitação.
- É possível registrar Ministério Público como parte do processo ou
  como fiscal da ordem jurídica, distinguindo os dois casos.
- Um advogado é sempre registrado como representante vinculado a um
  participante, nunca como parte do processo.
- Um participante pode ter nenhum, um ou vários representantes
  registrados.
- O cadastro de advogado externo aceita nome, OAB, UF, telefone e
  e-mail sem exigir CPF.
- Um advogado interno ao escritório é vinculado ao usuário ou membro de
  equipe já existente, sem gerar uma segunda ficha.
- Uma mudança de qualificação processual do mesmo participante não gera
  um novo registro de pessoa, e a alteração relevante fica
  historicamente identificável.
- A mesma pessoa pode ter qualificações diferentes em processos ou
  apensos distintos, sem conflito entre os registros.
- A tela de participantes exibe grupos dinâmicos por posição estrutural
  e se adapta a telas menores.
- É possível registrar uma autoridade do tipo juiz com nome, vara ou
  órgão, e observação opcional, separadamente da lista de partes.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [product-vision-original.docx](../../history/source-material/product-vision-original.docx)
- [phase-1-functional-feedback.docx](../../history/source-material/phase-1-functional-feedback.docx)
- [phase-2-consolidated-plan-v1.docx](../../history/source-material/phase-2-consolidated-plan-v1.docx)
