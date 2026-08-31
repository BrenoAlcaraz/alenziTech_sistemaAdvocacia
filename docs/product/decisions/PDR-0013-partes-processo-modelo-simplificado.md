---
id: PDR-0013
title: Partes de processo — modelo simplificado
status: accepted
owner: product-and-engineering
decision_date: 2026-08-31
last_reviewed: 2026-08-31
supersedes:
  - PDR-0011
partially_supersedes:
  - PDR-0001
source_files: []
---

# PDR-0013 — Partes de processo: modelo simplificado

## Contexto

A revisão estrutural de documentação conduzida a partir dos protótipos
funcionais (`docs/prototipos/processo-prototipo.html`) confrontou a
especificação validada nesses protótipos com dois PDRs em vigor:

- [PDR-0001](PDR-0001-participantes-processuais.md), baseado em material
  histórico de produto, que exige obrigatoriamente três dimensões
  separadas (vínculo com o escritório, posição estrutural, qualificação
  processual), advogado modelado como representante normalizado em
  relação 1:N distinto de parte, e autoridade processual (juiz) registrada
  em entidade própria, separada das partes;
- [PDR-0011](PDR-0011-taxonomia-representacao-participantes-processos.md),
  que complementa PDR-0001 com a taxonomia inicial de dez opções, a
  distinção interno/externo do advogado e o estado de classificação
  pendente do Cliente automático.

O protótipo, aba Partes, implementa algo mais simples: um único campo
"Tipo de parte" (as mesmas dez opções de PDR-0011, agrupadas visualmente
em Polo Ativo, Polo Passivo e Outros, porém como um único valor de
domínio — sem separar vínculo, posição estrutural e qualificação
processual), nome, CPF/CNPJ opcional, e um subformulário opcional de
advogado com dois campos de texto livre (nome, OAB), sem entidade própria,
sem vínculo a um `User` e sem distinção interno/externo. Juiz é apenas
mais uma opção do mesmo campo de papel, sem entidade de autoridade
separada.

Esse modelo simplificado contradiz diretamente as regras obrigatórias e os
critérios de aceite de PDR-0001 — não apenas os complementos de PDR-0011.
Esse alcance mais amplo foi identificado durante a redação desta decisão,
depois de o Product Owner já ter aprovado o modelo do protótipo em
resposta ao conflito registrado contra PDR-0011. Levado de volta ao
Product Owner nesses termos — substitui uma decisão apoiada em material
histórico de produto, não apenas um complemento posterior —, a
simplificação foi confirmada em 2026-08-31, com pleno conhecimento de que
o modelo de dados de PDR-0001 é parcialmente superado por esta decisão.

## Decisão

### Campo único de papel

`ParteProcesso` (ou equivalente) passa a registrar um único campo de papel
processual, com os dez valores já definidos na taxonomia de PDR-0011:

| Papel | Grupo visual |
| --- | --- |
| Autor | Polo Ativo |
| Embargante | Polo Ativo |
| Recorrente | Polo Ativo |
| Réu | Polo Passivo |
| Embargado | Polo Passivo |
| Recorrido | Polo Passivo |
| Terceiro Interessado | Outros |
| Ministério Público | Outros |
| Amicus Curiae | Outros |
| Juiz | Outros |

O agrupamento em Polo Ativo/Polo Passivo/Outros permanece como
apresentação visual, mas não constitui mais um campo de domínio separado
como em PDR-0011 — é derivado do único valor de papel.

Juiz continua não sendo modelado como parte no sentido de "lado" do
processo, mas, diferente de PDR-0001/PDR-0011, esta decisão não exige uma
entidade de autoridade processual separada: fica registrado com o mesmo
campo de papel, dentro de `ParteProcesso`. Distinguir juiz como autoridade
estruturalmente separada da lista de partes não é obrigação desta decisão.

### Advogado como texto livre

O advogado de uma parte não é mais uma entidade normalizada em relação
1:N, nem distingue interno de externo. É um subformulário opcional com
dois campos de texto associados diretamente à parte: nome do advogado e
OAB. Uma parte comporta, no máximo, um advogado registrado por este
formulário.

