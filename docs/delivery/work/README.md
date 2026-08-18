---
title: Protocolo de work items
status: canonical
owner: delivery
last_reviewed: 2026-08-18
---

# Protocolo de work items

## Objetivo

Este diretório define como uma unidade do roadmap se torna um contrato
de execução — o Work Item.

- [current-state.md](../current-state.md) descreve o que o HEAD
  contém hoje.
- [roadmap.md](../roadmap.md) define a sequência oficial de fases.
- Um Work Item traduz um ponto dessa sequência em uma unidade concreta,
  auditável e executável de trabalho.
- Código e testes continuam sendo a prova de implementação, conforme a
  [hierarquia das fontes de verdade](../../README.md#hierarquia-das-fontes-de-verdade).
  Um Work Item não prova, por si, que algo foi implementado — apenas
  descreve o que deveria ser feito e, quando concluído, aponta para a
  evidência correspondente no HEAD.
- Um Work Item não se torna fonte canônica de produto, arquitetura ou
  segurança só por existir. Ele deriva autoridade das fontes que cita;
  não a substitui.

Referências de governança, produto e segurança relevantes para qualquer
Work Item:

- [../../governance/documentation-policy.md](../../governance/documentation-policy.md)
- [../../governance/decision-index.md](../../governance/decision-index.md)
- [../../governance/terminology-policy.md](../../governance/terminology-policy.md)
- [../../product/open-decisions.md](../../product/open-decisions.md)
- [../../security/overview.md](../../security/overview.md)
- [../../security/authorization-model.md](../../security/authorization-model.md)
- [../../security/data-scope.md](../../security/data-scope.md)
- [../../security/authorization-matrix.md](../../security/authorization-matrix.md)

## Hierarquia de autoridade

Um Work Item ocupa a posição mais operacional da hierarquia documental
do projeto, conforme
[../../README.md#hierarquia-das-fontes-de-verdade](../../README.md#hierarquia-das-fontes-de-verdade),
adaptada aqui à finalidade deste protocolo:

1. Governança documental — como a documentação é categorizada,
   nomeada e mantida.
2. PDRs e ADRs — decisões de produto e arquitetura aceitas e vigentes.
3. Especificações canônicas de produto.
4. Arquitetura canônica.
5. Segurança canônica.
6. `current-state.md` — fotografia verificada do HEAD.
7. `roadmap.md` — sequência oficial de fases.
8. Work Item — contrato operacional derivado dos níveis acima.

Regras que decorrem desta hierarquia:

- Um Work Item não pode sobrescrever um PDR ou ADR.
- Um Work Item não pode resolver uma decisão em aberto (`OPEN-XXX`).
- Um Work Item não pode criar um requisito de produto novo — requisitos
  de produto pertencem a uma especificação canônica ou a um PDR.
- Quando um Work Item revela uma divergência entre fontes canônicas, ou
  entre uma fonte canônica e o código, a divergência deve ser escalada
  para decisão humana, conforme a
  [Regra de conflito](../../README.md#regra-de-conflito) — nunca
  resolvida silenciosamente dentro do próprio Work Item.

## Ciclo de vida

Um Work Item existe sempre em um destes seis estados operacionais:

- **draft** — ainda incompleto ou em revisão; escopo, critérios de
  aceite ou fontes podem estar incompletos. Não deve ser executado.
- **ready** — escopo e critérios de aceite estão suficientemente
  definidos para que a execução comece.
- **in_progress** — a implementação está em andamento.
- **blocked** — existe uma dependência concreta impedindo o avanço; o
  bloqueio deve ser registrado explicitamente no corpo do item, com sua
  causa. Não deve ser usado para dificuldade técnica comum — apenas
  para impedimentos reais, como uma OPEN não resolvida necessária ao
  item, uma dependência anterior não concluída, um requisito
  contraditório, uma informação obrigatória ausente, ou uma falha
  estrutural que impede execução segura.
- **done** — só é atingido depois que todos os itens abaixo estiverem
  satisfeitos:
  - implementação concluída;
  - critérios de aceite verificados;
  - validações executadas e registradas;
  - documentação de estado atualizada, quando aplicável;
  - evidência de Git correspondente registrada.
- **superseded** — o item foi substituído por outro Work Item ou por
  uma mudança canônica. Um item substituído nunca é apagado
  silenciosamente; ele permanece no repositório com esse estado.

## Identificação

Todo Work Item recebe um identificador sequencial no formato `WI-XXXX`
(por exemplo, `WI-0001`, apenas como exemplo textual — não criado neste
lote).

Regras:

- o identificador é sequencial;
- um identificador nunca é reutilizado, mesmo que o item associado seja
  `superseded`;
- o identificador não codifica módulo, fase ou data;
- o título humano do item é separado do identificador.

Nome de arquivo futuro: `WI-XXXX-slug-curto.md` (por exemplo,
`WI-0001-aplicar-autorizacao-clientes.md`, apenas como exemplo textual
— não criado neste lote).

## Tamanho e atomicidade

Um Work Item deve ser:

- pequeno o suficiente para ser auditado por completo, de ponta a
  ponta;
- grande o suficiente para entregar um comportamento útil e observável;
- fechado em escopo, preferencialmente em torno de um único objetivo
  coerente;
- livre de decisões de produto independentes misturadas no mesmo item;
- livre de "refatorar tudo" ou de alteração oportunista fora do que o
  objetivo exige.

Atomicidade é funcional e auditável, não uma métrica arbitrária. Este
protocolo não define quantidade máxima de arquivos, linhas, horas ou
dias — esses limites não determinam, por si, se um item está bem
recortado.

## Relação com o roadmap

Todo Work Item deve indicar:

- a fase do roadmap à qual pertence;
- o objetivo daquela fase que o item atende;
- as dependências de fases ou itens anteriores;
- se pode ser executado em paralelo com outro trabalho em andamento, ou
  não.

Um Work Item não pode pular pré-requisitos de fase definidos em
[roadmap.md](../roadmap.md). A sequência atual de fases —

A — Autorização
B — Escopo
C — Integridade
D — Financeiro
E — Funcionalidades de apoio
F — Preparação IA
G — IA

— é apresentada aqui apenas como referência de leitura. `roadmap.md` é
a fonte oficial da sequência vigente; este protocolo não a duplica como
regra permanente e não impede que o roadmap evolua.

## Relação com current-state

Todo Work Item deve declarar a evidência do estado atual que motivou a
tarefa, apontando para a seção relevante de
[current-state.md](../current-state.md) em vez de copiar seu conteúdo.
Categorias de evidência aceitas:

- comportamento existente;
- lacuna constatada;
- divergência com PDR;
- cobertura de teste ausente;
- operação planejada.

A evidência apontada deve ser reconfirmada no código antes da
implementação — `current-state.md` é um registro auditado em um
commit específico, não uma garantia permanente sobre o HEAD atual.

## Fontes obrigatórias do item

Todo Work Item deve listar, em seções próprias:

- **Fontes canônicas** — PDRs, especificações de módulo,
  arquitetura e segurança relevantes para o item.
- **Evidência do HEAD** — arquivos de código e de teste que precisam
  ser auditados antes de alterar qualquer coisa.
- **Decisões abertas** — quaisquer `OPEN-XXX` que afetem o item.

Regra: se uma decisão necessária para completar o item estiver em
aberto, o agente não inventa a resposta. Ele bloqueia o Work Item, ou
executa apenas a parte do trabalho que é independente dessa decisão,
quando o próprio item permitir isso explicitamente.

## Escopo permitido

Todo Work Item deve declarar explicitamente:

- os arquivos ou áreas que podem ser alterados;
- os tipos de mudança permitidos;
- as migrations permitidas ou proibidas;
- os templates permitidos;
- os testes que podem ser criados ou alterados;
- a documentação que pode ser atualizada.

Listar um arquivo ou área nesta seção não autoriza, por si, qualquer
mudança nesse arquivo — apenas delimita onde uma mudança necessária ao
objetivo do item pode ocorrer.

## Fora de escopo

Toda alteração útil, mas não necessária para satisfazer os critérios de
aceite do item, permanece fora de escopo até ser explicitamente
incorporada a este item ou a outro.

Um achado lateral encontrado durante a execução deve ser registrado no
relatório do item — nunca implementado silenciosamente.

## Resultado observável

Antes da implementação, todo Work Item deve explicitar, em termos que o
Product Owner reconheça sem precisar ler código:

- o que o Product Owner conseguirá fazer quando o item terminar;
- o que continuará **não** coberto — principalmente comportamento
  adjacente que, visual ou conceitualmente, possa parecer incluído sem
  estar.

Esta declaração não substitui os critérios de aceite; ela é a tradução,
em linguagem observável, do que esses critérios entregam e do que
deliberadamente deixam de fora.

Distinção obrigatória em relação a "Resultado esperado"
([template.md](template.md#resultado-esperado)): **Resultado
observável** é a tradução da entrega para linguagem de produto — o que
o Product Owner consegue fazer, e o que continua não coberto, sem
precisar interpretar código. **Resultado esperado** é o comportamento
técnico resultante que a implementação e a revisão devem produzir e
verificar. Nenhuma das duas seções substitui a outra: a primeira é lida
por quem avalia o produto; a segunda é verificada por quem revisa a
implementação.

Quando o item altera comportamento diretamente observável ou
exercitável pelo usuário através do produto, pode ser necessária
validação manual dirigida por 2 a 5 cenários, além dos testes
automatizados. A regra completa pertence a
[../../development/quality-gates.md#gate-de-validação-manual-dirigida](../../development/quality-gates.md#gate-de-validação-manual-dirigida) —
este documento apenas a referencia.

## Critérios de aceite

Critérios de aceite devem ser:

- observáveis;
- verificáveis;
- relacionados a comportamento;
- livres de percentuais vagos;
- livres de expressões como "código limpo" ou "funciona corretamente";
- não dependentes apenas de inspeção visual.

Quando aplicável ao item, os critérios devem cobrir: caminho permitido,
caminho negado, usuário sem autorização, objeto fora de escopo, tenant
diferente, `POST` manipulado e integridade de relacionamento. Nem todo
item precisa cobrir todos esses casos — apenas os que forem relevantes
ao seu objetivo.

## Testes

Todo Work Item deve declarar:

- testes existentes relevantes;
- testes novos esperados;
- testes negativos esperados, quando aplicável;
- comandos de teste a executar;
- se a suíte completa é necessária ou apenas um subconjunto;
- qualquer teste que não pôde ser executado, e o motivo.

Não é permitido registrar "testes passam" sem evidência de execução. O
relatório do item deve diferenciar três coisas: teste existente, teste
executado e resultado observado.

## Migrations

Regras gerais para qualquer Work Item que envolva mudança de schema:

- não criar migration se o schema não mudou;
- criar migration apenas quando ela for necessária ao objetivo do item;
- nunca editar uma migration já aplicada apenas para "arrumar" seu
  conteúdo;
- revisar o impacto em `SHARED_APPS` versus `TENANT_APPS` antes de
  criar a migration;
- separar uma data migration de uma migration de schema quando
  necessário;
- a migration deve estar explicitamente dentro do escopo declarado do
  item.

## Segurança

Todo item que toca dados de tenant deve considerar, quando aplicável,
as camadas descritas em
[../../security/overview.md](../../security/overview.md#camadas-de-controle):
autenticação, isolamento de tenant, autorização de módulo, nível
técnico atual, habilitação funcional, autorização da ação, escopo de
dados, autorização sobre objeto específico e integridade da operação.

Referências obrigatórias para qualquer item com impacto de segurança:

- [../../security/authorization-model.md](../../security/authorization-model.md)
- [../../security/data-scope.md](../../security/data-scope.md)
- [../../security/authorization-matrix.md](../../security/authorization-matrix.md)

Princípios que todo item deve preservar:

- a interface nunca substitui a verificação equivalente no backend;
- um identificador (`id`/`pk`) não concede acesso por si só;
- uma resposta ou sugestão de IA nunca amplia o escopo que o usuário já
  teria diretamente.

## Regras de execução para agentes

Sequência geral esperada de qualquer agente que execute um Work Item:

1. confirmar branch, HEAD e status do Git;
2. ler o Work Item inteiro;
3. ler as fontes canônicas listadas no item;
4. auditar os arquivos do HEAD indicados como evidência;
5. confirmar o entendimento do escopo antes de alterar qualquer
   arquivo;
6. implementar somente o necessário para satisfazer os critérios de
   aceite;
7. executar as validações declaradas no item;
8. revisar o diff produzido;
9. comparar o resultado com os critérios de aceite;
10. atualizar a documentação permitida pelo escopo do item;
11. reportar o resultado, incluindo achados fora do escopo;
12. não fazer commit se o Work Item ou o comando da sessão em curso
    proibir.

Nenhum agente deve presumir que pode, ou deve, fazer commit
automaticamente — essa autorização depende do item e da sessão em que
ele é executado, não deste protocolo.

## Controle de escopo durante execução

Antes e depois de qualquer alteração, o agente deve verificar:

```
git status --short
git diff --name-status
git diff --stat
```

Quando houver staging autorizado pelo item ou pela sessão:

```
git diff --cached --name-status
```

Se essa verificação revelar uma alteração fora do escopo declarado do
item — feita por este agente ou já presente no diretório de trabalho
antes da execução — o agente deve parar, não esconder a alteração, não
resetar trabalho alheio, e relatar o que encontrou. Comandos
destrutivos nunca devem ser usados para "limpar" alterações externas ao
item.

## Achados fora do escopo

Um achado lateral encontrado durante a execução de um Work Item deve
ser registrado no relatório do item com:

- descrição do achado;
- evidência (arquivo, comportamento ou trecho observado);
- impacto;
- recomendação de novo Work Item, PDR ou ADR, se aplicável.

O achado não deve ser implementado silenciosamente dentro do item em
execução, mesmo que a correção pareça simples.

## Atualização de current-state

`current-state.md` deve ser atualizado quando um Work Item concluído
representar:

- implementação material nova;
- mudança de estado de um módulo (por exemplo, de "não identificado"
  para "parcialmente implementado");
- fechamento de uma lacuna relevante já registrada no documento;
- uma nova integração;
- alteração material de arquitetura observável;
- mudança relevante na cobertura de testes.

Um ajuste cosmético não justifica, por si, uma atualização de
`current-state.md`. Todo Work Item deve indicar, em sua seção de
encerramento, se espera atualizar o snapshot.

## Atualização do roadmap

`roadmap.md` não deve ser alterado apenas porque um Work Item terminou.
Ele deve ser atualizado quando:

- uma fase muda materialmente de estado;
- uma dependência entre fases muda;
- uma decisão de produto altera a sequência;
- o estado do HEAD permite avançar oficialmente de fase.

## Git e evidência de conclusão

Ao ser concluído, um Work Item deve registrar:

- a branch em que foi executado;
- o HEAD inicial (commit anterior à execução);
- os arquivos alterados;
- os testes executados;
- o resultado das validações;
- o commit final, se houver;
- o estado final do Git.

Nenhum hash de commit deve ser registrado antes de o commit existir.

### Commit de implementação e fechamento documental

Quando um item combina implementação funcional (código e testes) com
fechamento documental (registro de evidência, atualização de
`current-state.md` quando aplicável, transição para `done`), o padrão
observado é de dois commits distintos:

1. **commit de implementação** — código e testes, criado quando a
   implementação é aprovada;
2. **commit documental** — criado depois, para persistir o fechamento
   (a atualização do próprio Work Item e de `current-state.md`, quando
   aplicável), já referenciando o commit de implementação anterior.

Regras:

- o commit de implementação nunca inventa o hash do commit documental
  que ainda não existe;
- o Work Item não precisa registrar, dentro de si, o hash do commit que
  contém o seu próprio fechamento — esse hash só é conhecido depois que
  esse commit é criado, e o arquivo não pode se auto-referenciar antes
  disso;
- não é exigido um terceiro commit para este padrão;
- dois commits não são obrigatórios para todo item — quando o trabalho
  é puramente documental, sem implementação funcional separada, um
  único commit pode ser suficiente.

## Quando um item está bloqueado

`blocked` é usado somente diante de um impedimento real e concreto,
como:

- uma decisão em aberto (`OPEN-XXX`) necessária ao item, ainda não
  resolvida;
- uma dependência anterior do roadmap ainda não concluída;
- um requisito contraditório entre fontes canônicas;
- uma informação obrigatória ausente que nenhuma fonte canônica supre;
- uma falha estrutural que impede a execução segura do item.

Dificuldade técnica comum durante a implementação não é motivo para
`blocked`.

## Quando criar PDR ou ADR

- **PDR** — quando a implementação do item exigir uma nova decisão de
  produto, ainda não coberta por um PDR existente.
- **ADR** — quando houver uma decisão arquitetural relevante, duradoura
  e com alternativas significativas, ainda não coberta por um ADR
  existente.

Um Work Item nunca substitui um PDR ou um ADR — ele pode, no máximo,
registrar a necessidade de um, para decisão humana posterior.

## Encerramento

Um Work Item não é `done` apenas porque o código foi escrito. O
encerramento exige, no mínimo:

- critérios de aceite verificados;
- testes e validações registrados, com evidência de execução;
- diff revisado;
- escopo respeitado, ou desvios explicitamente relatados;
- documentação atualizada quando aplicável;
- bloqueios e achados externos registrados;
- evidência de Git registrada.
