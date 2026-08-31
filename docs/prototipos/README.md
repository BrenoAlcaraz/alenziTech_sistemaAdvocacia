---
title: Protótipos funcionais de referência
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-31
---

# Protótipos funcionais de referência

## Autoridade

Os arquivos HTML deste diretório são protótipos funcionais navegáveis de
alta fidelidade. Eles representam de forma fidedigna as funcionalidades
desejadas do sistema e documentam experiência, navegação, estados, relações
entre telas e fluxos interativos. Não devem ser tratados como imagens
ilustrativas ou material histórico.

Ao trabalhar em uma funcionalidade demonstrada aqui, a pessoa ou o agente
deve abrir o HTML correspondente e percorrer sua navegação para compreender
o comportamento completo. A leitura isolada dos blocos de texto não
substitui essa interação.

Os comportamentos funcionais demonstrados permanecem vigentes salvo quando
um PDR posterior identifica expressamente um ponto diferente. Já nomes de
tabelas, queries e outros detalhes dos blocos “Como construir” são
orientações técnicas do protótipo e devem ser conciliados com o HEAD e com
as fontes canônicas de arquitetura e segurança antes de implementação
literal. A hierarquia completa está em
[docs/README.md](../README.md#hierarquia-das-fontes-de-verdade).

## Como utilizar

- abrir o protótipo do módulo em um navegador;
- percorrer abas, cards, formulários, filtros, estados e ligações entre
  telas;
- usar a navegação demonstrada como referência da experiência desejada;
- confrontar apenas os detalhes técnicos com o HEAD, arquitetura e
  segurança;
- preservar todo comportamento funcional que não tenha sido substituído
  expressamente por decisão posterior.

## Exceções posteriores já formalizadas

As exceções abaixo são pontuais. Elas não reduzem a fidelidade nem a
autoridade funcional do restante dos protótipos:

- `processo-prototipo.html` demonstra propagação de integrantes entre
  apensos; PDR-0012/PDR-0014 preservam a independência e não adotam essa
  cascata.
- `financeiro-prototipo.html` demonstra solicitações em fluxo curto
  `a_pagar`/`paga`; PDR-0015 define o fluxo vigente com análise e aprovação.
- `agenda-prototipo.html` demonstra o comportamento de notificações; a
  antecedência específica de 15 minutos foi acrescentada por PDR-0016.
- os detalhes de Partes de `processo-prototipo.html` foram consolidados no
  modelo aprovado em PDR-0013.

## Arquivos

- `agenda-prototipo.html`
- `configuracoes-prototipo.html`
- `dashboard-prototipo.html`
- `financeiro-prototipo.html`
- `modelos-prototipo.html`
- `processo-prototipo.html`
- `tarefas-prototipo.html`
