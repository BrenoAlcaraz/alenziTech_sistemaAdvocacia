---
title: Modelos
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-31
related_pdrs:
  - PDR-0008
---

# Modelos

## Objetivo

Manter um repositório organizado de modelos de peças e documentos
jurídicos reutilizáveis pelo escritório.

## Escopo funcional

Como intenção funcional, o módulo Modelos compreende:

- cadastro manual de modelo;
- upload de peça ou documento produzido pelo usuário;
- consulta e reutilização de modelos;
- organização dos modelos dentro do tenant;
- integração futura com geração e edição assistida por IA;
- possibilidade futura de salvar conteúdo produzido com IA, após
  confirmação do usuário.

## Atores e expectativas de acesso

- Modelos pertencem ao tenant e o acervo é sempre institucional: qualquer
  usuário autorizado ao módulo Modelos alcança todos os modelos do
  tenant, não apenas os que ele mesmo cadastrou.
- Modelos não possui a dimensão de nível "somente os seus"/"todos"
  compartilhada por Processos, Clientes, Tarefas, Painel e Agenda —
  decisão registrada em 2026-08-31, resolvendo o ponto que este documento
  listava como "autoria e propriedade individual versus institucional de
  um modelo". Modelos passa a ser tratado, para efeito dessa dimensão,
  como Chat e Gerir: sem nível.
- O alcance exato desse escopo é definido em
  [docs/security/authorization-matrix.md](../../security/authorization-matrix.md).
  O estado de aplicação dessas regras no backend deve ser verificado no
  código e em [docs/delivery/current-state/modelos.md](../../delivery/current-state/modelos.md).
- Acesso a modelos deve ser verificado no backend; ocultar ou exibir
  um modelo na interface não substitui essa verificação.

## Conceitos e entidades

Este módulo não introduz uma seção própria no
[glossário funcional](../glossary.md). Um modelo não deve ser
confundido com um documento de cliente ou de processo, conforme
definidos nesse glossário e em [clientes.md](clientes.md) e
[processos.md](processos.md).

## Regras funcionais

- O upload manual de um modelo não depende de nenhuma funcionalidade
  de IA.
- A integração com IA é posterior e depende de
  [PDR-0008](../decisions/PDR-0008-ia-apos-nucleo-funcional.md).
- A IA não salva automaticamente um modelo definitivo sem confirmação
  do usuário.
- Um modelo não deve ser confundido com um documento de um cliente ou
  de um processo.
- Copiar ou reutilizar um modelo não altera silenciosamente o modelo
  original.
- O formato técnico de versionamento de modelos ainda não está
  decidido.

Os itens a seguir não são canonizados como obrigação atual por esta
especificação; podem aparecer como pontos em aberto ou evolução
futura:

- deduplicação semântica automática entre modelos;
- uma funcionalidade do tipo "meu estilo";
- geração em massa de peças;
- marca d'água, cabeçalho ou rodapé automáticos;
- comparação automática de similaridade entre peças;
- classificação automática de modelos por IA.

## Fluxos principais

1. Cadastrar modelo manualmente.
2. Anexar arquivo como modelo.
3. Consultar modelos autorizados.
4. Reutilizar um modelo sem alterar o original.
5. Sugerir, futuramente, o salvamento de conteúdo produzido por IA
   como modelo — fluxo futuro, condicionado aos pré-requisitos do
   PDR-0008 e à especificação de
   [inteligencia-artificial.md](inteligencia-artificial.md).
6. Confirmar ou rejeitar o salvamento sugerido.

## Integrações e dependências

- Modelos permanecem distintos dos documentos de
  [clientes.md](clientes.md) e de [processos.md](processos.md).
- A integração com a IA jurídica é uma dependência futura, descrita em
  [inteligencia-artificial.md](inteligencia-artificial.md),
  condicionada aos pré-requisitos de PDR-0008.

## Fora do escopo imediato

- Deduplicação automática por IA.
- Geração em massa de peças ou documentos.
- Aprendizado automático do estilo de redação do escritório.
- Edição colaborativa em tempo real.
- Criação automática de modelo sem confirmação humana.

## Pontos em aberto

- Categorias e metadados dos modelos.
- Edição direta do modelo já cadastrado.
- Versionamento de modelos.
- Aprovação de modelos antes de disponibilização.
- Deduplicação entre modelos.
- Critérios para considerar duas peças equivalentes.
- Funcionalidade do tipo "meu estilo".
- Cabeçalho, rodapé e marca d'água automáticos.
- Geração em massa de documentos.
- Formatos e limites de arquivo aceitos.
- Detalhamento da integração com IA.

## Critérios de aceite funcionais

- É possível cadastrar um modelo manualmente e anexar um arquivo como
  modelo, sem depender de nenhuma funcionalidade de IA.
- Um usuário autorizado ao módulo Modelos acessa todos os modelos do
  tenant, verificado no backend — não existe restrição por autoria.
- Reutilizar um modelo não altera o modelo original.
- Um modelo não é confundido, na especificação nem na interface, com
  um documento de cliente ou de processo.
- Quando implementada, uma sugestão de IA para salvar um modelo exige
  confirmação humana antes de se tornar definitiva.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0008 — IA após o núcleo funcional](../decisions/PDR-0008-ia-apos-nucleo-funcional.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)
- [inteligencia-artificial.md](inteligencia-artificial.md)
