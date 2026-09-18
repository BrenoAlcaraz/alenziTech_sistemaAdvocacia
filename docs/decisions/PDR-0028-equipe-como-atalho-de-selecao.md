---
id: PDR-0028
title: Equipe como atalho de seleção (substitui o vínculo dinâmico de Equipe)
status: accepted
owner: product-and-engineering
decision_date: 2026-09-18
last_reviewed: 2026-09-18
supersedes: []
complements:
  - PDR-0014
  - PDR-0020
  - PDR-0026
source_files: []
---

# PDR-0028 — Equipe como atalho de seleção

## Contexto

Havia uma regra de produto (registrada só em `docs/PRODUCT.md`, seção
"Equipe como integrante/participante/atribuído dinâmico", sem PDR
próprio) segundo a qual adicionar uma Equipe a um Processo (integrantes
habilitados, PDR-0014), a uma Tarefa (participantes) ou a um
Compromisso (participantes, PDR-0020) criava um vínculo dinâmico: quem
entrava na equipe depois entrava sozinho, quem saía perdia o acesso.
Implementada com `EquipeVinculada`/`VinculoIntegrante` e sinais de
`MembroEquipe` por app.

Problemas apontados pelo dono do produto:

1. se o usuário removia uma pessoa, a etiqueta da equipe continuava
   dizendo que a equipe toda estava lá;
2. em Processos, integrante habilitado dá acesso — novo membro de equipe
   ganhava acesso a processo sigiloso sem decisão humana.

## Decisão

- Equipe é apenas **atalho de seleção**: escolhê-la seleciona seus
  membros ativos (`MembroEquipe.ativo=True`, equipe `ativo=True`) como
  pessoas individuais. Nenhum vínculo com a equipe permanece.
- Em Processos (cartão "Integrantes") e na edição de Tarefas/Agenda, a
  escolha abre uma lista de conferência com todos marcados; o usuário
  desmarca e confirma. Na criação de Tarefas/Agenda, botões de equipe
  marcam as caixinhas de pessoas.
- O servidor valida cada usuário (elegível no contexto e membro ativo da
  equipe informada) e nunca confia no JS. Habilitações: as mesmas de
  antes em cada módulo; nenhuma nova.
- Substitui a decisão anterior de vínculo dinâmico. O grupo de chat
  automático por equipe (PDR-0026) **não muda**.

## Consequências

- `EquipeVinculada`, `VinculoIntegrante`, `apps/accounts/vinculo_equipe.py`
  e os sinais de `MembroEquipe` em processos/agenda/tarefas foram
  removidos; migration `accounts.0032` apaga as duas tabelas. As pessoas
  já materializadas continuam nas listas reais e viram individuais, sem
  perda.
- **Consequência aceita pelo dono do produto**: quem sai de uma equipe
  (ou é desativado nela) **não perde mais o acesso automaticamente** a
  processos/tarefas/compromissos onde foi adicionado; a remoção passa a
  ser manual, pessoa por pessoa.
- Em Agenda cada participante segue a confirmação de presença normal
  (PDR-0020); em Tarefas a equipe nunca é responsável.

## Fora do escopo desta decisão

Modo "acompanhar equipe", exceções lembradas, equipe como responsável,
mudança de habilitações e o chat por equipe.