Quando a parte cadastrada corresponde ao Cliente do processo (por
CPF/CNPJ, seguindo a mesma regra de comparação de PDR-0011: ambos os
documentos não vazios, valores iguais após normalização, comparação
restrita a `Processo.cliente`), os campos de advogado são pré-preenchidos
automaticamente com os dados do responsável do processo — mas continuam
sendo os mesmos dois campos de texto, não uma referência normalizada a
`User`.

### Ministério Público

Ministério Público permanece uma das dez opções de papel. Esta decisão não
mantém o campo separado de "forma de atuação" (parte ou fiscal da ordem
jurídica) aprovado em PDR-0001/PDR-0011; se essa distinção for necessária,
exige nova decisão.

## Relação com PDR-0001 e PDR-0011

Esta decisão substitui integralmente o modelo de dados de PDR-0001 e
PDR-0011 para partes de processo: a separação obrigatória entre vínculo,
posição estrutural e qualificação processual; a normalização de
representantes em relação 1:N; a distinção interno/externo do advogado; a
entidade própria de autoridade processual para juiz; e o estado de
classificação pendente do Cliente automático deixam de ser a direção
vigente.

Nenhum outro ponto de PDR-0001 ou PDR-0011 alheio ao desenho de
`ParteProcesso` e à representação de advogado é alterado por esta decisão
— por exemplo, a regra de que o Cliente do processo aparece entre os
participantes sem redigitação de dados permanece válida em espírito,
ainda que sua materialização técnica mude, conforme "Pontos em aberto"
abaixo.

## Consequências

- `ParteProcesso` simplifica para um único campo de papel, em vez de
  posição estrutural e qualificação processual separadas;
- a entidade normalizada de representante (`RepresentanteParte`) e a
  distinção interno/externo deixam de ser a direção vigente; advogado passa
  a ser texto livre associado à parte;
- o histórico de mudança de qualificação processual (`HistoricoClassificacaoParte`)
  e o estado de classificação pendente do Cliente automático deixam de ser
  exigidos por esta decisão;
- o código já implementado conforme PDR-0001/PDR-0011/WI-0006
  (`ParteProcesso` com três dimensões, `RepresentanteParte`,
  `HistoricoClassificacaoParte`, `AutoridadeProcessual`) precisa de um
  Work Item de reversão/simplificação para refletir este modelo; até que
  esse Work Item seja concluído,
  [docs/delivery/current-state/processos.md](../../delivery/current-state/processos.md)
  registra a divergência entre o modelo implementado e o modelo aprovado.

## Fora do escopo desta decisão

- apensos e relação Processo ↔ Processo, conforme
  [PDR-0012](PDR-0012-relacao-simetrica-processos-apensos.md), não alterado;
- autorização e escopo de Processos, conforme
  [PDR-0010](PDR-0010-autorizacao-escopo-responsabilidade-processos.md), não
  alterado por esta decisão;
- diretório global de advogados externos;
- IA e Laboratório.

## Pontos em aberto

- Se o Cliente vinculado ao processo (`Processo.cliente`) deve ganhar
  automaticamente um registro correspondente em `ParteProcesso` não é
  definido por esta decisão — o protótipo não demonstra esse comportamento
  de forma inequívoca. Fica como ponto em aberto até nova decisão.

## Critérios de aceite funcionais

- uma parte é cadastrada com um único campo de papel, dentre as dez
  opções definidas, exibidas em três grupos visuais;
- uma parte aceita, no máximo, um advogado, registrado como nome e OAB em
  texto livre, sem vínculo a `User`;
- quando a parte corresponde ao Cliente do processo por CPF/CNPJ, os
  campos de advogado são pré-preenchidos automaticamente;
- Ministério Público é uma opção válida de papel;
- juiz é uma opção válida de papel, sem exigir entidade de autoridade
  processual separada.

## Fontes

- decisão direta do Product Owner registrada em 2026-08-31, durante a
  revisão estrutural de documentação a partir dos protótipos funcionais;
- [docs/prototipos/processo-prototipo.html](../../prototipos/processo-prototipo.html),
  aba Partes;
- [PDR-0001 — Participantes processuais](PDR-0001-participantes-processuais.md)
  (parcialmente substituída por esta decisão nos pontos de modelagem de partes e
  advogado);
- [PDR-0011 — Taxonomia e representação de participantes de Processos](PDR-0011-taxonomia-representacao-participantes-processos.md)
  (substituída por esta decisão).
