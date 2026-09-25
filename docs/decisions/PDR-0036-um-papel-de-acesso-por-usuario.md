---
id: PDR-0036
title: Um papel de acesso por usuário
status: accepted
owner: product-and-engineering
decision_date: 2026-09-24
last_reviewed: 2026-09-24
supersedes: []
complements:
  - PDR-0030
source_files: []
---

# PDR-0036 — Um papel de acesso por usuário

## Contexto

Um usuário podia ter vários papéis ativos, e o acesso era a soma deles
(maior nível por módulo, união das habilitações), mais os ajustes
individuais. Não dava para responder "o que essa pessoa pode fazer e
por quê": tirar um papel podia não tirar o acesso, somar um papel
ampliava o acesso sem aviso, e a criação de usuário (um papel) contradizia
a tela de atribuição (somava papéis).

## Decisão

- **Cada usuário tem um único papel de acesso.** As exceções de uma
  pessoa são ajustes individuais (`PermissaoUsuario`/`HabilitacaoUsuario`),
  que continuam valendo acima do papel. Uma combinação repetida por várias
  pessoas vira um papel próprio do escritório.
- Atribuir um papel substitui o anterior. Tirar alguém de um papel o
  devolve ao "Limitado".
- **Gerente de equipe não é papel de acesso**: é relação organizacional,
  com efeitos restritos à relação com os membros da própria equipe. Não
  libera módulos.
- O Administrador do escritório continua fora dos papéis (acesso total).

## Consequências

- O banco garante no máximo um papel ativo por usuário
  (`uniq_usuariopapel_um_ativo_por_usuario`).
- Conversão (`accounts.0007`): quem tinha mais de um papel ativo foi
  para o "Limitado", com os ajustes individuais preservados; quem perdeu
  acesso a Processos teve os processos transferidos ao Administrador, que
  reatribui papel e processos manualmente.
- Mostrar na tela o que vem do papel e o que é ajuste individual ficou
  como pendência (`docs/STATUS.md`).
