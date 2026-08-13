---
title: Workflow de desenvolvimento
status: canonical
owner: development
last_reviewed: 2026-08-06
---

# Workflow de desenvolvimento

## Objetivo

Este documento define o ciclo operacional que qualquer execução de
trabalho neste repositório deve seguir, do início de uma unidade de
trabalho até seu fechamento. Ele é **executor-agnóstico**: aplica-se
igualmente a uma pessoa desenvolvendo manualmente e a um agente de IA
executando a mesma tarefa. Nenhuma etapa deste documento depende de um
executor específico, de um produto de IA específico, de sintaxe
proprietária de alguma ferramenta, de tamanho de contexto ou de
quantidade de tokens.

Este documento não substitui:

- [docs/delivery/work/README.md](../delivery/work/README.md) — o
  protocolo de Work Items, sua estrutura e seu ciclo de vida;
- [testing.md](testing.md) — a estratégia e os comandos de teste;
- [quality-gates.md](quality-gates.md) — os critérios de validação antes
  do encerramento de um item;
- [git-procedure.md](git-procedure.md) — o procedimento de Git para
  working tree, staging, commit, push e line endings.

Este documento define **como executar**; ele não define **o que**
construir (isso pertence a `docs/product/`), **como o sistema é
estruturado** (`docs/architecture/`), nem **os controles de segurança**
(`docs/security/`).

## Princípio central

> O Work Item define a unidade operacional e o escopo; as fontes
> canônicas governam produto, arquitetura e segurança; o HEAD do
> repositório prova o estado efetivamente implementado.

Um Work Item **não autoriza**:

- redefinir produto;
- resolver uma decisão em aberto (`OPEN-XXX`) silenciosamente;
- alterar arquitetura fora do escopo declarado;
- fazer refatoração lateral não necessária ao objetivo do item;
- modificar um arquivo porque "seria melhor", sem relação com os
  critérios de aceite do item.

Qualquer necessidade que exceda o que o Work Item autoriza é tratada
como achado fora do escopo — ver "Achados fora do escopo" abaixo — nunca
implementada silenciosamente.

## Estados do Work Item

