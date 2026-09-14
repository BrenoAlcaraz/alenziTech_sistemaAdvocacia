---
id: PDR-0023
title: Partes — catálogo de papéis estendido com pares por tipo de ação
status: accepted
owner: product-and-engineering
decision_date: 2026-09-14
last_reviewed: 2026-09-14
supersedes: []
complements:
  - PDR-0013
source_files: []
---

# PDR-0023 — Partes: catálogo de papéis estendido com pares por tipo de ação

## Contexto

PDR-0013 define o modelo vigente de Partes: um único campo `papel` com
10 opções fixas (Autor, Embargante, Recorrente, Réu, Embargado,
Recorrido, Terceiro Interessado, Ministério Público, Amicus Curiae,
Juiz), agrupadas visualmente em Polo Ativo/Polo Passivo/Outros. Na
reunião de 13/09, o sócio pediu nomenclatura própria por tipo de ação
processual (execução usa Exequente/Executado, não Autor/Réu; trabalhista
usa Reclamante/Reclamado; mandado de segurança usa Impetrante/Impetrado
etc.) em vez do par genérico Autor/Réu para todos os casos.

## Problema

O par genérico Autor/Réu é impreciso para processos que não são ação de
conhecimento comum — nomear as partes de uma execução como "Autor" e
"Réu" em vez de "Exequente" e "Executado" não corresponde à terminologia
processual real, o que já havia motivado parte da complexidade do
modelo anterior (PDR-0001/PDR-0011, substituído por ser
excessivamente genérico/complexo). A simplificação do PDR-0013 foi na
direção certa (um único campo, sem normalização), mas reduziu também a
precisão terminológica que o catálogo antigo tentava capturar.

## Decisão

O catálogo de `papel` (`ParteProcesso.PAPEL_CHOICES`) **mantém** Autor/
Réu para o caso genérico e **adiciona** 10 pares específicos por tipo de
ação, sem remover nem renomear nenhuma opção existente (exceto Amicus
Curiae, tratado à parte abaixo):

**Polo Ativo** — Autor, Embargante, Recorrente (já existentes) +
Exequente, Requerente, Reclamante, Agravante, Impugnante, Reconvinte,
Excipiente, Impetrante, Inventariante.

**Polo Passivo** — Réu, Embargado, Recorrido (já existentes) +
Executado, Requerido, Reclamado, Agravado, Impugnado, Reconvindo,
Excepto, Impetrado, Inventariado.

**Outros** — Terceiro Interessado, Ministério Público, Juiz (mantidos);
**Amicus Curiae removido** do catálogo — decisão explícita desta mesma
reunião, sem substituto.

Quem cadastra uma Parte escolhe o par correspondente ao tipo de ação do
processo (ex.: execução → Exequente/Executado); nada no sistema infere
esse par automaticamente a partir de outro campo do processo — a
escolha continua sendo manual, exatamente como já era para os 10
papéis originais.

## Regras obrigatórias

- Nenhum papel do catálogo original (PDR-0013) muda de grupo visual
  (`GRUPO_POR_PAPEL`) ou é removido, exceto Amicus Curiae.
- Os pares novos seguem o mesmo modelo de dado do PDR-0013: um único
  campo `papel` por Parte, sem normalização em entidade própria, sem
  vínculo/posição estrutural/qualificação separados — o PDR-0013
  continua vigente para a forma do modelo, só o catálogo de valores
  válidos é estendido.
- Uma Parte já cadastrada com `papel="amicus_curiae"` antes desta
  decisão não é migrada nem apagada — o valor deixa de ser oferecido no
  formulário, mas registro histórico existente não é alterado
  retroativamente.

## Consequências

- `docs/modules/processos.md`, seção "Partes (PDR-0013 — modelo
  vigente)", passa a registrar a lista completa de papéis e a nota de
  que este PDR estende (não substitui) o PDR-0013.
- `docs/STATUS.md`, linha Processos, passa a registrar o catálogo
  estendido como implementado.

## Fora do escopo desta decisão

- Qualquer inferência automática do papel a partir da área do
  direito/fase do processo — continua manual.
- Reintrodução do modelo de três dimensões do PDR-0001/PDR-0011
  (vínculo/posição estrutural/qualificação, representantes
  normalizados) — permanece descartado.
- Catálogo de autoridades além de juiz (relator, desembargador,
  perito) — ponto em aberto já registrado em `docs/modules/processos.md`,
  não tratado aqui.

## Critérios de aceite funcionais

- O formulário de Parte oferece os 10 pares novos, agrupados
  corretamente em Polo Ativo/Polo Passivo, ao lado de Autor/Réu.
- "Amicus Curiae" não aparece mais como opção em nenhum formulário.
- Todos os papéis já existentes antes desta decisão continuam
  funcionando sem migração de dado.

## Fontes

- Conversa desta sessão (reunião de 13/09, repassada pelo Product
  Owner); spec `specs/processos-ajustes-formulario-detalhe.md` (apagada
  após a promoção deste PDR, conforme
  [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
