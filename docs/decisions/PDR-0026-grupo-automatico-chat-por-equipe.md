---
id: PDR-0026
title: Grupo automático de Chat por Equipe
status: accepted
owner: product-and-engineering
decision_date: 2026-09-14
last_reviewed: 2026-09-14
supersedes: []
complements: []
source_files: []
---

# PDR-0026 — Grupo automático de Chat por Equipe

## Contexto

`docs/PRODUCT.md`, seção Chat, registrava "Equipe não gera grupo de
chat automaticamente". Nesta reunião, o Product Owner reverteu essa
regra explicitamente: toda Equipe passa a ter um grupo de Chat
correspondente, sincronizado automaticamente.

## Decisão

- Criar uma Equipe cria, na mesma operação, uma conversa em grupo de
  Chat com o mesmo conjunto de membros (`Conversa.equipe` aponta para a
  `Equipe` de origem, `OneToOne`).
- Adicionar um usuário à equipe (`MembroEquipe` ativo) adiciona esse
  usuário ao grupo de chat correspondente, automaticamente; remover
  (exclusão do registro, ou `ativo=False`) remove do grupo,
  automaticamente.
- Sincronização é de mão única: sair do grupo de chat manualmente não
  remove da equipe — só entra/sai quem é membro efetivo da equipe.
- Fora isso, o grupo se comporta como qualquer conversa em grupo do
  Chat hoje (notificação por participante, indicador de não lida por
  participante, anexo, tempo real por WebSocket).

## Consequências

- `docs/PRODUCT.md`, seção Chat, deixa de registrar "Equipe não gera
  grupo de chat automaticamente" — passa a documentar a regra decidida
  aqui.
- Implementado via signals (`apps/chat/signals.py`) sobre
  `accounts.Equipe`/`accounts.MembroEquipe`, cobrindo qualquer caminho
  de escrita (views, admin, shell) — mesmo padrão já usado pela
  exclusão de anexo de mensagem.
- Migração de dados cria o grupo retroativo para equipes já existentes
  antes desta decisão, com os membros ativos atuais.

## Fora do escopo desta decisão

- Efeito de desativar uma equipe (`Equipe.ativo=False`) sobre o grupo
  de chat correspondente — mesma lacuna já registrada em
  `docs/PRODUCT.md` sobre desativação de equipe, continua sem decisão
  aprovada.
- Qualquer automação de chat fora do contexto de equipe (ex.: grupo
  automático por processo/cliente).
- Múltiplas equipes por usuário, hierarquia/aninhamento entre equipes —
  gaps pré-existentes, inalterados por esta decisão.

## Critérios de aceite funcionais

- Criar uma equipe com N membros gera um grupo de chat com esses
  mesmos N participantes.
- Adicionar/remover um membro da equipe reflete no grupo de chat sem
  ação manual no Chat.

## Fontes

- Conversa desta sessão (reunião, repassada pelo Product Owner); spec
  `specs/chat-grupo-automatico-por-equipe.md` (apagada após a promoção
  deste PDR, conforme
  [AGENTS.md](../../AGENTS.md#antes-de-apagar-uma-spec-concluída)).
