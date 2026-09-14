# Spec — Chat: grupo automático por equipe

Status: **decisão reverte regra hoje documentada em PRODUCT.md**
("Equipe não gera grupo de chat automaticamente") — confirmada
explicitamente pelo Product Owner nesta reunião. Ao implementar, abrir
PDR novo substituindo essa frase antes de promover conhecimento durável.

## Objetivo

Ao criar uma equipe, criar automaticamente um grupo de chat
correspondente; manter a lista de participantes do grupo sincronizada
com os membros da equipe.

## Comportamento esperado

- Criar uma Equipe cria, na mesma operação, uma conversa em grupo de
  Chat com o mesmo conjunto de membros.
- Adicionar um usuário à equipe adiciona esse usuário ao grupo de chat
  correspondente, automaticamente.
- Remover um usuário da equipe remove esse usuário do grupo de chat
  correspondente, automaticamente.
- Fora isso, o grupo se comporta como qualquer conversa em grupo do Chat
  hoje (notificação por participante, indicador de não lida por
  participante, anexo, tempo real por WebSocket).

## Regras de negócio relevantes

- Só entra/sai automaticamente quem é membro efetivo da equipe — não há
  sincronização no sentido contrário (sair do grupo de chat manualmente
  não remove da equipe).
- O efeito de desativar uma equipe sobre o grupo de chat correspondente é
  ponto em aberto (mesma lacuna já registrada em PRODUCT.md sobre
  desativação de equipe) — a definir junto da implementação.

## Fora de escopo

- Equipe deixar de existir como conceito organizacional puro — continua
  sem conceder acesso/autorização por si só (regra inalterada).
- Qualquer automação de chat fora do contexto de equipe (ex.: grupo
  automático por processo/cliente).

## Critérios de aceite

- Criar uma equipe com N membros gera um grupo de chat com esses mesmos
  N participantes.
- Adicionar/remover um membro da equipe reflete no grupo de chat sem
  ação manual no Chat.
