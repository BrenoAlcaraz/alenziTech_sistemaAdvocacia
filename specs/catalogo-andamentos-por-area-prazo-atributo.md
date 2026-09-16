# Spec — Catálogo de andamentos por área + prazo como atributo + aba Prazos funcional

## Objetivo

Reestruturar o campo "tipo de andamento" do módulo Processos — removendo
"Prazo" como tipo e reorganizando em catálogo por área jurídica — e tornar a
aba "Prazos" do detalhe do processo funcional, agregando automaticamente os
prazos marcados nos andamentos.

Independente da spec parada
[agenda-prazos-processuais-automaticos.md](agenda-prazos-processuais-automaticos.md)
(bloqueada aguardando validação jurídica externa, cobre cálculo automático de
prazo em dias úteis/feriados via API/IA). Esta feature não reabre esse
escopo: é só rastreabilidade manual, sem nenhum cálculo de data.

## Estado atual (contexto técnico)

- `MovimentacaoProcessual` (`apps/processos/models.py`) tem campo `tipo`
  (`TIPO_CHOICES`, default `"andamento"`) com choices genéricas: andamento,
  prazo, decisao, audiencia, outro.
- `tipo="prazo"` hoje é só categoria de exibição (badge) — usa a mesma data
  genérica do andamento, sem lógica própria.
- Aba "Prazos" do detalhe do processo (`templates/processos/detalhe.html`)
  está hardcoded vazia ("Nenhum prazo cadastrado."), sem agregação real nem
  contexto passado pela view.
- `Processo.area_direito` já existe com 9 valores: Cível, Consumidor,
  Trabalhista, Sucessões, Penal, Administrativo, Tributário, Família, Outro.
- `Processo.prazo_proximo` é campo manual único (usado por Dashboard/Agenda),
  preenchido opcionalmente ao lançar andamento via checkbox "atualizar
  próximo prazo".
- Padrão de referência de implementação: módulo Partes já usa `<select>`
  único com `<optgroup>` (`ParteProcessoForm.GRUPOS_PAPEL`).

## Comportamento esperado / regras de negócio

1. **Prazo deixa de ser tipo, vira atributo.** Remove "Prazo" do enum
   `tipo`. Novo campo `data_prazo` (data, opcional) em
   `MovimentacaoProcessual`, independente do `tipo` — qualquer andamento, de
   qualquer tipo/catálogo, pode ter esse campo preenchido.

2. **Vínculo opcional de origem do prazo.** Ao marcar `data_prazo` num
   andamento, permitir selecionar opcionalmente qual andamento anterior do
   mesmo processo originou aquele prazo (FK opcional auto-referenciada em
   `MovimentacaoProcessual`) — ex.: o Despacho que determinou "5 dias",
   vinculado ao andamento de Intimação/Publicação em Diário Oficial que
   efetivamente disparou a contagem.
   - Sem cálculo automático de data — o usuário sempre digita a data final
     já calculada por ele.
   - Motivo: no processo civil/trabalhista/penal, um prazo determinado por
     despacho só começa a contar a partir da intimação/publicação; a data
     final só é conhecida nesse segundo momento.
   - Vínculo é só para rastreabilidade/exibição, e prepara terreno para
     quando a spec parada for retomada, sem exigir nova migration na
     ocasião.

3. **Migração de dados existentes.** Andamentos com `tipo="prazo"`: copiar
   `data` para o novo campo `data_prazo`, reclassificar `tipo` para
   `"outro"`. Os demais 4 valores legados (andamento, decisao, audiencia,
   outro) não são migrados — continuam com o texto antigo; só andamentos
   novos usam o catálogo novo.

