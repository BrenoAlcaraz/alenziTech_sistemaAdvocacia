---
title: Documentação do Breno - LawSystem
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-31
---

# Documentação do Breno - LawSystem

## Objetivo

Este diretório contém as fontes versionadas utilizadas para produto,
arquitetura, segurança, entrega e desenvolvimento do Breno - LawSystem.
É o ponto de partida para qualquer pessoa ou agente que precise entender
o que o sistema é, como é construído e por que decisões foram tomadas.

## Arquitetura atual resumida

- Monólito modular Django.
- PostgreSQL como banco de dados.
- Multi-tenancy por schema, um schema PostgreSQL por escritório, via
  django-tenants.
- Módulos internos separados por apps Django (`accounts`, `clientes`,
  `processos`, etc.).
- Não há, na arquitetura atual, microserviços independentes.

## Organização documental

- `governance/` — políticas sobre como a documentação é organizada,
  mantida e nomeada, e o índice de decisões do projeto.
- `product/` — visão, escopo, glossário e especificações canônicas do
  produto.
- `architecture/` — decisões e especificações canônicas de arquitetura
  técnica.
- `security/` — regras, políticas e decisões de segurança do sistema.
- `delivery/` — estado atual, roadmap, tarefas ativas e relatórios de
  implementação.
- `development/` — procedimentos operacionais de desenvolvimento, testes,
  migrations e uso de agentes de IA.
- `prototipos/` — protótipos funcionais navegáveis de alta fidelidade;
  registram a experiência, a navegação e os fluxos desejados do produto.
- `history/` — material documental preservado para rastreabilidade, sem
  autoridade sobre o estado atual do sistema.

As áreas acima compõem a organização documental vigente. Novos
documentos podem ser adicionados dentro dessas áreas conforme o projeto
evolui.

## Hierarquia das fontes de verdade

Em ordem decrescente de autoridade:

1. PDR ou ADR aceito e vigente.
2. Especificação canônica do produto.
3. Arquitetura e segurança canônicas.
4. Protótipo funcional vigente, para experiência, navegação e fluxos que
   demonstra, salvo decisão posterior expressa.
5. Tarefa ativa aprovada.
6. Código e testes como evidência do comportamento implementado.
7. Current-state verificado em um commit.
8. Roadmap.
9. Material histórico, apenas como contexto.

Os protótipos não são meras ilustrações: devem ser abertos e navegados
quando o trabalho afetar as funcionalidades que demonstram. Seus fluxos,
estados, relações entre telas e comportamentos interativos integram a
intenção vigente do produto. Sugestões técnicas internas, como nomes de
tabelas, queries ou mecanismos de backend, continuam subordinadas às
fontes canônicas de arquitetura e segurança. Uma exceção funcional só é
descartada quando houver decisão posterior expressa que identifique o
ponto substituído.

O código demonstra o que existe. A especificação demonstra o que
deveria existir. Quando os dois divergem, a divergência não pode ser
resolvida silenciosamente por uma IA — ela deve ser registrada e
levada a uma decisão humana, conforme a [Regra de conflito](#regra-de-conflito).

## Leitura por impacto

O ponto de entrada de uma execução é [AGENTS.md](../AGENTS.md). Para trabalhar, leia o
Work Item/Context Pack ativo e os arquivos diretamente afetados. O Context
Pack aponta somente as fontes canônicas aplicáveis ao delta.

Documentação de módulo, PDRs/ADRs, arquitetura, segurança, estratégia
detalhada de testes, migrations, `current-state`, roadmap e histórico são
contexto sob demanda, não uma lista obrigatória para toda tarefa. O risco
define a profundidade: alterações de autorização, escopo/IDOR, tenant,
integridade sensível ou migration de dados exigem as fontes especializadas;
alterações localizadas não exigem reconstruir todo o domínio.

Quando a tarefa afetar uma funcionalidade demonstrada em protótipo, o
protótipo correspondente integra o Context Pack e deve ser navegado para
compreensão do fluxo, não apenas lido como HTML estático.

Para consultar material sem autoridade vigente, use
[docs/history/](history/README.md).

## Regra de conflito

Diante de uma divergência relevante entre documentação e código, ou entre
documentos canônicos, o agente deve:

1. Interromper a decisão afetada.
2. Registrar a divergência encontrada.
3. Apontar os documentos e o código envolvidos.
4. Solicitar decisão humana.
5. Atualizar a fonte canônica antes de implementar.

## Estado da reorganização

A estrutura documental base está estabelecida: todas as áreas listadas
em "Organização documental" existem e possuem pelo menos seus
documentos de índice. Este índice não mantém estado de produto ou de
implementação — para isso, consultar
[docs/delivery/current-state.md](delivery/current-state.md) e
[docs/delivery/roadmap.md](delivery/roadmap.md).
