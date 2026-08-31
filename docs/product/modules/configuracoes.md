---
title: Configurações
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-13
related_pdrs:
  - PDR-0009
---

# Configurações

## Objetivo

Centralizar configurações pessoais, administrativas e de identidade do
escritório, mantendo separadas informações de perfil, organização,
autorização, white label e cobrança da plataforma.

## Escopo funcional

- Edição de dados pessoais.
- Nome de exibição.
- Foto de perfil.
- Alteração de senha pelo fluxo seguro do Django.
- Gestão administrativa de usuários.
- Papéis de acesso.
- Habilitações.
- Equipes.
- Dados e identidade visual do escritório.
- Configurações white label.
- Consulta ou gestão do plano SaaS, conforme autorização.

Esta especificação não afirma quais campos técnicos já existem no
sistema.

## Atores e expectativas de acesso

- Todo usuário autenticado pode editar o próprio perfil pessoal.
- A gestão administrativa de usuários, papéis, habilitações e dados do
  escritório é restrita a papéis de acesso autorizados para
  administração do escritório.
- Consultar ou alterar o plano SaaS é restrito conforme autorização,
  distinguindo a administração do tenant e o Platform Admin.
- O alcance exato de quem pode alterar cada grupo de configurações é
  definido em [docs/security/authorization-matrix.md](../../security/authorization-matrix.md).
  O estado de aplicação dessas regras no backend deve ser verificado no
  código e em [docs/delivery/current-state/configuracoes.md](../../delivery/current-state/configuracoes.md).
- Autorização deve ser aplicada no backend; ocultar ou exibir um botão
  ou seção não substitui essa verificação.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Identidade e
organização": usuário, PerfilUsuario, Administrador do escritório,
Platform Admin, papel de acesso, habilitação, cargo profissional,
equipe, membro de equipe, gerente de equipe e escopo de dados. Este
documento não redefine esses termos.

## Regras funcionais

- Usuário e PerfilUsuario são conceitos distintos.
- Papel de acesso não é cargo profissional.
- Equipe não é papel de acesso.
- Gerente de equipe não recebe acesso global automaticamente; o
  alcance de um gerente depende de papel, habilitação e escopo de
  dados aplicados no backend, conforme [equipes.md](equipes.md).
- Alterações de papel de acesso ou de habilitação devem produzir
  efeito real no backend.
- Salvar uma configuração visual não altera autorização.
- A foto de perfil pode ser reutilizada em cabeçalho, chat e demais
  referências ao usuário, conforme [chat.md](chat.md).
- A alteração de senha exige o fluxo seguro do Django, com validação
  adequada.
- A administração de usuários e de acesso respeita o tenant; um
  usuário de um tenant não pode ser administrado a partir de outro
  tenant.
- As configurações white label pertencem ao escritório (tenant).
- A administração da plataforma SaaS pertence ao Platform Admin, e não
  ao Administrador do escritório.
- Plano e Assinatura são conceitos pertencentes ao billing SaaS e
  permanecem em `saas_billing`. Configurações pode apresentar ou
  administrar informações do plano conforme autorização e
  implementação futura, sem que essa consulta crie lançamento no
  Financeiro do tenant. Uma eventual integração financeira futura
  entre `saas_billing` e o financeiro do tenant exige um novo PDR,
  conforme
  [PDR-0003](../decisions/PDR-0003-areas-funcionais-financeiro.md),
  tratada também em [financeiro.md](financeiro.md).

Esta especificação não define:

- `auth.Group` como fonte canônica de papel de acesso;
- a lista definitiva de papéis de acesso;
- a precedência técnica entre regras de autorização;
- exclusão de usuários;
- limites exatos dos planos SaaS;
- campos exatos de white label.

## Fluxos principais

1. Editar perfil pessoal.
2. Alterar nome de exibição.
3. Adicionar ou substituir foto de perfil.
4. Alterar senha.
5. Criar ou editar usuário, conforme autorização.
6. Atribuir papel de acesso.
7. Atribuir habilitação.
8. Relacionar usuário a uma equipe.
9. Alterar identidade do escritório.
10. Consultar ou alterar o plano SaaS, quando autorizado.

Esta especificação não determina exclusão física de usuário.

## Integrações e dependências

- Depende do módulo Equipes para relacionar usuários a equipes,
  conforme [equipes.md](equipes.md).
- Fornece a foto de perfil reutilizada pelo módulo Chat, conforme
  [chat.md](chat.md), sem que essa reutilização crie dependência de
  autorização entre os módulos.
- Depende do módulo de billing SaaS (`saas_billing`) para consulta e
  gestão de plano e assinatura, mantido como conceito distinto do
  financeiro do tenant.

## Fora do escopo imediato

- Exclusão física de usuário.
- Enforcement automático dos limites comerciais dos planos.
- Fluxo completo de upgrade e downgrade de plano.
- Configuração avançada de white label além do necessário para
  identidade visual básica do escritório.

## Pontos em aberto

- Exclusão, desativação ou bloqueio de usuário.
- Campos e limites da foto de perfil.
- Campos configuráveis de white label.
- Quem pode alterar cada grupo de configurações.
- Enforcement dos limites comerciais dos planos.
- Fluxo de upgrade e downgrade de plano.
- Efeitos de uma redução de plano sobre dados e usuários existentes.
- Tratamento de usuários acima do limite contratado.
- Interface exata de apresentação ou administração do plano SaaS
  dentro de Configurações — não confirmada nesta especificação nem no
  código, apenas prevista como possibilidade funcional futura.

## Critérios de aceite funcionais

- Todo usuário autenticado consegue editar seus próprios dados
  pessoais, nome de exibição e foto de perfil.
- A alteração de senha segue o fluxo seguro do Django.
- Usuários de um tenant não são administráveis a partir de outro
  tenant.
- Um usuário indicado como gerente de equipe não obtém acesso global
  apenas por essa indicação.
- Salvar uma configuração visual não altera a autorização de nenhum
  usuário.
- Consulta e gestão do plano SaaS respeitam a distinção entre
  Administrador do escritório e Platform Admin.
- Alterações de papel de acesso e habilitação produzem efeito real no
  backend.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)
- [equipes.md](equipes.md)