4. **Novo catálogo por área jurídica**, substituindo as choices genéricas
   atuais. Um único campo `<select>` com `<optgroup>`: grupo da área do
   processo (`Processo.area_direito`) + grupo "Genéricos" sempre visível
   (Despacho, Decisão interlocutória, Perícia — presentes nas 3 listas
   abaixo).

   **Cível:** Petição inicial; Despacho; Decisão interlocutória; Expedição
   de mandado (citação, penhora, avaliação, levantamento de valores, carta
   precatória); Retorno de citação; Intimação; Contestação; Reconvenção;
   Exceção de pré-executividade; Réplica; Quesitos técnicos; Perícia; Ata de
   audiência; Alegações finais; Sentença; Embargos de declaração; Apelação;
   Contrarrazões; Agravo de instrumento; Agravo interno; Recurso adesivo;
   Acórdão; Recurso especial (STJ); Recurso extraordinário (STF); Agravo em
   recurso especial/extraordinário; Embargos de divergência; Petição (mero
   expediente); Juntada de documento; Certidão; Homologação (acordo,
   transação, cálculos); Trânsito em julgado; Cumprimento de
   sentença/execução; Impugnação; Penhora/constrição de bens; Arquivamento;
   Desarquivamento.

   **Trabalhista:** Reclamação trabalhista (petição inicial); Despacho;
   Decisão interlocutória; Expedição de mandado (citação, penhora,
   avaliação, levantamento de valores, carta precatória); Retorno de
   citação (notificação inicial); Intimação; Contestação; Reconvenção;
   Réplica; Quesitos técnicos; Perícia; Ata de audiência; Razões finais;
   Sentença; Embargos de declaração; Recurso ordinário (RO); Contrarrazões;
   Agravo de instrumento; Acórdão; Recurso de revista (RR); Embargos ao
   TST; Recurso extraordinário (STF); Petição (mero expediente); Juntada de
   documento; Certidão; Homologação (acordo, transação, cálculos); Trânsito
   em julgado; Liquidação de sentença; Execução; Impugnação;
   Penhora/constrição de bens; Agravo de petição; Habilitação de crédito
   (falência/recuperação judicial do executado); Arquivamento;
   Desarquivamento.

   **Penal:** Inquérito policial/termo circunstanciado; Denúncia/
   queixa-crime; Decisão (recebimento ou rejeição da denúncia/queixa);
   Expedição de mandado (citação, busca e apreensão, prisão); Retorno de
   citação; Intimação; Resposta à acusação; Réplica (rito do Júri — art.
   409 CPP); Decisão (absolvição sumária); Quesitos técnicos; Perícia;
   Pronúncia/impronúncia (rito do Júri); Ata de audiência (instrução e
   julgamento); Interrogatório; Alegações finais; Sentença; Embargos de
   declaração; Apelação; Recurso em sentido estrito (RESE); Contrarrazões;
   Acórdão; Carta testemunhável; Habeas corpus; Recurso especial (STJ);
   Recurso extraordinário (STF); Embargos infringentes ou de nulidade;
   Revisão criminal (ação autônoma, não recurso técnico — incluída na fase
   recursal por praticidade); Sessão de julgamento (Plenário do Júri);
   Petição (mero expediente); Juntada de documento; Certidão; Homologação
   (transação penal, suspensão condicional do processo); Trânsito em
   julgado; Guia de execução penal; Progressão/regressão de regime;
   Livramento condicional; Remição de pena; Agravo em execução; Extinção
   da punibilidade; Arquivamento (do inquérito ou definitivo dos autos);
   Desarquivamento.

5. **Áreas sem catálogo próprio** (Consumidor, Sucessões, Administrativo,
   Tributário, Família, Outro): usam a lista Cível como catálogo padrão,
   mais o grupo Genéricos.

6. **Aba "Prazos" funcional.** Agrega automaticamente todos os andamentos
   do processo com `data_prazo` preenchido, em linha do tempo, mostrando:
   - data do prazo em destaque visual (mais chamativa que o resto);
   - tipo/nome do andamento relacionado;
   - todos os prazos (passados e futuros), com estilo visual distinto para
     vencidos;
   - estado vazio com mensagem quando não houver nenhum.

   O prazo continua aparecendo também na aba "Andamentos" (visão geral, sem
   ser o foco ali).

7. **`Processo.prazo_proximo` automático.** Passa a ser calculado
   automaticamente como o `data_prazo` mais próximo entre os andamentos do
   processo — remove o checkbox manual "atualizar próximo prazo" do
   formulário de andamento. Continua alimentando Dashboard/Agenda
   normalmente.

## Fora do escopo

- Cálculo automático de data de prazo (dias úteis, feriados, recesso
  forense, API, IA) — spec parada
  [agenda-prazos-processuais-automaticos.md](agenda-prazos-processuais-automaticos.md)
  continua bloqueada.
- Geração de subtítulo por IA para itens genéricos — direção futura,
  sujeita a PDR-0008.
- Exibir Intimações (`Intimacao.prazo_manifestacao`) na aba Prazos.

## Critérios de aceite

- "Prazo" não existe mais como opção de tipo de andamento.
- Campo de data de prazo disponível em qualquer andamento, com vínculo
  opcional a um andamento de origem.
- Formulário de tipo mostra catálogo agrupado por área do processo +
  genéricos.
- Aba Prazos mostra timeline real (data em destaque, vencidos distintos) com
  estado vazio quando aplicável.
- `Processo.prazo_proximo` reflete automaticamente o prazo mais próximo
  entre os `data_prazo` dos andamentos do processo.
- Andamentos existentes com `tipo="prazo"` migrados: `data` copiada para
  `data_prazo`, `tipo` reclassificado para `"outro"`.
