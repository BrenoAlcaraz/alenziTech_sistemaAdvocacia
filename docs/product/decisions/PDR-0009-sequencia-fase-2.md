---
id: PDR-0009
title: Sequência revisada da Fase 2
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-13
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/2026-08-05-ficha-tecnica-arquitetura-snapshot.txt
---

# PDR-0009 — Sequência revisada da Fase 2

## Contexto

A Fase 2 reúne um conjunto amplo de entregas — permissões, modelagem de
partes, andamentos, tarefas, agenda, financeiro, custas, honorários,
painel do gestor e assistente/laboratório — que possuem dependências
reais entre si. Sem uma ordem explícita, existe risco de construir
módulos avançados sobre uma base de acesso e integridade ainda
incorreta.

## Problema

Iniciar módulos como financeiro, painel do gestor ou assistente antes de
consolidar permissões e a modelagem de participantes processuais
aumenta o risco de retrabalho, de exposição indevida de dados entre
usuários e tenants, e de regras de negócio construídas sobre suposições
que ainda não foram validadas.

## Decisão

A Fase 2 segue a seguinte ordem de dependência entre rodadas:

1. Rodada 2.1 — Permissões e integridade dos vínculos.
2. Rodada 2.2A — Modelagem de clientes, processos e participantes.
3. Rodada 2.2B — Fluxos e interfaces de clientes e processos.
4. Rodada 2.3 — Andamentos, documentos e prazos.
5. Rodada 2.4 — Tarefas e Agenda.
6. Rodada 2.5 — Núcleo financeiro.
7. Rodada 2.6 — Custas e solicitações.
8. Rodada 2.7 — Honorários e relatórios.
9. Rodada 2.8 — Painel do gestor e atividade.
10. Rodada 2.9 — Assistente e Laboratório.

## Regras obrigatórias

- Esta sequência representa dependências de produto entre as rodadas,
  não uma evidência de que qualquer rodada esteja concluída.
- O estado real de conclusão de cada rodada é responsabilidade de
  [docs/delivery/current-state.md](../../delivery/current-state.md), não
  deste PDR.
- Uma rodada pode ser dividida internamente em tarefas e mini-etapas,
  desde que a ordem entre rodadas seja respeitada.
- Migrations relevantes produzidas em qualquer rodada exigem auditoria e
  revisão antes de aplicação.
- A inteligência artificial (Rodada 2.9) vem depois da estrutura
  jurídica e administrativa estar consolidada, em linha com
  [PDR-0008](PDR-0008-ia-apos-nucleo-funcional.md).

## Consequências

- Qualquer planejamento de execução da Fase 2 deve respeitar esta ordem
  de dependência entre rodadas, mesmo que o ritmo interno de cada
  rodada varie.
- A divisão de Rodada 2.2 em 2.2A (modelagem) e 2.2B (fluxos e
  interface) passa a ser a referência oficial de produto para essa
  etapa.
- Roadmaps operacionais futuros devem refletir esta sequência de
  dependência, e não uma ordem alternativa, salvo substituição explícita
  por um novo PDR.
- A auditoria e revisão de migrations passa a ser uma condição
  obrigatória antes de aplicar mudanças de schema em qualquer rodada.

## Alternativas ou regras substituídas

Esta sequência substitui roadmaps históricos anteriores quando houver
divergência entre eles e a ordem aqui registrada. Em particular, a
ficha técnica (`2026-08-05-ficha-tecnica-arquitetura-snapshot.txt`)
registra a mesma ordem de dependência (Rodada 2.1 antes de 2.2A, antes
de 2.2B) como confirmação arquitetural, o que é compatível com esta
decisão e não representa conflito. Onde qualquer plano ou anotação
anterior sugerir uma ordem diferente — por exemplo, iniciar financeiro,
painel ou assistente antes de permissões e modelagem de partes — esta
sequência prevalece.

## Fora do escopo desta decisão

- O conteúdo funcional detalhado de cada rodada: tratado nos PDRs
  específicos de cada tema (PDR-0001 a PDR-0008) e em especificações de
  módulo futuras.
- O cronograma com datas ou prazos de entrega: não é definido por este
  PDR.
- O estado real de execução de cada rodada: será registrado em
  current-state, não neste documento.
- Decisões técnicas de arquitetura sobre como dividir uma rodada em
  tarefas: pertence à execução e ao planejamento operacional, não a este
  PDR de produto.

## Critérios de aceite funcionais

- Nenhuma rodada posterior é iniciada como substituta de uma rodada
  anterior sem que a rodada anterior tenha sido tratada.
- A Rodada 2.1 (permissões e integridade dos vínculos) é tratada como
  pré-requisito de produto para as rodadas seguintes.
- A Rodada 2.9 (Assistente e Laboratório) é tratada como a última rodada
  da sequência, posterior à consolidação do núcleo jurídico e
  administrativo.
- Qualquer migration relevante gerada durante a Fase 2 passa por
  auditoria e revisão antes de ser aplicada.
- Um roadmap operacional que divirja desta ordem de dependência é
  identificado como desatualizado em relação a este PDR, até que um novo
  PDR o substitua.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [2026-08-05-ficha-tecnica-arquitetura-snapshot.txt](../../history/source-material/2026-08-05-ficha-tecnica-arquitetura-snapshot.txt)