Este documento usa exatamente os seis estados definidos em
[docs/delivery/work/README.md#ciclo-de-vida](../delivery/work/README.md#ciclo-de-vida):

```text
draft
ready
in_progress
blocked
done
superseded
```

Nenhum outro estado (por exemplo, "review", "qa", "approved",
"completed", "merged" ou "closed") é tratado como estado operacional de
Work Item por este workflow.

### `ready`

Um item só pode sair de `ready` para `in_progress` quando escopo,
critérios de aceite e dependências permitem execução segura — ou seja,
quando a Etapa 5 ("Confirmar executabilidade") deste workflow, abaixo,
tiver sido concluída sem apontar impedimento.

### `in_progress`

A mudança para `in_progress` só ocorre depois de:

- preflight válido (Etapa 1);
- leitura integral do Work Item (Etapa 2);
- leitura das fontes canônicas necessárias (Etapa 3);
- auditoria mínima do HEAD relevante ao item (Etapa 4);
- confirmação de que nenhuma decisão indispensável ao item permanece em
  aberto (Etapa 5).

A mudança de estado deve ser registrada no próprio Work Item quando essa
alteração estiver dentro do escopo autorizado do item (o protocolo de
Work Items trata o próprio arquivo do item como algo que a execução
atualiza).

### `blocked`

Usado somente diante de um impedimento real, conforme
[docs/delivery/work/README.md#quando-um-item-está-bloqueado](../delivery/work/README.md#quando-um-item-está-bloqueado) —
por exemplo, uma `OPEN-XXX` necessária ainda não resolvida, uma
dependência de fase anterior não concluída, um requisito contraditório
entre fontes canônicas, uma informação obrigatória ausente, ou uma falha
estrutural que impede execução segura. Dificuldade técnica comum não é
motivo para `blocked`.

### `done`

`done` não significa apenas "código escrito". Exige, no mínimo:

- critérios de aceite verificados com evidência, não por inferência;
- testes e validações executados e registrados, conforme
  [testing.md](testing.md) e [quality-gates.md](quality-gates.md);
- diff revisado (técnica e de escopo);
- documentação aplicável atualizada;
- evidência de Git registrada no Work Item.

Commit e push **não são obrigatórios em todo contexto** para um item
chegar a `done`. Quando commit não tiver sido autorizado na execução em
questão, o Work Item pode registrar, como evidência Git válida:

```text
commit não autorizado nesta execução
```

## Sequência operacional

### Etapa 1 — Preflight

Antes de qualquer leitura de Work Item ou alteração de arquivo,
registrar o estado real do repositório:

```text
branch
HEAD
git status
upstream, quando relevante
```

Comandos correspondentes em
[git-procedure.md#preflight](git-procedure.md#git--preflight).

Se houver qualquer alteração externa não compreendida no diretório de
trabalho (arquivo modificado, staged ou não rastreado sem relação com a
execução que está começando): **parar**. Não esconder, não resetar, não
sobrescrever. Relatar o que foi encontrado antes de prosseguir.

### Etapa 2 — Ler o Work Item integralmente

Ler o arquivo do Work Item por completo, não apenas as seções de
objetivo ou critérios. Conferir, no mínimo:

- estado atual (`draft`/`ready`/`in_progress`/`blocked`/`done`/`superseded`);
- fase do roadmap e objetivo relacionado;
- objetivo do item;
- fontes canônicas listadas;
- arquivos do HEAD a auditar antes da implementação;
- escopo permitido e fora de escopo;
- decisões abertas e bloqueios;
- critérios de aceite;
- testes esperados;
- quality gates declarados;
- dependências de outros itens ou fases.

### Etapa 3 — Ler fontes canônicas

Ler apenas as fontes canônicas necessárias ao Work Item em questão —
aquelas listadas em sua seção "Fontes canônicas". Este workflow não
transforma cada execução em releitura indiscriminada de todo o
repositório.

### Etapa 4 — Auditar o HEAD

Reconfirmar, por leitura direta do código no HEAD atual, a evidência
listada no Work Item em "Arquivos do HEAD a auditar antes da
implementação". A evidência registrada no próprio item (ou em
[current-state.md](../delivery/current-state.md)) foi capturada em um
commit específico e pode estar desatualizada em relação ao HEAD real no
momento da execução. Não implementar sobre uma premissa documental
desatualizada sem antes reconfirmá-la no código.

### Etapa 5 — Confirmar executabilidade

Se a auditoria da Etapa 4 revelar que uma premissa central do item
mudou desde que ele foi escrito:

- ajustar o próprio Work Item, quando isso for permitido pelo escopo e
  não alterar o requisito em si (por exemplo, corrigir um caminho de
  arquivo incorreto);
- ou registrar o achado, conforme "Achados fora do escopo" abaixo;
- ou bloquear o item (`blocked`), quando a mudança impedir execução
  segura.

Não improvisar política nem preencher lacuna de decisão com suposição —
ver [docs/governance/documentation-policy.md#uso-por-agentes-de-ia](../governance/documentation-policy.md#uso-por-agentes-de-ia).

### Etapa 6 — Marcar `in_progress`

Somente depois de concluídas as Etapas 1 a 5 sem impedimento. Ver
"Estados do Work Item" acima.

### Etapa 7 — Implementar a menor alteração coerente

Implementar apenas o necessário para satisfazer os critérios de aceite
declarados, dentro do escopo permitido do item. Não incluir:

- refatoração oportunista;
- "limpeza" lateral de código não relacionado;
- renomeações não necessárias ao objetivo do item;
- novas dependências sem previsão no escopo do item;
- mudanças de schema não autorizadas explicitamente pelo item.

### Etapa 8 — Testar incrementalmente

Conforme a estratégia definida em [testing.md](testing.md) e os gates de
teste de [quality-gates.md](quality-gates.md): teste alvo primeiro,
depois a regressão relevante.

### Etapa 9 — Rodar quality gates

Rodar apenas os gates relevantes ao item, conforme
[quality-gates.md](quality-gates.md) — obrigatórios sempre, condicionais
conforme o tipo de alteração feita.

### Etapa 10 — Revisar o diff

Revisão técnica (o código faz o que deveria, sem efeito colateral não
intencional) e revisão de escopo (nenhum arquivo fora do escopo
permitido foi alterado), conforme
[docs/delivery/work/README.md#controle-de-escopo-durante-execução](../delivery/work/README.md#controle-de-escopo-durante-execução).

### Etapa 11 — Atualizar documentação

O Work Item sempre registra sua própria execução (evidência, arquivos
alterados, testes, resultado). Atualizar
[current-state.md](../delivery/current-state.md) apenas quando houver
mudança material, conforme
[docs/delivery/work/README.md#atualização-de-current-state](../delivery/work/README.md#atualização-de-current-state).
Atualizar [roadmap.md](../delivery/roadmap.md) apenas conforme o
protocolo já estabelecido em
[docs/delivery/work/README.md#atualização-do-roadmap](../delivery/work/README.md#atualização-do-roadmap).
Um ajuste cosmético não justifica, por si, nenhuma dessas duas
atualizações.

### Etapa 12 — Fechar critérios

Cada critério de aceite (cada checkbox do Work Item) deve possuir
evidência verificável antes de ser marcado como cumprido. Não marcar um
critério por inferência ou por semelhança com outro item.

### Etapa 13 — Atualizar estado do Work Item

`done`, `blocked`, ou permanecer `in_progress`, de acordo com a
evidência real reunida nas etapas anteriores — nunca por conveniência de
encerrar a sessão de trabalho.

### Etapa 14 — Staging

Somente quando staging estiver autorizado para esta execução. Ver
[git-procedure.md#staging](git-procedure.md#git--staging).

### Etapa 15 — Commit

Somente quando commit estiver autorizado para esta execução. Ver
[git-procedure.md#commit](git-procedure.md#git--commit).

### Etapa 16 — Push

Somente quando push estiver autorizado para esta execução. Ver
[git-procedure.md#push](git-procedure.md#git--push).

### Etapa 17 — Relatório final

Reportar, ao final de qualquer execução: estado do Work Item, arquivos
alterados, testes executados e resultado, quality gates aplicados e
resultado, achados fora do escopo, se houve commit e/ou push, e o estado
final do Git (`git status --short`, `git diff --stat`).

## Achados fora do escopo

Quando, durante a execução, surgir um problema útil mas não necessário
ao Work Item em andamento:

1. não implementar a correção silenciosamente;
2. registrar a evidência (arquivo, comportamento ou trecho observado);
3. explicar o impacto;
4. classificar o destino provável: novo Work Item, PDR, ADR, outra fase
   do roadmap, ou apenas documentação;
5. continuar a execução do item atual normalmente, desde que o achado
   não bloqueie sua conclusão.

Se o achado bloquear de fato a execução do item (não apenas revelar uma
melhoria possível), o item passa para `blocked`, conforme "Estados do
Work Item" acima — não para uma ampliação de escopo improvisada.

Um achado lateral nunca autoriza, por si, expandir o escopo do item em
execução. Ver também
[docs/delivery/work/README.md#achados-fora-do-escopo](../delivery/work/README.md#achados-fora-do-escopo).

## Falhas de teste

Uma falha de teste deve ser tratada com cuidado, porque pode ter
origens muito diferentes:

- causada pela alteração feita nesta execução;
- preexistente ao início da execução;
- ambiental (por exemplo, dependência externa indisponível);
- incompatibilidade de fixture;
- divergência entre um teste histórico e o código atual — ver o exemplo
  já registrado em
  [testing.md#divergências-conhecidas-na-suíte](testing.md#divergências-conhecidas-na-suíte);
- falha real de requisito.

Não é permitido declarar uma falha como "preexistente" sem evidência —
quando necessário, comparar o resultado com uma execução da suíte antes
do diff atual (baseline).

Se um teste relevante falhar por causa da alteração feita nesta
execução, o Work Item **não pode chegar a `done`**.

Se a falha for externa, comprovada, e não invalidar os critérios de
aceite do item, ela é registrada como achado fora do escopo, conforme a
seção acima — não como justificativa para ignorar a falha.

Nunca apagar, editar ou desabilitar um teste apenas para tornar a
execução "verde", a menos que alterar esse teste específico faça parte
explicitamente do escopo do Work Item em execução.

## Referências

- [docs/delivery/work/README.md](../delivery/work/README.md)
- [testing.md](testing.md)
- [quality-gates.md](quality-gates.md)
- [git-procedure.md](git-procedure.md)
- [commands.md](commands.md)
- [docs/delivery/current-state.md](../delivery/current-state.md)
- [docs/delivery/roadmap.md](../delivery/roadmap.md)
- [docs/governance/documentation-policy.md](../governance/documentation-policy.md)
