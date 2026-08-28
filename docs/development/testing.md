---
title: Estratégia e comandos de testes
status: canonical
owner: development
last_reviewed: 2026-08-27
---

# Estratégia e comandos de testes

## Objetivo

Definir como selecionar testes por dependência e quando uma evidência
anterior continua válida. Os disparadores de comandos que não são testes
pertencem a [quality-gates.md](quality-gates.md).

## Runner e ambiente

O projeto usa o test runner padrão do Django:

```text
python manage.py test <label>
```

Os testes baseados em `TenantTestCase` dependem de PostgreSQL e criam
schemas reais. Não há runner obrigatório de pytest, tox ou coverage
configurado no repositório.

Labels podem apontar para método, classe, módulo, app ou suíte completa:

```text
python manage.py test apps.processos.tests.test_exemplo.Classe.test_caso
python manage.py test apps.processos.tests.test_exemplo
python manage.py test apps.processos
python manage.py test
```

## Camadas de execução

### Teste alvo

Executado durante implementação e correção. Cobre diretamente o comportamento
ou finding alterado e fornece feedback rápido.

### Suíte do app

Executada antes de H1 em STANDARD ou STRICT quando o comportamento do app
mudou. Não é automática para documentação ou delta que não afeta o app.

### Suítes de outros apps

Executadas somente quando o delta invalida contrato ou dependência
compartilhada consumida por esses apps, ou quando regressão ampla final foi
explicitamente justificada. Mudança exclusiva em `apps.processos` não
implica, por si só, executar `apps.accounts` e `apps.clientes` completos.

### Suíte completa

Reservada para mudança transversal, configuração/test runner, kernel
compartilhado, risco STRICT que atravesse módulos ou regressão final
explicitamente necessária. Não é um ritual de toda sessão.

## Matriz de testes por impacto

| Delta | Testes imediatos | Antes de H1 | Normalmente não exige |
| --- | --- | --- | --- |
| Documentação | Validação documental | Nenhum teste de código | Suítes Django, PostgreSQL, migration, frontend |
| Template sem classe/contrato frontend novo | Teste de view/template afetado, se houver comportamento | Suíte do app apenas se comportamento do app mudou | Apps não consumidores, migration |
| Template, CSS, classe Tailwind ou configuração frontend | Teste alvo visual/HTTP quando existente | Suíte do app se fluxo mudou; build conforme gate | Migration e apps não consumidores |
| Form, view, endpoint ou serviço de módulo | Teste alvo permitido/negado conforme risco | Suíte do app | Suítes de outros apps sem contrato invalidado |
| Model aditivo | Testes do model e comportamento consumidor | Suíte do app; teste de migration criada | Apps não consumidores |
| Autorização, IDOR ou escopo | Positivo, negado, objeto fora de escopo e ausência de mutação indevida | Suíte do app e consumidores efetivamente invalidados | Apps sem dependência |
| Accounts/kernel compartilhado | Teste alvo do contrato do kernel | `apps.accounts` e consumidores do contrato alterado | Apps que não usam o contrato |
| Cliente/API consumida | Teste alvo do contrato alterado | Produtor e consumidores identificados | Módulos sem consumo |
| Migration de schema | Teste do estado migrado e comportamento do model | Suíte do app; aplicação em PostgreSQL | Frontend e apps não consumidores |
| Migration de dados | Casos de dados existentes, nulos, duplicados e fronteiras relevantes | Aplicação e, se reversível/arriscada, rollback/reapply; suíte do app | Repetição sem delta na migration |
| Configuração ou test runner | Teste mínimo que prove carregamento | Suítes afetadas, possivelmente completa | Reuso automático de evidência obtida sob configuração anterior |

Testes negativos são obrigatórios quando segurança ou integridade estiverem
envolvidas. A matriz não substitui análise de dependências reais.

## Princípio de validade

> Evidência continua válida se o delta não alterou arquivo, contrato,
> configuração ou dependência relevante para aquela evidência.

Troca de sessão, passagem de executor para reviewer, atualização documental
ou novo prompt não invalidam evidência por si sós. A última evidência válida
fica registrada no WI com comando, base/delta, resultado e validade.

## Matriz de invalidação de evidências

| Alteração desde a evidência | Evidência que permanece válida | Evidência invalidada e ação |
| --- | --- | --- |
| Somente docs | Todos os testes/gates de código anteriores | Links, formatação e consistência dos docs alterados |
| Template sem nova classe Tailwind | Migration e testes de model não relacionados | Teste/inspeção do fluxo renderizado; suíte do app somente se comportamento mudou |
| Template, classe Tailwind, CSS ou config frontend | Testes backend sem dependência visual | Build e validação visual/HTTP aplicável |
| Form/view/endpoint/serviço | Migration e apps sem consumo | Teste alvo; suíte do app antes de H1 |
| Model/schema Django | Frontend sem dependência e apps não consumidores | Testes do model/consumidores, suíte do app, `makemigrations --check`; migration se criada |
| Autorização/queryset/escopo | Evidências puramente visuais ou de schema não relacionado | Testes permitido/negado/IDOR e consumidores do contrato |
| Accounts/kernel compartilhado | Apps comprovadamente sem uso do contrato | Kernel e cada consumidor identificado; regressão ampla se alcance não puder ser delimitado |
| Cliente/API consumida | Áreas sem importação, chamada ou contrato com o produtor | Produtor e consumidores do contrato alterado |
| Migration criada ou alterada | Build/frontend e testes sem dependência do schema | Revisão/aplicação PostgreSQL e teste de migration; rollback/reapply conforme risco |
| Migration de dados alterada | Evidências não relacionadas a dados/schema | Casos representativos, preservação, idempotência quando aplicável e rollback/reapply se suportado/relevante |
| Teste alterado | Evidências de produção não cobertas pelo teste | Reexecutar o label alterado; ampliar se fixture/helper compartilhado mudou |
| Configuração, settings ou test runner | Evidências totalmente independentes da configuração, se demonstrável | Reexecutar suítes que dependem do ambiente/configuração alterada |

### Regras de aplicação

1. Comparar o delta com a base da evidência.
2. Identificar arquivos, contratos, fixtures, configurações e consumidores
   alcançados.
3. Marcar no Context Pack o que foi invalidado e o que permanece válido.
4. Executar somente a camada necessária para renovar evidência.
5. Se o alcance não puder ser delimitado com confiança, ampliar a regressão
   e registrar o motivo.

Correção de teste ou fixture compartilhada pode invalidar mais evidências que
uma correção de produção localizada. Resultado anterior não é reutilizado se
o comando falhou, foi interrompido, usou base desconhecida ou configuração
diferente relevante.

## Interpretação de resultados

Distinguir sempre:

- **existe** — o teste está no código;
- **executado** — o comando rodou na base/delta informado;
- **passou/falhou** — resultado observado pelo runner;
- **válido** — o delta posterior não alcançou sua dependência;
- **não executado** — nenhuma conclusão sobre resultado.

Falha relevante causada pelo delta impede conclusão. Falha preexistente ou
ambiental exige evidência comparável; comentário histórico não basta.

## Referências

- [Workflow](workflow.md)
- [Quality gates](quality-gates.md)
- [Comandos](commands.md)
- [Protocolo de Work Items](../delivery/work/README.md)
