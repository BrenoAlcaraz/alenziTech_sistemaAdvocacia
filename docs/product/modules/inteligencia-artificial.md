---
title: Inteligência Artificial
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-13
related_pdrs:
  - PDR-0007
  - PDR-0008
  - PDR-0009
---

# Inteligência Artificial

## Objetivo

Definir os produtos de IA planejados e seus pré-requisitos funcionais,
sem decidir tecnologia ou afirmar implementação.

## Escopo funcional

Esta especificação separa dois produtos de IA e uma interface
planejada:

### Assistente do sistema

- ajuda de uso;
- documentação;
- navegação;
- dúvidas operacionais.

### IA jurídica

- contexto do processo;
- busca em documentos;
- resumos;
- discussão de estratégia;
- geração e edição de peças;
- histórico de versões;
- integração futura com o módulo Modelos.

### Assistente/Laboratório

- interface planejada para apresentar a IA jurídica dentro do contexto
  do processo;
- não é um terceiro produto de IA — é a interface prevista para a IA
  jurídica;
- preserva separação técnica interna em relação aos demais módulos,
  quando adequado.

## Atores e expectativas de acesso

- O acesso à IA jurídica não amplia o escopo de dados já autorizado ao
  usuário.
- Uma resposta ou sugestão de IA não cria autorização adicional.
- O acesso a cada documento utilizado pela IA deve ser controlado no
  backend, do mesmo modo que o acesso direto a esse documento.
- Conhecer o identificador de um documento não concede acesso a ele.
- O alcance exato de autorização sobre a IA é definido em
  [docs/security/authorization-matrix.md](../../security/authorization-matrix.md).
  O estado de aplicação dessas regras no backend deve ser verificado no
  código e em [docs/delivery/current-state/inteligencia-artificial.md](../../delivery/current-state/inteligencia-artificial.md).
- Ocultar ou exibir um elemento de interface não substitui essa
  verificação.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Inteligência
artificial": Assistente do sistema, IA jurídica e
Assistente/Laboratório. Este documento não redefine esses termos.

## Regras funcionais

- A IA não é pré-requisito das funções básicas do sistema.
- Clientes, Processos, Tarefas, Agenda e Financeiro funcionam sem IA.
- Assistente do sistema e IA jurídica são produtos distintos.
- A IA jurídica opera apenas sobre conteúdo autorizado ao usuário.
- A interface de IA não amplia o escopo de acesso do usuário.
- Uma resposta ou sugestão de IA não cria autorização.
- A identificação futura de honorários pela IA gera uma sugestão,
  conforme
  [PDR-0007](../decisions/PDR-0007-honorarios-manuais-antes-ia.md).
- Uma sugestão de honorário exige confirmação humana, conforme
  [financeiro.md](financeiro.md).
- A integração futura com Modelos não salva um modelo definitivo sem
  confirmação do usuário, conforme [modelos.md](modelos.md).
- Tecnologia, provedor e modelo de linguagem não são decididos por
  esta especificação.

### Pré-requisitos obrigatórios da IA jurídica

- Autorização aplicada no backend.
- Escopo de dados aplicado.
- Isolamento entre tenants.
- Acesso seguro a documentos.
- Dados processuais estruturados.
- Histórico e rastreabilidade.
- Módulos centrais estáveis.
- Controle de acesso a cada documento utilizado.
- Impossibilidade de acessar um dado apenas por conhecer seu
  identificador.

Esta especificação não inventa provedor, modelo de linguagem, banco
vetorial, arquitetura RAG, política de retenção, preço, limite de uso,
ferramenta de busca jurídica ou promessa de precisão.

## Fluxos principais

**Assistente do sistema**

1. Fazer uma pergunta operacional.
2. Receber orientação de uso do produto.

**IA jurídica futura** — os fluxos abaixo representam comportamento
planejado, condicionado aos pré-requisitos desta especificação e do
PDR-0008:

1. Abrir o Assistente/Laboratório dentro de um processo autorizado.
2. Selecionar ou acessar documentos autorizados.
3. Solicitar resumo, busca ou discussão sobre o processo.
4. Solicitar geração ou edição de peça.
5. Revisar o conteúdo gerado.
6. Salvar uma versão ou encaminhar o conteúdo para Modelos, quando
   autorizado.
7. Confirmar sugestões que alterem registros do sistema, como um
   honorário sugerido.

## Integrações e dependências

- Depende dos pré-requisitos consolidados em Processos, conforme
  [processos.md](processos.md) e PDR-0008.
- Depende do módulo Modelos para a integração futura de geração e
  salvamento de peças, conforme [modelos.md](modelos.md).
- Depende do módulo Financeiro para a sugestão futura de honorários,
  conforme [financeiro.md](financeiro.md) e PDR-0007.

## Fora do escopo imediato

- IA antes da consolidação do núcleo funcional.
- Leitura autônoma irrestrita de todos os documentos do tenant.
- Busca jurídica externa sem provedor e regras definidos.
- Automação financeira irreversível.
- Criação automática definitiva de honorários.
- Geração em massa de peças ou documentos.
- Decisões jurídicas autônomas.
- Acesso a documento não autorizado.

## Pontos em aberto

- Provedor e modelo de linguagem.
- Arquitetura técnica da IA.
- Indexação e busca documental.
- Retenção de prompts e respostas.
- Logs e auditoria de uso.
- Limites por plano.
- Custo e cobrança do uso de IA.
- Pesquisa jurídica externa.
- Exigência de indicação de fontes nas respostas.
- Política de versões das peças geradas.
- Aprovação ou revisão de conteúdo gerado.
- OCR e tratamento de documentos escaneados.
- Segurança contra instruções maliciosas embutidas em documentos.
- Política para dados enviados a provedores externos.

## Critérios de aceite funcionais

- Nenhuma funcionalidade essencial do núcleo (Clientes, Processos,
  Participantes, Tarefas, Agenda, Financeiro) exige IA para operar.
- Assistente do sistema e IA jurídica são apresentados como
  funcionalidades distintas, não intercambiáveis.
- A implementação da IA jurídica só é iniciada após autorização,
  escopo de dados, acesso seguro a documentos, dados processuais
  estruturados, histórico, rastreabilidade e módulos centrais estarem
  consolidados.
- Uma resposta ou sugestão de IA nunca concede acesso a um dado que o
  usuário não estivesse previamente autorizado a ver.
- Quando implementada, uma sugestão de honorário gerada por IA exige
  confirmação humana antes de se tornar um lançamento definitivo.
- Quando implementada, a interface da IA jurídica aparece no contexto
  visual do processo, como painel do tipo Assistente/Laboratório.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0007 — Honorários manuais antes da IA](../decisions/PDR-0007-honorarios-manuais-antes-ia.md)
- [PDR-0008 — IA após o núcleo funcional](../decisions/PDR-0008-ia-apos-nucleo-funcional.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)
- [processos.md](processos.md)
- [modelos.md](modelos.md)
- [financeiro.md](financeiro.md)
