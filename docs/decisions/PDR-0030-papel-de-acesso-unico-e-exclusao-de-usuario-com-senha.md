---
id: PDR-0030
title: Papel de acesso como único mecanismo e exclusão de usuário com senha
status: accepted
owner: product-and-engineering
decision_date: 2026-09-20
last_reviewed: 2026-09-20
supersedes: []
complements:
  - PDR-0010
  - PDR-0019
source_files: []
---

# PDR-0030 — Papel de acesso como único mecanismo e exclusão de usuário com senha

## Contexto

A criação de usuário pedia dois campos que pareciam a mesma coisa:
"Tipo de conta" (Limitado/Financeiro, via `auth.Group`) e "Papel de
acesso" (`PapelAcesso`). O Tipo de conta era o mecanismo legado e ainda
valia como fallback de autorização quando o usuário não tinha nenhum
`UsuarioPapel`; a tela de Permissões tinha abas fixas para ele, além das
abas de papéis. Cinco papéis de fábrica (Sócio Gestor, Advogado
Associado, Estagiário/Paralegal, Gestor Financeiro, Secretaria/Recepção)
eram criados em todo escritório.

Excluir usuário (PDR-0010) era um clique com `confirm()`.

## Decisão

- **Papel de acesso é o único mecanismo de autorização**, além do
  Administrador do escritório (flag em `PerfilUsuario`, com bypass
  total). O Tipo de conta deixa de existir: formulário, aba de
  Permissões, colunas `tipo_conta` de `PermissaoPapel`/`HabilitacaoPapel`
  e o fallback por `auth.Group` saem por completo. Usuário sem papel e
  sem override não tem acesso a nada.
- De fábrica existem só o Administrador e o papel **"Limitado"**
  (`codigo_preset="limitado"`), com tudo desligado. Os cinco presets
  antigos deixam de ser criados. O Administrador cria e edita papéis,
  permissões de módulo/nível e habilitações.
- Novo usuário exige papel, com "Limitado" pré-selecionado.
- "Limitado" é editável (nome, descrição, permissões), mas não pode ser
  excluído nem desativado. Desativar qualquer papel com usuários ativos é
  recusado ("reatribua os N usuários antes").
- **Excluir usuário exige a senha de quem está logado** (não a do
  excluído), validada no backend; senha ausente ou errada não exclui e
  devolve mensagem genérica. Vale só para exclusão de usuário — outras
  exclusões (cliente, processo, modelo) não pedem senha.

## Consequências

- Sistema fora de produção: sem migração fina de dados. A migration
  `accounts.0033` descarta as linhas legadas por `tipo_conta` e os cinco
  presets antigos (usuários neles passam ao Limitado) e cria o Limitado;
  a `0034` remove `tipo_conta` e torna `papel` obrigatório.
- Quem hoje depende de Financeiro/Limitado por Group precisa de um papel
  equivalente criado pelo Administrador.
- Não há limite de tentativas de senha na exclusão: o login também não
  tem throttling hoje, então nada foi reaproveitado. Fica como lacuna
  registrada em `docs/STATUS.md`.
- Promover usuário a Administrador pela interface segue fora de escopo.
