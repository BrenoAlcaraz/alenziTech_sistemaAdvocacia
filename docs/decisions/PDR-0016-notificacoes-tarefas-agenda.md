---
id: PDR-0016
title: Notificações de Tarefas e Agenda
status: accepted
owner: product-and-engineering
decision_date: 2026-08-31
last_reviewed: 2026-08-31
supersedes: []
source_files: []
---

# PDR-0016 — Notificações de Tarefas e Agenda

## Contexto

`docs/product/modules/tarefas.md` e `docs/product/modules/agenda.md`
registravam notificações como explicitamente fora do escopo imediato, por
não estarem formalmente aprovadas em nenhum PDR aceito. A exploração
registrada nos protótipos funcionais
(`docs/prototipos/tarefas-prototipo.html`,
`docs/prototipos/agenda-prototipo.html`) descreve notificações para os
dois módulos. O protótipo de Tarefas sustenta a notificação de conclusão;
o protótipo de Agenda demonstra outra notificação, sem definir a
antecedência de 15 minutos. O Product Owner decidiu diretamente as regras
abaixo, que prevalecem sobre os detalhes dos protótipos e substituem a
deferral anterior.

## Decisão

### Tarefas

- Ao concluir uma tarefa, o criador da tarefa é notificado — exceto
  quando o criador é a própria IA (funcionalidade futura, condicionada a
  PDR-0008) ou quando o criador é o próprio responsável que concluiu.

### Agenda

- Todo compromisso e todo prazo geram uma notificação automática 15
  minutos antes do horário marcado, exibida dentro do sistema — no mesmo
  modelo do Google Agenda.
- Essa notificação depende de verificação periódica em segundo plano; não
  depende de nenhuma ação do usuário para ser disparada.

## Consequências

- `docs/product/modules/tarefas.md` deixa de listar "notificações de
  atribuição, reatribuição ou prazo" como fora de escopo imediato; passa a
  descrever a notificação de conclusão ao criador como regra funcional;
- `docs/product/modules/agenda.md` deixa de listar "lembretes automáticos"
  e "notificações push" como fora de escopo imediato; passa a descrever a
  notificação de 15 minutos antes como regra funcional;
- é necessário um mecanismo de verificação periódica em segundo plano
  (job assíncrono) para a notificação de Agenda — infraestrutura que ainda
  não existe no projeto e deve ser detalhada no Work Item de implementação;
- notificação de atribuição ou reatribuição de tarefa (distinta de
  conclusão) e notificação de prazo de tarefa continuam fora do escopo
  desta decisão.

## Fora do escopo desta decisão

- canal de notificação além de dentro do próprio sistema (e-mail, push
  fora do navegador, SMS);
- notificação de atribuição ou reatribuição de tarefa;
- notificação de prazo de tarefa (distinta de prazo de agenda);
- configuração pelo usuário de quais notificações recebe ou da antecedência
  de 15 minutos;
- integração com calendários externos.

## Critérios de aceite funcionais

- ao concluir uma tarefa cujo criador é diferente do responsável e não é
  a IA, o criador recebe notificação;
- ao concluir uma tarefa cujo criador é o próprio responsável, ou cujo
  criador é a IA, nenhuma notificação de conclusão é gerada;
- todo compromisso e todo prazo na Agenda gera notificação dentro do
  sistema 15 minutos antes do horário marcado, sem exigir ação do usuário.

## Fontes

- decisão direta do Product Owner registrada em 2026-08-31, durante a
  revisão estrutural de documentação a partir dos protótipos funcionais;
- [docs/prototipos/tarefas-prototipo.html](../prototipos/tarefas-prototipo.html);
- [docs/prototipos/agenda-prototipo.html](../prototipos/agenda-prototipo.html)
  (protótipo funcional navegável de alta fidelidade; a antecedência de 15
  minutos foi acrescentada por esta decisão).
