---
id: PDR-0039
title: Responsabilidade atribuída a vários usuários no Processo
status: accepted
owner: product-and-engineering
decision_date: 2026-09-26
last_reviewed: 2026-09-26
supersedes: []
complements:
  - PDR-0010
  - PDR-0014
source_files: []
---

# PDR-0039 — Responsabilidade atribuída a vários usuários no Processo

## Contexto

Cada processo tinha um único responsável principal obrigatório
(PDR-0010/PDR-0014), escolhido no formulário do processo. Na revisão do
sócio de 2026-09-26, "responsabilidade" passou a significar a
atribuição feita por quem gerencia: um gerente de equipe ou o
administrador define quem cuida do processo, e pode ser mais de uma
pessoa.

## Decisão

- O antigo responsável principal vira **`criado_por`** (quem cadastrou).
  Não aparece em nenhum formulário e não precisa ser um dos
  responsáveis.
- **Responsáveis** são N usuários atribuídos, na ordem da atribuição.
- Quem atribui: o Administrador e quem tem `processos_atribuir_responsavel`
  atribuem para qualquer usuário com acesso a Processos; o **gerente de
  equipe** atribui só para os membros ativos não-gerentes das equipes
  que gerencia, e só retira quem poderia atribuir. O campo aparece no
  card "Atribuir responsabilidade" do processo e no formulário de
  novo/editar (só para quem pode atribuir).
- Escopo "somente seus" e edição (fora o Administrador): processos que o
  usuário **criou ou pelos quais é responsável**.
- Avisos do acompanhamento (DJEN/DataJud) e de honorário vão para todos
  os responsáveis ativos; sem nenhum, para quem criou.
- Prazo gerado pelo andamento continua **um por andamento** (PDR-0034): o
  1º responsável é o responsável do item e os demais entram como
  participantes; sem responsável, vai para quem criou. Mudança nos
  responsáveis reflete nos prazos em aberto.
- Na migração, o responsável de cada processo virou `criado_por` e
  primeiro responsável — nada mudou para quem já usava.

## Consequências

- A fila "Responsável inativo" virou "Sem responsável ativo".
- Perda de acesso ao módulo tira o usuário dos responsáveis; o processo
  que fica sem ninguém passa ao Administrador.
- O que o PDR-0010/0014 dizia sobre o "responsável principal único"
  deixa de valer; integrantes habilitados seguem inalterados.
