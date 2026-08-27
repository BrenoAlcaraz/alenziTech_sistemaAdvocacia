---
title: Processos
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-20
related_pdrs:
  - PDR-0001
  - PDR-0008
  - PDR-0009
  - PDR-0010
  - PDR-0011
  - PDR-0012
---

# Processos

## Objetivo

Centralizar processos judiciais e casos extrajudiciais, seus dados,
participantes, documentos, andamentos, vínculos e prazos.

## Escopo funcional

- cadastro e edição de processos;
- clientes representados;
- participantes;
- representantes;
- autoridades;
- andamentos;
- documentos;
- fases;
- status;
- prazos;
- processos apensos;
- tempo decorrido desde o último andamento;
- contexto futuro do Assistente/Laboratório.

## Atores e expectativas de acesso

O Administrador do escritório deve poder acessar e gerenciar qualquer
processo do tenant. Demais usuários devem alcançar processos conforme
o papel de acesso, as habilitações e o escopo de dados que lhes forem
aplicados — na direção vigente, escopo por responsável. Equipe só
poderá participar em evolução posterior expressamente decidida.

Esta seção descreve necessidade funcional, não uma matriz técnica
definitiva de permissões; essa matriz é
[docs/security/authorization-matrix.md](../../security/authorization-matrix.md).
O estado de aplicação dessas regras no backend deve ser verificado no
código e em [docs/delivery/current-state.md](../../delivery/current-state.md).
Autorização e escopo de dados devem ser aplicados no backend, não
apenas ocultando elementos de interface.

