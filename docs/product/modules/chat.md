---
title: Chat
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-13
related_pdrs: []
---

# Chat

## Objetivo

Oferecer comunicação interna entre usuários pertencentes ao mesmo
escritório.

## Escopo funcional

Como escopo pretendido, o módulo Chat compreende:

- conversas individuais;
- conversas em grupo;
- envio de mensagens;
- anexos de imagens e documentos;
- identificação dos participantes;
- apresentação de foto de perfil, quando disponível.

Esta especificação não afirma que comunicação em tempo real já existe.

## Atores e expectativas de acesso

- Participantes de uma conversa pertencem ao mesmo tenant.
- Um usuário acessa somente as conversas das quais participa, ou que
  seu escopo administrativo autorize.
- O alcance exato de eventual acesso administrativo a conversas é
  definido em [docs/security/authorization-matrix.md](../../security/authorization-matrix.md).
  O estado de aplicação dessas regras no backend deve ser verificado no
  código e em [docs/delivery/current-state.md](../../delivery/current-state.md).
- Acesso a mensagens e anexos deve ser verificado no backend; conhecer
  o identificador de uma conversa ou de um arquivo não concede acesso
  a ele.

## Conceitos e entidades

Este módulo não introduz uma seção própria no
[glossário funcional](../glossary.md). Os conceitos de usuário,
tenant e foto de perfil utilizados aqui são os mesmos definidos nesse
glossário e em [configuracoes.md](configuracoes.md).

## Regras funcionais

- Nenhuma conversa pode atravessar tenants.
- Conversas individuais e conversas em grupo são conceitos distintos.
- Anexos preservam vínculo com a conversa a que pertencem.
- A foto de perfil é apenas apresentação; ela não controla identidade
  nem autorização.
- Uma equipe não gera automaticamente um grupo de chat nesta decisão.

## Fluxos principais

1. Iniciar conversa individual.
2. Criar conversa em grupo.
3. Adicionar participantes a um grupo, quando autorizado.
4. Enviar mensagem.
5. Anexar arquivo.
6. Consultar histórico autorizado.

Esta especificação não transforma uma experiência equivalente à de
aplicativos de mensagens populares em requisito técnico definido.

## Integrações e dependências

- Depende de [configuracoes.md](configuracoes.md) para a foto de
  perfil apresentada nas conversas, sem que essa dependência crie
  autorização adicional.
- Pode se relacionar futuramente ao módulo Equipes como referência
  organizacional, sem que uma equipe crie automaticamente um grupo de
  chat.

## Fora do escopo imediato

- Chamadas de áudio ou vídeo.
- Comunicação com pessoas externas ao tenant.
- Integração com aplicativos externos de mensagens.
- Bots ou inteligência artificial dentro do chat interno.
- Notificações push, enquanto não formalizadas.

## Pontos em aberto

- Criação automática de grupo a partir de uma equipe.
- Comunicação em tempo real.
- Notificações de mensagens.
- Confirmação de leitura.
- Edição de mensagem.
- Exclusão de mensagem.
- Retenção e arquivamento de conversas.
- Limites e formatos de anexos.
- Administração ou moderação de grupos.
- Histórico de uma conversa após a saída de um participante.

## Critérios de aceite funcionais

- Nenhuma conversa ou mensagem é acessível a um usuário fora do
  tenant a que pertence.
- Um usuário só acessa conversas das quais participa ou que seu
  escopo administrativo autorize.
- O acesso a mensagens e anexos é verificado no backend, não apenas
  pelo conhecimento do identificador do recurso.
- Uma conversa em grupo permanece distinta de uma conversa individual
  em toda a interface e na modelagem funcional.
- A criação de uma equipe não gera automaticamente um grupo de chat
  correspondente.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)
- [configuracoes.md](configuracoes.md)
