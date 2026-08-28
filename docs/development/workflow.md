---
title: Workflow de desenvolvimento
status: canonical
owner: development
last_reviewed: 2026-08-27
---

# Workflow de desenvolvimento

## Objetivo

Este documento governa como executar trabalho: modos de risco, sequência,
review, sessões, prompts e H1/H2. O protocolo e a estrutura de Work Items
pertencem a [docs/delivery/work/README.md](../delivery/work/README.md);
seleção de testes a [testing.md](testing.md); disparo de gates a
[quality-gates.md](quality-gates.md); operações Git a
[git-procedure.md](git-procedure.md).

## Princípio central

> O Work Item delimita o trabalho; seu Context Pack carrega o contexto
> aplicável; o delta invalida somente as evidências que realmente afeta.

PDRs, ADRs e especificações canônicas governam intenção. O HEAD prova a
implementação. Nenhuma execução pode inventar requisito, resolver decisão
aberta, ampliar escopo ou reduzir garantias de autorização, IDOR, tenant,
integridade e preservação de dados.

## Modos de execução

O modo é registrado no Context Pack antes da escrita e sobe de nível sempre
que o impacto real superar o inicialmente previsto.

| Modo | Critérios objetivos | Contexto | Testes e gates | Review |
| --- | --- | --- | --- | --- |
| **FAST** | Documentação, copy, alteração visual localizada ou CSS determinístico, sem mudança de contrato, backend, segurança, dados ou dependência compartilhada | WI/Context Pack, arquivos afetados e fonte específica da regra | Validação diretamente invalidada; gates condicionais aplicáveis; sempre revisar o diff e executar `git diff --check` | Self-review normalmente suficiente |
| **STANDARD** | Form, view, endpoint, serviço de módulo, regra de negócio comum ou model aditivo sem transformação sensível; não contém gatilho STRICT | FAST mais módulo/contratos diretamente consumidos | Teste alvo durante a execução; suíte do app antes de H1 quando seu comportamento mudou; gates pelo delta | Review independente normal |
| **STRICT** | Autorização; IDOR/escopo; tenant/cross-tenant; migration de dados; constraint sobre dados existentes; operação destrutiva; financeiro ou integridade sensível; kernel compartilhado; mudança arquitetural relevante | STANDARD mais fontes especializadas de segurança/arquitetura/PDR e dependências afetadas | Testes negativos e de fronteira; suíte do app e consumidores invalidados; PostgreSQL/migration quando aplicável; regressão ampla final quando o risco justificar | Review adversarial independente |

Model aditivo com migration de schema pode permanecer STANDARD se não
transformar dados existentes, não introduzir constraint arriscada e não tocar
segurança. O modo não é inferido pelo tamanho do diff.

## Sequência operacional

### 1. Preflight

Antes de escrever, registrar branch, HEAD e `git status`; upstream somente
quando relevante. Alteração externa não compreendida exige parada, sem reset,
limpeza ou sobrescrita.

### 2. Contextualizar pelo impacto

Ler integralmente o WI/Context Pack e os arquivos diretamente afetados.
Abrir apenas as fontes sob demanda indicadas pelo risco. Reconfirmar no HEAD
as premissas que podem ter mudado desde a base registrada.

Se o item consumir permissão, configuração, preferência, feature flag ou
mecanismo semelhante, verificar como ele é administrado no estado atual.
Não presumir UI, rota, Admin ou integração.

### 3. Confirmar execução

Validar modo, escopo, dependências, decisões abertas e comportamento
observável. Uma contradição indispensável ou informação obrigatória ausente
torna o WI `blocked`; dificuldade técnica comum não.

### 4. Implementar o menor delta coerente

Não incluir refatoração oportunista, nova dependência, mudança de schema,
renomeação ou documentação lateral sem relação necessária com os critérios
de aceite.

### 5. Testar incrementalmente

Executar teste alvo durante a implementação. Antes de H1, ampliar somente
para as suítes invalidadas pelo delta, conforme [testing.md](testing.md).
Uma nova sessão não invalida evidência por si só.

### 6. Aplicar gates

Executar apenas os gates cujos disparadores estão presentes no delta,
conforme [quality-gates.md](quality-gates.md). Gate não aplicável não é
falha; gate declarado aprovado exige execução real.

