---
title: Equipes
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-13
related_pdrs:
  - PDR-0002
  - PDR-0009
---

# Equipes

## Objetivo

Representar a organização interna do escritório para distribuição de
responsabilidade, gestão e escopo de dados.

## Escopo funcional

- criação e edição de equipes;
- inclusão e remoção de membros;
- indicação de gerente ou responsável organizacional por equipe;
- uso da equipe como referência de escopo em módulos operacionais,
  quando autorizado.

## Atores e expectativas de acesso

A gestão de equipes deve ser restrita a papéis de acesso autorizados
para administração do escritório, aplicada no backend. O alcance de um
gerente de equipe sobre a gestão da própria equipe, ou sobre dados dos
membros que gerencia, é uma extensão possível de papel, habilitação e
escopo — não uma concessão automática decorrente apenas de ser
gerente.

Esta seção descreve necessidade funcional, não uma matriz técnica
definitiva de permissões; essa matriz é
[docs/security/authorization-matrix.md](../../security/authorization-matrix.md).
O estado de aplicação dessas regras no backend deve ser verificado no
código e em [docs/delivery/current-state.md](../../delivery/current-state.md).

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Identidade e
organização": equipe, membro de equipe, gerente de equipe, papel de
acesso, cargo profissional e escopo de dados. Este documento não
redefine esses termos.

## Regras funcionais

- O termo canônico é Equipe. "Departamento" é um termo histórico e
  depreciado, mantido apenas em documentação e código legado, conforme
  [../../governance/terminology-policy.md](../../governance/terminology-policy.md).
- Equipe é uma relação organizacional.
- Papel de acesso é uma relação de autorização.
- Cargo profissional é descritivo.
- Equipe, papel de acesso e cargo profissional não são conceitos
  equivalentes entre si.
- Gerente de equipe representa uma relação organizacional de
  responsabilidade sobre a equipe.
- Ser gerente de uma equipe não concede automaticamente acesso global
  ao sistema; o acesso depende de papel de acesso, habilitação e
  escopo de dados aplicados no backend.
- Membros de uma equipe pertencem ao mesmo tenant.
- Vínculos organizacionais de equipe não podem atravessar tenants.
- Uma equipe pode ser utilizada na distribuição de processos, tarefas
  e visões gerenciais quando o usuário estiver autorizado a esse
  escopo.
- A aplicação do escopo baseado em equipe deve ocorrer no backend.

## Fluxos principais

1. Criar equipe.
2. Editar equipe.
3. Adicionar ou remover membro de uma equipe.
4. Indicar gerente ou responsável organizacional de uma equipe.
5. Utilizar a equipe como referência de escopo em um módulo
   operacional autorizado.

## Integrações e dependências

- Referência de escopo para o módulo Tarefas, na visibilidade
  associada a "habilitação de gestão" (ver [tarefas.md](tarefas.md)).
- Referência de escopo potencial para o módulo Processos e para visões
  gerenciais futuras.

## Fora do escopo imediato

- Hierarquia avançada ou herança automática de permissões entre
  equipes.
- Métricas de desempenho por equipe.
- Gestão de equipes por perfis além dos autorizados para administração
  do escritório.

## Pontos em aberto

Os seguintes pontos não possuem decisão aprovada nas fontes
consolidadas e não são resolvidos por esta especificação:

- se um usuário pode participar de uma única equipe ou de várias
  simultaneamente;
- se uma equipe exige exatamente um gerente;
- se existe hierarquia entre equipes;
- se equipes podem ser aninhadas;
- se há herança automática de permissões entre equipes relacionadas;
- se a exclusão de uma equipe é em cascata ou de outra forma;
- existência de desativação ou encerramento de equipe;
- efeitos da desativação sobre membros, processos, tarefas e
  histórico;
- estratégia de preservação dos vínculos caso a funcionalidade de
  desativação ou encerramento seja aprovada.

## Critérios de aceite funcionais

- Equipe, papel de acesso e cargo profissional são tratados como
  conceitos distintos em toda a especificação e na interface.
- Um usuário indicado como gerente de uma equipe não obtém acesso
  global ao sistema apenas por essa indicação.
- Todos os membros de uma equipe pertencem ao mesmo tenant.
- A aplicação de escopo baseado em equipe ocorre no backend, não
  apenas ocultando elementos de interface.
- Uma equipe pode ser referenciada como escopo por módulos
  operacionais autorizados, como Tarefas.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0002 — Delegação direta de tarefas](../decisions/PDR-0002-delegacao-direta-de-tarefas.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)

A transição terminológica de "departamento" para "Equipe" está
registrada, apenas como contexto histórico não canônico, em
`docs/history/legacy-plans/plano-fase-2-departamentos.md`.
