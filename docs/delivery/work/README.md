---
title: Protocolo de work items
status: canonical
owner: delivery
last_reviewed: 2026-08-27
---

# Protocolo de work items

## Objetivo

Um Work Item (WI) transforma uma necessidade do roadmap em contrato de
execução pequeno, auditável e limitado. Ele não substitui PDR, ADR,
especificação de módulo, arquitetura ou segurança; aponta somente as fontes
aplicáveis.

O [template V2](template.md) vale para novos WIs. Itens antigos permanecem
como registro histórico e não precisam ser reescritos retroativamente.

## Hierarquia de autoridade

A hierarquia oficial está em
[docs/README.md](../../README.md#hierarquia-das-fontes-de-verdade). O WI é a
camada operacional: não sobrescreve decisão canônica, não resolve
`OPEN-XXX` nem cria requisito novo. Divergência relevante entre fontes ou
com o HEAD é escalada conforme a
[regra de conflito](../../README.md#regra-de-conflito).

## Identificação e atomicidade

O identificador é sequencial e nunca reutilizado: `WI-XXXX-slug-curto.md`.
O item entrega um resultado observável coerente, pequeno o suficiente para
review ponta a ponta e sem refatoração ou decisão independente lateral.

## Ciclo de vida

- **draft** — incompleto; não executável.
- **ready** — contexto, escopo, critérios e dependências permitem iniciar.
- **in_progress** — execução em andamento.
- **blocked** — impedimento concreto, registrado com causa; dificuldade
  comum não basta.
- **done** — critérios, validações, diff, documentação aplicável e Git foram
  verificados.
- **superseded** — substituído, preservado para rastreabilidade.

## Context Pack

Todo WI V2 contém um bloco compacto que permite retomar o trabalho sem
reconstruir contexto integral:

```text
CONTEXT PACK
Base HEAD:
Modo: FAST | STANDARD | STRICT
Objetivo:
Arquivos/áreas afetadas:
Fontes canônicas diretamente aplicáveis:
Riscos:
Dependências:
Estado/evidência de satisfação das dependências:
Testes invalidados:
Evidências anteriores ainda válidas:
```

Regras:

- a base identifica o estado contra o qual escopo e evidências foram
  avaliados;
- o modo segue os critérios de
  [workflow.md](../../development/workflow.md#modos-de-execução);
- fontes são links específicos e necessários, não listas preventivas;
- arquivos/áreas orientam a auditoria do HEAD e o delta permitido;
- riscos explicam gatilhos de modo e fronteiras relevantes;
- dependências identificam pré-requisitos, e seu estado/evidência permite
  confirmá-los na retomada sem reconstruir contexto histórico;
- testes invalidados e evidências válidas seguem
  [testing.md](../../development/testing.md#matriz-de-invalidação-de-evidências);
- nova sessão atualiza preflight e delta, não recopia o domínio.

Se o impacto real mudar, atualizar o Context Pack antes de ampliar execução,
modo, contexto ou testes.

## Conteúdo mínimo do WI V2

Um novo item contém somente:

- ID, status e fase;
- resultado observável;
- Context Pack;
- escopo e fora do escopo;
- critérios de aceite;
- decisões abertas/bloqueios;
- plano de validação;
- última evidência válida;
- findings abertos;
- Git, validação manual e encerramento.

Não copiar para o WI:

- regras permanentes do harness ou políticas gerais de Git;
- conteúdo integral de PDR, módulo ou segurança;
- catálogo global de comandos/gates;
- logs completos de todas as rodadas;
- evidência superada preservada apenas para narrar a execução.

## Resultado observável

Descreve em linguagem de produto o que o PO poderá fazer e o que continuará
fora da entrega. Detalhes técnicos pertencem aos critérios de aceite e às
fontes canônicas apontadas, sem duplicação integral.

## Escopo e fora do escopo

O item lista áreas/arquivos e tipos de mudança autorizados. Estar listado não
autoriza mudança desnecessária. Migration, dependência, template, teste ou
documentação entram apenas quando necessários ao objetivo.

Achado lateral não é implementado silenciosamente. Registre descrição,
evidência, impacto e destino provável. Se impedir execução segura, use
`blocked`; caso contrário, mantenha-o fora do delta.

## Critérios de aceite

Critérios são observáveis, verificáveis e ligados ao comportamento. Incluem
caminhos permitido/negado, objeto fora de escopo, tenant, POST manipulado e
integridade somente quando aplicáveis ao risco — não como checklist universal.
Cada checkbox exige evidência.

## Decisões abertas e bloqueios

Liste somente decisões que afetam o item. Uma decisão indispensável em aberto,
dependência não concluída, contradição canônica ou informação obrigatória
ausente bloqueia a parte afetada; o executor não inventa resposta.

## Plano de validação

O plano declara:

- teste alvo;
- suíte do app, quando comportamento mudou;
- consumidores invalidados;
- gates condicionais disparados;
- cenários manuais, quando agregarem evidência.

Seleção e validade seguem [testing.md](../../development/testing.md) e
[quality-gates.md](../../development/quality-gates.md). Não replique suas
regras no WI.

## Migrations

Migration só entra no WI quando necessária e explicitamente incluída no
escopo. A execução segue os disparadores e garantias definidos em
[quality-gates.md](../../development/quality-gates.md#gates-de-migration),
sem copiar esse procedimento para o item.

## Última evidência válida

Use uma tabela substitutiva:

| Comando/verificação | Base/delta | Resultado | Validade |
| --- | --- | --- | --- |
| ... | ... | ... | válida; ou invalidada por ... |

Mantenha a evidência mais recente ainda útil. Quando o delta a invalidar,
substitua-a pelo novo resultado ou marque claramente a pendência; não acumule
transcrições de cada rodada. Diferencie teste existente, executado, resultado
observado e validade.

## Findings e delta-review

Findings abertos registram severidade, evidência, impacto e estado. Após
correção, o pacote de delta-review contém finding, base, delta, arquivos,
evidências invalidadas e novas evidências. A política canônica de reabrir ou
não review completo está em
[workflow.md](../../development/workflow.md#correção-e-delta-review).

## Controle de escopo durante execução

Antes de escrever e antes do staging, confira:

```text
git status --short
git diff --name-status
git diff --stat
```

Com staging, confira também `git diff --cached --name-status`. Alteração
externa não compreendida exige parada; nunca use comando destrutivo para
obter working tree limpo.

## Regras de execução para agentes

Agentes seguem a sequência, os modos e as guardas canônicas de
[workflow.md](../../development/workflow.md). O WI fornece Context Pack,
escopo e evidência; não duplica o workflow.

## Git e encerramento

Registre branch, base HEAD, arquivos do escopo, última evidência válida,
validação manual, commit quando existir e estado final. Hash futuro não é
inventado.

As definições únicas de H1/H2 e quando separar commits estão em
[workflow.md](../../development/workflow.md#h1-e-h2). O WI apenas registra o
que ocorreu. Commit e push dependem da autoridade explícita da sessão.

## Atualização de current-state

`current-state.md` muda somente quando o fechamento representa estado
material novo: capacidade relevante, lacuna fechada, integração, mudança
arquitetural observável ou marco de cobertura. Ajuste cosmético e rodada de
correção não justificam atualização.

## Atualização do roadmap

`roadmap.md` muda quando fase, dependência, sequência ou possibilidade
oficial de avanço muda materialmente — não a cada WI concluído.

## Quando criar PDR ou ADR

Crie PDR para decisão duradoura de produto com alternativas relevantes e ADR
para decisão arquitetural duradoura equivalente. Detalhe local de execução
fica no WI/código; o WI apenas aponta necessidade de decisão ainda ausente.

## Encerramento

Um WI chega a `done` quando critérios possuem evidência, validações
aplicáveis estão válidas, diff e escopo foram revisados, findings/bloqueios
foram tratados, documentação material foi atualizada e o estado Git foi
registrado.

## Referências

- [Template V2](template.md)
- [Workflow](../../development/workflow.md)
- [Testes](../../development/testing.md)
- [Quality gates](../../development/quality-gates.md)
- [Procedimento Git](../../development/git-procedure.md)
