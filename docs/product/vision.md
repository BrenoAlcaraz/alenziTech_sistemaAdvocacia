---
title: Visão do produto
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Visão do produto

## Produto

Breno - LawSystem é um sistema jurídico SaaS white label, multi-tenant,
destinado a escritórios de advocacia e suas equipes. Cada escritório
opera como um tenant isolado por schema PostgreSQL, com a plataforma
SaaS (tenants, planos, assinaturas) mantida em um schema público
compartilhado.

O produto é construído como um monólito modular Django, com domínios de
negócio organizados internamente em módulos (apps Django). Não é um
sistema de microserviços, e essa distinção não deve ser confundida em
nenhuma decisão de produto.

## Problema

Escritórios de advocacia precisam administrar, em um ambiente integrado,
um conjunto amplo de rotinas jurídicas e administrativas:

- clientes;
- processos e casos;
- participantes;
- andamentos e documentos;
- tarefas;
- agenda e prazos;
- finanças;
- equipes;
- modelos de peças;
- comunicação interna;
- indicadores de gestão.

Hoje essas rotinas costumam estar fragmentadas entre planilhas, sistemas
isolados e controles manuais, o que gera retrabalho, dados duplicados e
falta de rastreabilidade. Esta visão descreve o problema que o produto
se propõe a resolver — não afirma que todos esses recursos já estão
implementados de forma completa. O estado real de implementação é
registrado em documentos de current-state e nas especificações de cada
módulo, não nesta visão.

## Proposta de valor

O Breno - LawSystem se propõe a:

- centralizar a operação do escritório em um único ambiente;
- reduzir duplicidade e inconsistência de dados entre módulos;
- relacionar informações jurídicas e administrativas de forma coerente;
- controlar acesso conforme papel, habilitação e escopo de cada usuário;
- preservar isolamento entre escritórios (tenants);
- permitir personalização white label para cada escritório;
- criar uma base confiável de dados e permissões sobre a qual
  automação e inteligência artificial possam ser construídas no futuro.

## Usuários do produto

Em nível conceitual, o produto atende:

- Administrador do escritório;
- profissionais jurídicos;
- gerentes de equipe;
- usuários financeiros;
- apoio administrativo;
- Platform Admin, restrito à administração da plataforma SaaS e fora do
  escopo de um tenant específico.

Esta visão identifica categorias conceituais de usuários, mas não define
a matriz técnica de papéis e permissões, que pertence à documentação de
autorização.

## Princípios do produto

- núcleo funcional confiável antes de automação avançada;
- regras de negócio antes de refinamentos visuais;
- dados reais em vez de mocks operacionais;
- autorização aplicada no backend, não apenas na interface;
- isolamento entre tenants;
- integridade dos vínculos entre entidades (clientes, processos,
  participantes, finanças);
- rastreabilidade das decisões e alterações relevantes;
- evolução incremental, sem reescrita total do sistema;
- inteligência artificial aplicada somente sobre dados e permissões já
  consolidados.

## Domínios principais

- identidade, usuários, papéis e equipes;
- clientes;
- processos e participantes;
- tarefas;
- agenda e prazos;
- financeiro;
- painel e gestão;
- chat interno;
- modelos de peças;
- configurações e white label;
- cobrança SaaS;
- assistência e IA futuras.

## Visão de IA

O produto distingue explicitamente dois produtos de inteligência
artificial, que não devem ser confundidos entre si:

### Assistente do sistema

Apoio ao uso do próprio produto: documentação, navegação e dúvidas
operacionais sobre como utilizar o sistema.

### IA jurídica

Análise de documentos e processos, pesquisa contextual, resumo,
discussão de estratégia, e geração e edição de peças jurídicas.

Assistente do sistema e IA jurídica são produtos distintos. A IA
jurídica depende de pré-requisitos que devem estar consolidados antes
da implementação:

- dados jurídicos estruturados;
- permissões efetivamente aplicadas;
- acesso seguro aos documentos;
- histórico e rastreabilidade;
- um núcleo funcional estável.

## Critério de sucesso

O produto é bem-sucedido quando um escritório de advocacia consegue
operar suas rotinas jurídicas e administrativas com dados consistentes,
acesso seguro e integração real entre os módulos que compõem o sistema.
Este documento não define métricas quantitativas de sucesso; elas não
fazem parte desta visão.
