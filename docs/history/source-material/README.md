---
title: Fontes originais do produto
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Fontes originais do produto

## Finalidade

Os arquivos deste diretório são preservados em formato original para fins
de rastreabilidade. Eles registram o pensamento, os requisitos e as
decisões técnicas em diferentes momentos da evolução do produto e não
devem ser modificados após serem adicionados ao histórico.

## Catálogo

| Arquivo | Origem | Classificação | Autoridade atual | Uso esperado |
|---|---|---|---|---|
| `product-vision-original.docx` | Visão inicial elaborada pelo especialista jurídico. | Visão histórica inicial do produto. | Não canônica; perde precedência diante de decisões posteriores aprovadas. | Compreender objetivos originais e funcionalidades desejadas. |
| `phase-1-functional-feedback.docx` | Avaliação do especialista jurídico após a Fase 1. | Feedback funcional e proposta de evolução. | Fonte importante de requisitos, mas alterações posteriores expressamente aprovadas têm precedência. | Rastrear problemas percebidos e necessidades jurídicas. |
| `phase-2-consolidated-plan-v1.docx` | Consolidação técnica produzida após análise das anotações. | Proposta técnica histórica. | Não integralmente canônica; mistura recomendações, itens aprovados e pontos ainda sujeitos a validação. | Entender a transição da Fase 1 para a Fase 2. |
| `2026-08-05-decisoes-funcionais-consolidadas-original.txt` | Consolidação posterior das decisões funcionais para desenvolvimento. | Fonte primária das decisões funcionais aprovadas para os futuros PDRs. | Fonte de decisão até que seu conteúdo seja formalizado nos respectivos PDRs; após isso, os PDRs terão precedência. | Criação e verificação dos PDR-0001 a PDR-0009. |
| `2026-08-05-ficha-tecnica-arquitetura-snapshot.txt` | Ficha técnica produzida a partir de determinado estado do projeto. | Snapshot técnico histórico. | Não canônica e parcialmente superada; o código e auditorias de commits posteriores podem divergir. | Contexto técnico e comparação histórica, nunca current-state vigente. |

## Regra de preservação

- não editar os arquivos originais;
- não corrigir terminologia dentro deles;
- não substituir o original por um resumo;
- criar novas decisões canônicas em outros diretórios (PDRs, ADRs,
  especificações de módulos, current-state);
- usar o manifesto SHA-256 (`docs/history/SHA256SUMS.txt`) para detectar
  alterações acidentais.
