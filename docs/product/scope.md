---
title: Escopo do produto
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-13
---

# Escopo do produto

## Objetivo

Este documento separa o que pertence ao escopo funcional do produto, o
que é foco da etapa atual, o que está planejado para mais adiante e o
que está fora de escopo. Ele não afirma o estado real de implementação
de nenhum item — o estado real é responsabilidade de
[docs/delivery/current-state.md](../delivery/current-state.md).

## Escopo funcional do produto

Os seguintes domínios pertencem ao escopo do produto:

- gestão de escritórios e tenants;
- usuários, papéis, habilitações e equipes;
- clientes e documentos de clientes;
- processos e casos;
- participantes, representantes e autoridades;
- andamentos, fases, status, apensos e documentos processuais;
- tarefas e delegação;
- agenda, prazos e compromissos;
- financeiro geral;
- custas judiciais;
- solicitações de pagamento e reembolso;
- honorários;
- painel, indicadores e gestão;
- chat interno;
- modelos de peças;
- configurações e white label;
- planos e assinaturas da plataforma;
- assistente e IA jurídica futuras.

## Foco da etapa atual

A Fase 2 prioriza, nesta ordem de dependência:

1. autorização e integridade;
2. modelagem de clientes, processos e participantes;
3. andamentos, documentos e prazos;
4. tarefas e agenda;
5. núcleo financeiro;
6. custas e solicitações;
7. honorários e relatórios;
8. painel do gestor e atividade;
9. assistente e laboratório após o núcleo.

Esta ordem de prioridade não é evidência de que qualquer uma dessas
etapas esteja concluída. O estado de conclusão de cada etapa é
responsabilidade do current-state e das especificações de módulo, não
deste documento.

## Dentro do escopo imediato

- aplicar permissões e habilitações no backend;
- implementar escopo de dados;
- garantir vínculos válidos entre cliente e processo;
- consolidar modelagem jurídica;
- sincronizar regras entre módulos;
- substituir shells e mocks operacionais por fluxos reais;
- criar testes de autorização, integridade e isolamento;
- manter migrations seguras para public e tenants.

## Planejado, mas não imediato

- notificações;
- chat individual e em grupo;
- tempo real;
- limites comerciais de planos com enforcement;
- analytics avançado;
- OCR e processamento documental;
- integrações com sistemas externos e tribunais;
- automações jurídicas;
- assistente do sistema;
- IA jurídica contextual.

## Fora do escopo da consolidação funcional atual

- transformar os apps atuais em microserviços;
- reescrita total da aplicação;
- depender de IA para regras básicas de negócio;
- criar decisões técnicas sem ADR;
- colocar funcionalidades de IA sobre dados sem autorização e
  rastreabilidade.

## Regra de interpretação

- pertencer ao escopo do produto não significa estar implementado;
- o current-state informará o estado real de implementação;
- o roadmap informará a ordem de entrega;
- especificações de módulos descreverão o comportamento detalhado de
  cada domínio;
- PDRs registram decisões de produto estáveis, não o estado do código.
