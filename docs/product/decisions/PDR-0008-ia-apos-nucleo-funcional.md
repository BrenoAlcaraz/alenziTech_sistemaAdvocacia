---
id: PDR-0008
title: IA após o núcleo funcional
status: accepted
owner: product-and-engineering
decision_date: 2026-08-05
last_reviewed: 2026-08-06
supersedes: []
source_files:
  - docs/history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt
  - docs/history/source-material/product-vision-original.docx
---

# PDR-0008 — IA após o núcleo funcional

## Contexto

O produto planeja funcionalidades de inteligência artificial, mas o
núcleo funcional do sistema — permissões, integridade dos vínculos entre
entidades, e dados jurídicos estruturados — ainda está em consolidação.
Era necessário definir explicitamente a relação de dependência entre a
IA e esse núcleo.

## Problema

Construir funcionalidades de IA sobre dados sem autorização aplicada,
sem escopo de dados consolidado e sem acesso seguro a documentos expõe o
sistema a risco de a IA operar sobre dados incorretos, incompletos ou
indevidamente acessíveis, além de gerar retrabalho quando o núcleo
funcional mudar.

## Decisão

A inteligência artificial não é pré-requisito das funções básicas do
sistema. O núcleo funcional, as permissões, a integridade dos vínculos e
os documentos vêm primeiro.

Assistente do sistema e IA jurídica são produtos distintos:

**Assistente do sistema**

- ajuda de uso do produto;
- documentação;
- navegação;
- dúvidas operacionais.

**IA jurídica**

- contexto do processo;
- busca em documentos;
- resumos;
- discussão de estratégia;
- geração e edição de peças;
- histórico de versões;
- integração futura com Modelos de peças.

## Regras obrigatórias

A IA jurídica depende dos seguintes pré-requisitos, que devem estar
consolidados antes de sua implementação:

- autorização aplicada;
- escopo de dados definido e aplicado;
- acesso seguro a documentos;
- dados processuais estruturados;
- histórico e rastreabilidade;
- módulos centrais estáveis.

A interface planejada para a IA jurídica é um painel do tipo
Assistente/Laboratório apresentado dentro do contexto visual do
processo, preservando a separação técnica interna entre esse componente
e os demais módulos, quando adequado.

Este PDR não decide tecnologia, provedor, modelo de linguagem ou
arquitetura técnica da IA — essas decisões pertencem a um ADR futuro.

## Consequências

- Nenhuma funcionalidade básica do sistema pode ser condicionada à
  existência de IA para funcionar.
- A ordem de dependência estabelecida aqui reforça a sequência de
  rodadas registrada em [PDR-0009](PDR-0009-sequencia-fase-2.md), na
  qual o Assistente e o Laboratório aparecem apenas na última rodada.
- Assistente do sistema e IA jurídica precisam ser tratados como
  iniciativas de produto separadas em qualquer planejamento futuro, com
  escopos e critérios de aceite próprios.
- A implementação da IA jurídica fica bloqueada até que autorização,
  escopo de dados, acesso seguro a documentos, estrutura de dados
  processuais e rastreabilidade estejam consolidados.

## Alternativas ou regras substituídas

O material de visão inicial (`product-vision-original.docx`) descrevia
um "laboratório jurídico" com capacidades avançadas de IA (geração
automática de peças a partir da análise de processos inteiros,
sugestões automáticas de próximos passos, tarefas repetidas em massa)
como parte central da proposta desde o início, sem condicionar essas
capacidades à consolidação prévia de um núcleo funcional. A decisão
consolidada posterior estabelece explicitamente essa dependência, e
prevalece sobre a visão inicial nesse ponto: a IA jurídica avançada
descrita na visão original passa a depender da consolidação do núcleo
funcional, permissões e estrutura de dados antes de ser implementada.

## Fora do escopo desta decisão

- Escolha de tecnologia, provedor, modelo de linguagem ou arquitetura
  técnica da IA: pertence a um ADR futuro.
- Definição detalhada de funcionalidades específicas do Assistente do
  sistema ou da IA jurídica além do que está listado aqui: pertence a
  especificações de módulo futuras.
- A ordem de rodadas de entrega, tratada em
  [PDR-0009](PDR-0009-sequencia-fase-2.md).
- Regras funcionais de honorários que mencionam identificação futura por
  IA: tratadas em [PDR-0007](PDR-0007-honorarios-manuais-antes-ia.md).

## Critérios de aceite funcionais

- Nenhuma funcionalidade essencial do núcleo (clientes, processos,
  participantes, tarefas, agenda, financeiro) exige IA para operar.
- O produto apresenta Assistente do sistema e IA jurídica como
  funcionalidades distintas, não intercambiáveis.
- A implementação de IA jurídica só é iniciada após autorização,
  escopo de dados, acesso seguro a documentos, dados processuais
  estruturados, histórico e rastreabilidade, e módulos centrais
  estarem consolidados.
- Quando implementada, a interface da IA jurídica aparece no contexto
  visual do processo, como painel do tipo Assistente/Laboratório.

## Fontes

- [2026-08-05-decisoes-funcionais-consolidadas-original.txt](../../history/source-material/2026-08-05-decisoes-funcionais-consolidadas-original.txt)
- [product-vision-original.docx](../../history/source-material/product-vision-original.docx)
