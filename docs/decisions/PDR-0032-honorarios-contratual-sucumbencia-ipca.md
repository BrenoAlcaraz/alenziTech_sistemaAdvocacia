---
id: PDR-0032
title: Honorários — formulário contratual/sucumbência, êxito e IPCA
status: accepted
owner: product-and-engineering
decision_date: 2026-09-21
last_reviewed: 2026-09-21
supersedes: []
complements:
  - PDR-0007
  - PDR-0021
  - PDR-0022
  - PDR-0029
source_files: []
---

# PDR-0032 — Honorários: contratual, sucumbência, êxito e IPCA

## Contexto

Revisão do sócio de 2026-09-20: o formulário de honorários misturava
tipos (contratual, sucumbencial, êxito, outro) e não cobria contrato com
parcelamento/recorrência nem o êxito como parte do contrato.

## Decisão

1. **Dois tipos para criar:** Contratual e Sucumbência. Registros
   anteriores `exito`/`outro` seguem visíveis e editáveis; não se criam
   novos.
2. **Contratual** é um único registro com "valor", "por êxito" ou
   "valor + êxito".
   - **Valor:** pagamento único (com data), parcelado (total dividido em N
     parcelas mensais) ou recorrente (mesmo valor, mensal/anual; duração
     por quantidade, data final ou indeterminada). Parcelado e recorrente
     geram receitas pendentes (categoria Honorários) pelo gerador do
     PDR-0021, vinculadas ao honorário; a última parcela absorve o
     arredondamento. O recebimento dessas receitas acontece nos
     lançamentos, não pela confirmação do honorário. Gerados os
     lançamentos, valor/datas/parcelamento só mudam neles. Cancelar o
     honorário cancela só as receitas pendentes ainda não vencidas.
   - **Por êxito:** percentual + base "pelo ganho" (atua pelo
     autor/reconvindo) ou "pela economia" (atua pelo réu). Processo
     obrigatório. É só anotação: sem lançamento e sem valor a receber
     calculado; a confirmação de recebimento não se aplica.
   - Confirmar recebimento segue exclusivo do Administrador (PDR-0007).
3. **Sucumbência:** forma valor fixo, percentual sobre a **condenação** ou
   valor fixo + percentual (substitui o "percentual sobre o valor da
   causa" do PDR-0029). Juros e correção monetária têm cada um data
   inicial e final de incidência (final vazia = até hoje). O índice passa
   a incluir **IPCA**, com taxa mensal informada à mão (sem integração
   externa, como INPC/IGP-M/Selic).
4. **Aviso de êxito na sucumbência:** contratos de êxito "pelo ganho"
   ativos do mesmo processo aparecem como "Você tem X% de êxito a
   receber", calculado sobre a condenação corrigida e somado ao total a
   receber (uma linha por contrato; sucumbência e êxito separados).
   "Pela economia" não entra. Sem valor de condenação (forma só fixa) não
   há base, então não há aviso. O êxito embutido na sucumbência
   (PDR-0029) deixa de se criar; o de registros anteriores é preservado.

## Fora do escopo

Integração com índices externos (IBGE/BCB); cálculo de êxito na sentença
além do aviso; alteração das regras de recebimento parcial (PDR-0022).