Para a versão atual,
[PDR-0010](../decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
formaliza que o módulo `processos` é tratado como uma unidade binária
de autorização: módulo habilitado dá acesso a todas as operações
atualmente existentes, sem checagem de habilitação granular por
operação. Escopo por `Processo.responsavel`, responsabilidade
obrigatória e a independência do módulo Clientes na seleção de
clientes em Processos são direção aprovada pelo mesmo PDR, para
implementação no WI-0005 — não implementadas nesta versão. Equipe não
concede acesso nem filtra Processos nesse escopo; `Da equipe` e
hierarquia de equipes permanecem para evolução posterior.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Clientes e processos":
processo judicial, caso extrajudicial, participante processual,
posição estrutural, qualificação processual, representante, autoridade
processual, processo apenso, andamento processual, documento
processual, fase processual e status processual. Este documento não
redefine esses termos.

## Regras de participantes

As regras de participantes processuais são formalizadas em
[PDR-0001 — Participantes processuais](../decisions/PDR-0001-participantes-processuais.md)
e complementadas pela taxonomia inicial e pela regra de representação de
[PDR-0011](../decisions/PDR-0011-taxonomia-representacao-participantes-processos.md).
Elas não são duplicadas integralmente aqui. Em síntese, um processo deve
suportar:

- múltiplos clientes representados pelo escritório;
- múltiplas pessoas em cada posição estrutural (polo ativo, polo
  passivo, terceiros);
- terceiros;
- Ministério Público, distinguindo atuação como parte e como fiscal
  da ordem jurídica;
- representantes registrados separadamente das partes, vinculados a
  cada participante;
- autoridades processuais registradas separadamente das partes;
- reutilização do cadastro de Cliente quando o participante já é
  cliente do escritório, sem redigitação de dados;
- criação automática de um único participante para `Processo.cliente`, mesmo
  sem CPF/CNPJ, com estado de classificação pendente restrito a esse vínculo
  enquanto posição e qualificação ainda não forem informadas;
- apresentação dos participantes em grupos dinâmicos por posição
  estrutural, com adaptação para telas menores;
- mudança de qualificação processual sem duplicar a pessoa
  participante;
- rastreabilidade histórica das mudanças relevantes de qualificação
  processual.

## Andamentos e documentos

- Andamentos são registrados em ordem cronológica.
- Um andamento pode possuir anexos.
- O usuário responsável pela inclusão de cada andamento deve ser
  identificável.
- O último andamento registrado serve de referência para o contador de
  tempo decorrido desde a última movimentação.
- Documentos relacionados ao processo não devem depender de nenhuma
  funcionalidade de IA para existir.

## Fase e status

Fase processual, status processual e andamento processual são
conceitos distintos, conforme definido no
[glossário funcional](../glossary.md):

- fase processual é a etapa do rito em que o processo se encontra;
- status processual é a situação corrente do processo;
- andamento processual é um evento registrado na tramitação.

As fontes históricas — o feedback funcional pós-Fase 1 e o plano
consolidado da Fase 2 — registram, de forma consistente entre si, uma
lista de cinco fases processuais:

- conhecimento;
- recursal;
- cumprimento de sentença;
- execução;
- outro.

Esta especificação adota esses valores como lista funcional inicial,
com base na concordância entre o feedback funcional posterior à Fase 1
e o plano consolidado da Fase 2. Uma alteração incompatível deverá
atualizar esta especificação e, quando representar mudança relevante
de produto, ser registrada por PDR.

A lista extensa de valores de status processual presente no feedback
funcional pós-Fase 1 não é elevada a enumeração canônica definitiva
por esta especificação, por não haver decisão aprovada sobre ela. Este
ponto permanece registrado em "Pontos em aberto".

## Apensos

Conforme
[PDR-0012 — Relação simétrica de processos apensos](../decisions/PDR-0012-relacao-simetrica-processos-apensos.md),
a primeira versão usa relação bidirecional sem hierarquia de negócio:

- dois Processos existentes podem ser relacionados simetricamente;
- ambos possuem identificação própria e permanecem independentes;
- A exibe B e B exibe A, com navegação nos dois sentidos;
- Cliente, responsável, equipe, status, fase, participantes, representantes,
  autoridades, andamentos, prazos e documentos não são copiados, fundidos,
  herdados nem propagados;
- remover a relação não exclui nenhum Processo;
- A ↔ B e B ↔ C não inferem A ↔ C;
- “menor” e “maior”, quando usados na persistência, são apenas normalização
  técnica do par e não significam principal, pai ou filho.

## IA

- O Assistente/Laboratório é uma funcionalidade futura, definida em
  [PDR-0008 — IA após o núcleo funcional](../decisions/PDR-0008-ia-apos-nucleo-funcional.md).
- Nenhuma funcionalidade essencial deste módulo — cadastro,
  participantes, documentos ou andamentos — exige IA para operar.
- A implementação do Assistente/Laboratório depende dos pré-requisitos
  definidos em PDR-0008 (autorização aplicada, escopo de dados
  definido, acesso seguro a documentos, dados processuais
  estruturados, histórico e rastreabilidade, módulos centrais
  estáveis).

## Fluxos principais

1. Criar processo com cliente já existente.
2. Criar cliente durante o fluxo de criação de processo — somente se
   suportado pela interface; o mecanismo exato (modal, nova aba ou
   outro) não está decidido nesta especificação.
3. Adicionar cliente representado a um processo.
4. Adicionar participante externo (parte contrária, terceiro,
   Ministério Público).
5. Adicionar representante a um participante.
6. Adicionar autoridade processual.
7. Registrar andamento e respectivo anexo.
8. Relacionar simetricamente dois Processos como apensos.
9. Registrar prazo processual.
10. Consultar o histórico de um processo.

Nenhum destes fluxos deve ser tratado como obrigatório além do que as
fontes efetivamente suportam; em especial, o fluxo 2 é uma
possibilidade sugerida historicamente, não uma obrigação formalizada.

## Integrações e dependências

- Depende do módulo Clientes para reaproveitar o cadastro de cliente
  como participante processual.
- Fornece prazos processuais que devem poder aparecer na Agenda,
  conforme [agenda.md](agenda.md).
- O Assistente/Laboratório é uma dependência futura, condicionada aos
  pré-requisitos do PDR-0008, e não uma dependência do núcleo deste
  módulo.

## Fora do escopo imediato

- Assistente/Laboratório, até que os pré-requisitos do PDR-0008
  estejam consolidados.
- OCR de documentos processuais.
- Integração com APIs de tribunais.
- Determinação automática de status processual por IA.

## Pontos em aberto

- Lista canônica definitiva de valores de status processual — a
  enumeração histórica extensa não foi elevada a decisão aprovada.
- Suporte a relator, desembargador, perito e outras autoridades ou
  auxiliares além de juiz na seção de Autoridades — mencionado nas
  fontes como evolução futura, não como obrigação de PDR-0001.
- Mecanismo exato de criação rápida de cliente durante o fluxo de
  processo (modal, nova aba ou outro).
- Estrutura técnica do histórico de mudanças de qualificação
  processual — PDR-0001 exige rastreabilidade, mas não define o
  mecanismo.
- Se a lista de fases processuais será fixa, configurável pelo
  escritório ou extensível por configuração administrativa.

## Critérios de aceite funcionais

- É possível registrar em um mesmo processo mais de um cliente
  representado, mais de uma pessoa no polo ativo, mais de uma no polo
  passivo, terceiros e o Ministério Público, simultaneamente.
- Um cliente já vinculado ao processo aparece automaticamente entre os
  participantes, com dados preenchidos a partir do cadastro de
  Cliente.
- Um advogado é sempre registrado como representante vinculado a um
  participante, nunca como parte do processo.
- Uma mudança de qualificação processual não gera um novo registro de
  pessoa participante.
- Processos relacionados como apensos permanecem independentes e navegáveis
  nos dois sentidos, sem hierarquia ou fusão de dados.
- Nenhuma funcionalidade essencial do módulo exige IA para operar.
- Quando implementado, o Assistente/Laboratório aparece no contexto
  visual do processo, condicionado aos pré-requisitos de PDR-0008.
- Andamentos aparecem em ordem cronológica.
- Um andamento pode possuir anexo.
- O usuário que incluiu o andamento é identificável.
- O contador de inatividade utiliza a data do último andamento.
- Fase, status e andamento são tratados como conceitos distintos.
- Processos relacionados como apensos permanecem registros independentes.

## Referências canônicas

- [Glossário funcional](../glossary.md)
- [PDR-0001 — Participantes processuais](../decisions/PDR-0001-participantes-processuais.md)
- [PDR-0008 — IA após o núcleo funcional](../decisions/PDR-0008-ia-apos-nucleo-funcional.md)
- [PDR-0009 — Sequência revisada da Fase 2](../decisions/PDR-0009-sequencia-fase-2.md)
- [PDR-0010 — Autorização, escopo e responsabilidade de Processos](../decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [PDR-0011 — Taxonomia e representação de participantes de Processos](../decisions/PDR-0011-taxonomia-representacao-participantes-processos.md)
- [PDR-0012 — Relação simétrica de processos apensos](../decisions/PDR-0012-relacao-simetrica-processos-apensos.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)

A lista de fases processuais registrada acima é apoiada por fontes
históricas não canônicas — o feedback funcional pós-Fase 1 e o plano
consolidado da Fase 2 — referenciadas apenas como contexto explicativo
de um ponto ainda não formalizado por PDR.
