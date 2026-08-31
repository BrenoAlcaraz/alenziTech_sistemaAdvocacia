---
title: Processos
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-31
related_pdrs:
  - PDR-0001
  - PDR-0008
  - PDR-0009
  - PDR-0010
  - PDR-0012
  - PDR-0013
  - PDR-0014
---

# Processos

## Objetivo

Centralizar processos judiciais e casos extrajudiciais, seus dados,
participantes, documentos, andamentos, vínculos e prazos.

## Escopo funcional

- cadastro e edição de processos;
- clientes representados;
- partes e respectivos advogados;
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
código e em [docs/delivery/current-state/processos.md](../../delivery/current-state/processos.md).
Autorização e escopo de dados devem ser aplicados no backend, não
apenas ocultando elementos de interface.

Para a versão atual,
[PDR-0010](../decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
formaliza que o módulo `processos` é tratado como uma unidade binária
de autorização: módulo habilitado dá acesso a todas as operações
atualmente existentes, sem checagem de habilitação granular por
operação. Escopo por `Processo.responsavel`, responsabilidade
obrigatória e a independência do módulo Clientes na seleção de
clientes em Processos são regras aprovadas pelo mesmo PDR. Equipe não
concede acesso nem filtra Processos nesse escopo; `Da equipe` e
hierarquia de equipes permanecem para evolução posterior.

[PDR-0014](../decisions/PDR-0014-responsavel-integrantes-processos.md)
abre uma única exceção a essa autorização binária: atribuir ou
reatribuir o responsável principal de um processo exige a habilitação
`processos_atribuir_responsavel` ("Atribuir responsabilidade de
processos"), disponível também ao Administrador do escritório por sua
autoridade administrativa geral. Nenhuma outra operação do módulo é
afetada por essa exceção.

## Conceitos e entidades

Os conceitos deste módulo são definidos no
[glossário funcional](../glossary.md), seção "Clientes e processos":
processo judicial, caso extrajudicial, participante processual,
parte processual, papel processual, advogado da parte, processo apenso,
andamento processual, documento processual, fase processual e status
processual. Os termos históricos posição estrutural, qualificação
processual, representante e autoridade processual não descrevem o modelo
vigente de Partes.

## Regras de participantes

As regras de participantes processuais (Partes) são formalizadas em
[PDR-0013 — Partes de processo: modelo simplificado](../decisions/PDR-0013-partes-processo-modelo-simplificado.md).
Elas não são duplicadas integralmente aqui. Em síntese, um processo deve
suportar:

- múltiplas partes, cada uma com um único campo de papel processual,
  dentre dez opções (Autor, Embargante, Recorrente, Réu, Embargado,
  Recorrido, Terceiro Interessado, Ministério Público, Amicus Curiae,
  Juiz), apresentadas em três grupos visuais (Polo Ativo, Polo Passivo,
  Outros);
- reutilização do cadastro de Cliente quando a parte corresponde ao
  Cliente do processo, sem redigitação de dados;
- pré-preenchimento automático dos campos de advogado quando a parte
  corresponde ao Cliente do processo por CPF/CNPJ;
- advogado registrado como texto livre (nome e OAB) associado
  diretamente à parte, no máximo um por parte.

PDR-0011, que aprovava um modelo de três dimensões, representantes
normalizados e classificação pendente, foi substituído por PDR-0013 e
permanece apenas como registro histórico.

## Responsabilidade e integrantes habilitados

Conforme
[PDR-0014 — Responsável principal e integrantes habilitados de Processos](../decisions/PDR-0014-responsavel-integrantes-processos.md):

- cada processo tem um único responsável principal, obrigatório, que é a
  referência do processo para distribuição de prazos na Agenda,
  indicadores e Análise de dados por usuário;
- cada processo pode ter, além do responsável principal, N integrantes
  habilitados — usuários que participam do processo sem se tornarem
  responsáveis principais automaticamente;
- apenas o responsável principal recebe automaticamente na Agenda os
  prazos gerados para o processo; integrantes habilitados não recebem;
- atribuir ou reatribuir o responsável principal exige a habilitação
  `processos_atribuir_responsavel` ("Atribuir responsabilidade de
  processos") ou a autoridade administrativa do Administrador do
  escritório;
- gerenciar quem são os integrantes habilitados de um processo exige a
  habilitação já existente `gerir_habilitar_usuario_processos`
  ("Habilitar usuário em processos").

## Arquivamento

"Arquivar processo" altera a situação processual para `arquivado`; o
processo sai da lista principal e passa a aparecer na listagem de
arquivados, podendo ser desarquivado de volta a `ativo`. Na versão
regida por PDR-0010/PDR-0014, a operação segue a autorização binária do
módulo e a fronteira de mutação por responsabilidade; não existe
habilitação granular específica para arquivar. Processos arquivados não
entram nos painéis operacionais do Painel (Paralisados, Prazos a vencer
etc.), mas continuam disponíveis na Análise de dados, quando filtrados.

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
- Cliente, responsável, integrantes habilitados, equipe, status, fase,
  partes, advogados, andamentos, prazos e documentos não são copiados,
  fundidos, herdados nem propagados;
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
4. Adicionar parte (papel processual, com advogado opcional em texto
   livre).
5. Registrar andamento e respectivo anexo.
6. Relacionar simetricamente dois Processos como apensos.
7. Registrar prazo processual.
8. Consultar o histórico de um processo.
9. Atribuir ou reatribuir o responsável principal do processo.
10. Adicionar ou remover integrante habilitado do processo.
11. Arquivar ou desarquivar um processo.

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
- Suporte a relator, desembargador, perito e outros papéis além dos dez
  aprovados por PDR-0013 — exige nova decisão de produto.
- Mecanismo exato de criação rápida de cliente durante o fluxo de
  processo (modal, nova aba ou outro).
- Se o Cliente vinculado ao processo deve gerar automaticamente uma
  Parte correspondente — ponto deixado em aberto por PDR-0013.
- Se a lista de fases processuais será fixa, configurável pelo
  escritório ou extensível por configuração administrativa.

## Critérios de aceite funcionais

- É possível registrar em um mesmo processo múltiplas partes, cada uma
  com um único papel processual, incluindo mais de uma no mesmo grupo
  visual (Polo Ativo, Polo Passivo, Outros) e o Ministério Público.
- Quando uma parte corresponde ao Cliente do processo por CPF/CNPJ, os
  campos de advogado dessa parte são pré-preenchidos automaticamente.
- Um advogado é sempre registrado como texto livre (nome e OAB)
  associado a uma parte, nunca como parte em si do processo.
- Processos relacionados como apensos permanecem independentes e navegáveis
  nos dois sentidos, sem hierarquia ou fusão de dados.
- Cada processo tem um único responsável principal, obrigatório; pode ter
  N integrantes habilitados além dele.
- Apenas o responsável principal recebe automaticamente prazos do
  processo na Agenda.
- Reatribuir o responsável principal exige `processos_atribuir_responsavel`
  ou a autoridade do Administrador do escritório.
- Arquivar um processo segue a autorização binária do módulo e a
  fronteira de mutação por responsabilidade; não existe habilitação
  granular separada para essa ação.
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
- [PDR-0012 — Relação simétrica de processos apensos](../decisions/PDR-0012-relacao-simetrica-processos-apensos.md)
- [PDR-0013 — Partes de processo: modelo simplificado](../decisions/PDR-0013-partes-processo-modelo-simplificado.md)
- [PDR-0014 — Responsável principal e integrantes habilitados de Processos](../decisions/PDR-0014-responsavel-integrantes-processos.md)
- [Visão do produto](../vision.md)
- [Escopo do produto](../scope.md)
- [Política de terminologia](../../governance/terminology-policy.md)

A lista de fases processuais registrada acima é apoiada por fontes
históricas não canônicas — o feedback funcional pós-Fase 1 e o plano
consolidado da Fase 2 — referenciadas apenas como contexto explicativo
de um ponto ainda não formalizado por PDR.