### 7. Revisar

Revisar técnica e integralmente o diff produzido, seu escopo e cada critério
de aceite. Aplicar a profundidade de review definida pelo modo e a política
de delta-review abaixo.

### 8. Registrar a última evidência válida

Atualizar o WI substituindo evidência superada, sem acumular logs completos
de rodadas. Registrar comando, base/delta, resultado e validade.

### 9. Encerrar e operar Git

Atualizar somente a documentação materialmente afetada. Staging, commit e
push dependem da autoridade explícita da sessão. O relatório final informa
arquivos, evidências, findings, Git e ações não executadas.

## Review baseado em risco

### Self-review

Padrão de FAST. Confirma escopo, diff integral, critérios e validações
diretamente afetadas. Review independente ainda pode ser solicitado por
incerteza concreta ou impacto não previsto.

### Review independente normal

Padrão de STANDARD. O reviewer verifica o contrato do WI, o diff, os testes
afetados e efeitos colaterais plausíveis. Não precisa reconstruir fontes ou
reexecutar evidências que o delta não invalidou.

### Review adversarial independente

Obrigatório em STRICT. Procura caminhos de negação, bypass, IDOR, vazamento
de tenant, corrupção/perda de dados, falhas de constraint e incompatibilidade
de contratos compartilhados. A profundidade é dirigida pelo risco, não por
uma lista universal de suítes.

## Correção e delta-review

Após um finding corrigido, **delta-review é o padrão**. O reviewer recebe:

- finding e base da revisão;
- delta desde a revisão anterior;
- arquivos tocados;
- evidências invalidadas;
- novas evidências.

O review completo só reabre quando a correção muda arquitetura ou contrato,
toca autorização/queryset, altera migration/constraint, adiciona dependência,
extrapola o finding ou revela problema estrutural. Caso contrário, o reviewer
valida a correção, regressões plausíveis no delta e a atualização da
evidência.

## Evidência entre sessões

Cada sessão faz preflight próprio, mas reutiliza o Context Pack e a última
evidência válida. Resultados anteriores permanecem válidos conforme a
[matriz de invalidação](testing.md#matriz-de-invalidação-de-evidências).
Independência de reviewer não significa repetir toda contextualização ou
regressão.

## H1 e H2

Esta é a definição canônica:

- **H1** — commit de implementação técnica aprovada.
- **H2** — commit posterior de fechamento documental, usado quando
  materialmente necessário, especialmente se havia validação manual
  pendente.

FAST pode usar um único commit quando implementação e documentação já estão
finais. STANDARD e STRICT usam H1/H2 somente quando existe motivo real para
separar implementação e fechamento. Um H2 apenas documental não invalida
automaticamente testes de código. Não se cria terceiro commit para registrar
o hash do próprio H2.

Commit e push nunca são implícitos: dependem da autoridade da sessão.

## Prompts operacionais

Prompts informam somente:

- papel;
- WI/Context Pack;
- base, quando necessária;
- objetivo ou delta;
- autoridade da sessão (read/write/commit/push);
- exceção específica.

Não copiam PDR, workflow, regras permanentes, contexto amplo de produto nem
dezenas de gates. Como orientação, implementação costuma caber em 5–15
linhas, review em 10–20, correção/delta em 5–12 e H1 em uma instrução
operacional curta. Esses intervalos não são limites rígidos.

## Falhas e achados fora do escopo

Falha relevante causada pelo delta impede conclusão. Falha preexistente ou
ambiental só pode ser classificada assim com evidência. Teste não é apagado
ou desabilitado para obter verde fora do escopo autorizado.

Achado lateral é registrado com evidência, impacto e destino provável; não
é implementado silenciosamente. Ele bloqueia apenas quando impede execução
segura do objetivo atual.

## Estados do Work Item

O workflow usa os seis estados definidos no
[protocolo](../delivery/work/README.md#ciclo-de-vida): `draft`, `ready`,
`in_progress`, `blocked`, `done` e `superseded`.

## Referências

- [Protocolo de Work Items](../delivery/work/README.md)
- [Estratégia de testes](testing.md)
- [Quality gates](quality-gates.md)
- [Procedimento de Git](git-procedure.md)
