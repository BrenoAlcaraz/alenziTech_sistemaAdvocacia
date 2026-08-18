---
title: WI-0003 — Hotfix de migration de Clientes
status: canonical
owner: delivery
last_reviewed: 2026-08-18
---

# WI-0003 — Hotfix de migration de Clientes

## Estado

in_progress

## Fase do roadmap

Fase: Fase B — Aplicar escopo de dados (hotfix sobre entrega já
concluída de Clientes).

Objetivo relacionado: nenhum objetivo novo de fase — este item corrige
um defeito de aplicação (`migrate_schemas`) descoberto durante
validação do [WI-0002](WI-0002-escopo-responsabilidade-clientes.md) em
outro ambiente, sem alterar o comportamento funcional já entregue.

Dependência: [WI-0002](WI-0002-escopo-responsabilidade-clientes.md)
(`done`, commit `07675f7`), que introduziu a migration
`apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`.

## Objetivo

Garantir que
`apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
possa ser aplicada por `python manage.py migrate_schemas` em um tenant
que já possui `Cliente`s (e tabelas de outros apps referenciando
`Cliente`) sem falhar com
`django.db.utils.OperationalError: cannot ALTER TABLE
"clientes_cliente" because it has pending trigger events`, preservando
integralmente o comportamento funcional e o schema resultante já
entregues pelo WI-0002.

## Resultado observável pelo Product Owner

### Ao concluir este WI

- Um tenant existente, com clientes cadastrados e com registros em
  Processos/Tarefas/Agenda/Financeiro vinculados a esses clientes,
  consegue receber a atualização de schema (`migrate_schemas`) sem erro
  de banco, incluindo a migration que tornou `Cliente.responsavel`
  obrigatório.

### Ainda não estará coberto

- Nenhuma mudança de regra de negócio de Clientes, Processos, Tarefas,
  Agenda ou Financeiro.
- Nenhuma alteração em dado real de qualquer schema/tenant existente.

## Contexto e motivação

Durante validação do WI-0002 em outro ambiente (fora deste
repositório), a aplicação de `python manage.py migrate_schemas` em um
tenant que já possuía `Cliente`s falhou com:

```text
django.db.utils.OperationalError: cannot ALTER TABLE
"clientes_cliente" because it has pending trigger events
```

A migration `0006_cliente_responsavel_obrigatorio.py` executa, na
mesma migration (portanto na mesma transação, já que
`atomic` não estava declarado e o padrão do Django para PostgreSQL é
`True`):

1. `RunPython` (`remover_clientes_sem_responsavel`) — `DELETE` via ORM
   sobre `Cliente` com `responsavel IS NULL`;
2. `AlterField` — `ALTER TABLE` sobre `clientes_cliente.responsavel`
   (torna a coluna `NOT NULL` e recria a constraint de FK com
   `on_delete=PROTECT`).

Este é um item de hotfix, não uma nova unidade de produto — não
implementa Processos, não altera dado, não usa `--fake`, não reseta
migrations.

## Evidência do estado atual

Reconfirmada por leitura direta do HEAD (commit `5ca5d75`) nesta
execução:

- **Migration auditada**:
  `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
  não declara `atomic` na classe `Migration` — usa o padrão do Django
  (`atomic = True` para backends que suportam DDL transacional, como
  PostgreSQL). As duas operações (`RunPython` + `AlterField`) portanto
  executam na mesma transação de banco.
- **Tabelas que referenciam `Cliente` via FK** (confirmado por busca
  `ForeignKey(Cliente` em todo o repositório):
  - `apps/processos/models.py:54` — `Processo.cliente`
    (`on_delete=SET_NULL`), migration `apps/processos/migrations/0001_initial.py`
    (depende apenas de `clientes.0001_initial`).
  - `apps/tarefas/models.py:27` — `Tarefa.cliente`
    (`on_delete=SET_NULL`), migration
    `apps/tarefas/migrations/0002_tarefa_cliente.py` (depende de
    `clientes.0002_cliente_ativo`).
  - `apps/agenda/models.py:36` — `Compromisso.cliente`
    (`on_delete=SET_NULL`), migration
    `apps/agenda/migrations/0002_compromisso_cliente_compromisso_dia_inteiro_and_more.py`
    (depende de `clientes.0002_cliente_ativo`).
  - `apps/financeiro/models.py:53,86` — `LancamentoFinanceiro.cliente` e
    `CustaJudicial.cliente` (`on_delete=SET_NULL`), migration
    `apps/financeiro/migrations/0001_initial.py` (depende de
    `clientes.0001_initial`).
  - Nenhuma dessas quatro migrations depende de `clientes.0006` —
    portanto, em qualquer tenant que já tenha essas quatro migrations
    aplicadas antes de `0006` (o caso de um tenant existente, migrado
    incrementalmente), as constraints de FK para `clientes_cliente` já
    existem no banco no momento em que `0006` roda.
- **Causa técnica confirmada**: no PostgreSQL, um `DELETE` sobre uma
  tabela referenciada por FK enfileira eventos de trigger (verificação
  de integridade referencial) sobre essa tabela dentro da transação
  corrente. Um `ALTER TABLE` subsequente sobre a mesma tabela, dentro
  da mesma transação, com eventos de trigger ainda pendentes, é
  rejeitado pelo PostgreSQL com exatamente o erro relatado. Isso só se
  manifesta quando (a) já existem linhas em `Cliente` referenciadas por
  outras tabelas no momento do `DELETE`, e (b) `RunPython` (DML) e
  `AlterField` (DDL) ocorrem na mesma transação — ambas as condições
  descritas no relato e confirmadas na leitura do código.
- **Reprodução**: reproduzida de forma isolada nesta execução, em
  schema PostgreSQL descartável (não um tenant real) — ver "Validações
  executadas" abaixo.
- **`current-state.md`**: registra a migration `0006` apenas como
  "migration de dados... que remove, de forma reproduzível, qualquer
  `Cliente` remanescente com `responsavel IS NULL`" — não menciona
  `atomic`/transação, portanto não há divergência a resolver, apenas
  uma lacuna de comportamento de aplicação não coberta antes deste
  hotfix.

## Resultado esperado

- `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
  declara `atomic = False` na classe `Migration`, com um comentário
  curto explicando a razão (pending trigger events).
- As operações e a semântica funcional da migration permanecem
  idênticas: mesma remoção de `Cliente` com `responsavel IS NULL`,
  mesma alteração de campo para obrigatório com
  `on_delete=PROTECT`. Nenhuma reordenação, divisão ou remoção de
  operação.
- `migrate_schemas` aplica `0006` com sucesso em um schema que já
  possui `Cliente`s e tabelas de outros apps referenciando `Cliente`,
  sem o erro de pending trigger events.
- Nenhuma mudança de comportamento funcional de Clientes, Processos,
  Tarefas, Agenda ou Financeiro.

## Fontes canônicas

- [docs/delivery/work/WI-0002-escopo-responsabilidade-clientes.md](WI-0002-escopo-responsabilidade-clientes.md)
- [docs/delivery/work/README.md](README.md#migrations)
- [docs/development/testing.md](../../development/testing.md)
- [docs/development/quality-gates.md](../../development/quality-gates.md)
- [docs/development/commands.md](../../development/commands.md#banco--multitenancy)

## Arquivos do HEAD a auditar antes da implementação

- `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
- `apps/clientes/models.py`
- `apps/processos/models.py`, `apps/tarefas/models.py`,
  `apps/agenda/models.py`, `apps/financeiro/models.py` (FKs para
  `Cliente`)
- `apps/clientes/tests/test_escopo.py`,
  `apps/clientes/tests/test_autorizacao.py`

## Escopo permitido

### Pode alterar

- `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
  (apenas adicionar `atomic = False` e um comentário curto).

### Pode criar

- Este próprio Work Item
  (`docs/delivery/work/WI-0003-hotfix-migration-clientes.md`).

### Migrations

- Nenhuma migration nova é criada — o schema-alvo (models) não muda.
- A migration `0006` existente é ajustada apenas em seu atributo de
  execução (`atomic`), não em suas operações.

### Documentação

- Este Work Item, incluindo sua seção de evidência de execução e
  encerramento.
- `current-state.md`/`roadmap.md` — apenas se a execução revelar
  necessidade material de atualização (ver "Atualização de
  current-state" abaixo); não esperado a priori, pois este hotfix não
  muda comportamento funcional observável.

## Fora de escopo

> qualquer alteração útil, mas não necessária para satisfazer os
> critérios deste item, permanece fora do escopo até ser explicitamente
> incorporada.

- Qualquer alteração de comportamento funcional de Clientes.
- Implementação de Processos ou de qualquer outro módulo.
- `--fake`, alteração manual de dados, reset de migrations, remoção de
  schemas.
- Dividir ou reordenar migrations existentes sem necessidade técnica
  concreta (não identificada nesta auditoria).

## Regras funcionais e técnicas

- A correção é estritamente de aplicação de migration (`atomic`), não
  de regra de negócio.
- A remoção de `Cliente`s com `responsavel IS NULL` continua sendo a
  mesma operação de dado, com o mesmo efeito final sobre o schema.

## Segurança e autorização

Não aplicável — este item não altera autorização, escopo de dados ou
qualquer view. É um hotfix de infraestrutura de aplicação de schema.

## Decisões abertas e bloqueios

Nenhuma `OPEN-XXX` afeta este item.

## Dependências

[WI-0002](WI-0002-escopo-responsabilidade-clientes.md) (`done`), que
introduziu a migration corrigida por este item.

## Critérios de aceite

- [x] `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
      declara `atomic = False`, com comentário explicando a razão.
- [x] As operações da migration (`RunPython` + `AlterField`) permanecem
      inalteradas em conteúdo e ordem.
- [x] `python manage.py test apps.clientes --noinput` e
      `python manage.py test apps.accounts --noinput` passam sem
      regressão.
- [x] `python manage.py check` sem erro.
- [x] `python manage.py makemigrations --check --dry-run` sem
      alteração pendente.
- [x] Reprodução isolada (schema descartável, não um tenant real)
      confirma: (a) a migration original falha com o erro relatado
      quando há `Cliente`s referenciados por outras tabelas; (b) a
      migration corrigida (`atomic = False`) aplica com sucesso o
      mesmo cenário, preservando o resultado de dado esperado (cliente
      sem responsável removido, demais preservados, coluna obrigatória).

## Testes esperados

### Existentes a considerar

- `apps/clientes/tests/test_autorizacao.py` (26 testes, WI-0001)
- `apps/clientes/tests/test_escopo.py` (31 testes, WI-0002)
- `apps/accounts/tests/` (regressão do kernel, consumido por Clientes)

### Novos testes

Nenhum teste automatizado novo de aplicação — a suíte de
`apps.clientes`/`apps.accounts` não exercita `migrate_schemas` (usa
`TenantTestCase`, que cria o schema de teste já na migration mais
recente, sem reproduzir o cenário de tenant pré-existente). A
verificação desta correção é feita pela reprodução isolada descrita em
"Validação manual" abaixo, não por um `TestCase` novo.

### Comandos de validação

```text
python manage.py test apps.clientes --noinput
python manage.py test apps.accounts --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

### Validação manual

Aplicável: SIM

Cenários previstos (2 a 5, quando aplicável):

- Aplicar a migration original (sem `atomic = False`) em um schema
  descartável com `Cliente`s referenciados por Processos/Tarefas/
  Agenda/Financeiro e confirmar a falha relatada.
- Reverter o schema ao estado anterior a `0006`, aplicar a correção e
  reaplicar `0006`, confirmando sucesso.
- Confirmar o resultado de dado após a migration corrigida: cliente
  sem responsável removido, cliente com responsável preservado, coluna
  `responsavel` obrigatória (`NOT NULL`).

Resultado real (preencher durante a execução, não antes):

- Reproduzido em schema PostgreSQL descartável
  (`wi0003_hotfix_validation`, criado e destruído nesta execução — não
  um tenant real, sem `Escritorio`/`Dominio` associado): com a migration
  original (sem `atomic = False`), a aplicação de `clientes.0006` sobre
  um schema com um `Cliente` sem responsável referenciado por
  `Processo`, `Tarefa`, `Compromisso`, `LancamentoFinanceiro` e
  `CustaJudicial` falhou com `django.db.utils.OperationalError: ERRO:
  não é possível executar ALTER TABLE "clientes_cliente", porque tem
  eventos de gatilho pendentes` — a mesma mensagem relatada (em
  português, mesmo texto de "pending trigger events"). A transação
  reverteu integralmente (2 `Cliente`s preservados, coluna ainda
  aceitando nulo, `0006` não registrada como aplicada).
- Com a correção (`atomic = False`) aplicada, a mesma migration sobre o
  mesmo schema (revertido a `0005` antes de reaplicar) teve sucesso:
  `Cliente` sem responsável removido; `Cliente` com responsável
  preservado; coluna `responsavel_id` alterada para `NOT NULL`;
  `Processo.cliente_id`, `Tarefa.cliente_id`, `Compromisso.cliente_id`,
  `LancamentoFinanceiro.cliente_id` e `CustaJudicial.cliente_id` das
  linhas que referenciavam o cliente removido corretamente ajustados
  para `NULL` (`on_delete=SET_NULL`, comportamento já existente,
  preservado). Schema descartável removido por completo
  (`DROP SCHEMA ... CASCADE`) ao final; apenas o schema real
  `demo` permaneceu no banco, nunca tocado por esta execução.

## Quality gates

- [x] testes alvo executados
- [ ] testes negativos executados, quando aplicável — não aplicável
      (hotfix de infraestrutura de migration, sem regra de autorização
      nova)
- [x] suíte relevante executada (`apps.clientes`, `apps.accounts`)
- [x] `git diff --check`
- [x] diff revisado integralmente
- [x] links e documentação referenciados verificados

## Atualizações documentais esperadas

Nenhuma atualização de `current-state.md`/`roadmap.md` é esperada a
priori — este hotfix não altera comportamento funcional observável,
apenas a robustez de aplicação de uma migration já registrada. Caso a
execução revele necessidade de registro adicional, será declarado em
"Achados fora do escopo" abaixo.

## Achados fora do escopo

Nenhum registrado.

## Evidência de execução

### Estado inicial

Branch: `docs/reorganizacao-harness`
HEAD: `5ca5d75` — "docs: encerrar WI-0002 de escopo de clientes"
Git status: limpo (`nothing to commit, working tree clean`)

### Arquivos alterados

- `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`
  (`atomic = False` + comentário; operações inalteradas).
- `docs/delivery/work/WI-0003-hotfix-migration-clientes.md` (novo,
  este arquivo).

### Testes executados

| Comando | Executado? | Resultado |
| --- | --- | --- |
| `python manage.py test apps.clientes --noinput` | sim | `OK` — 57 testes |
| `python manage.py test apps.accounts --noinput` | sim | `OK` — 86 testes |

### Validações executadas

| Gate | Comando | Executado? | Resultado |
| --- | --- | --- | --- |
| Django check | `python manage.py check` | sim | "System check identified no issues (0 silenced)." |
| Consistência de migrations | `python manage.py makemigrations --check --dry-run` | sim | "No changes detected", exit 0 |
| Formatação de diff | `git diff --check` | sim | sem saída, exit 0 |
| Reprodução isolada (migration original) | `migrate_schemas -s wi0003_hotfix_validation clientes 0006` (schema descartável, com dados existentes) | sim | falhou com `OperationalError`, mensagem "pending trigger events", igual ao relato — ver "Validação manual" |
| Reprodução isolada (migration corrigida) | mesmo comando, após `atomic = False` | sim | aplicada com sucesso, dado final íntegro — ver "Validação manual" |

### Resultado

Causa técnica confirmada e corrigida. `clientes.0006` aplica-se com
sucesso via `migrate_schemas` em um schema com `Cliente`s já
referenciados por outras tabelas, sem o erro de pending trigger
events, preservando o mesmo resultado de dado (remoção do cliente sem
responsável, campo obrigatório, `on_delete=PROTECT`) e sem alterar
nenhum comportamento funcional de Clientes ou de qualquer outro
módulo. Suítes de `apps.clientes` (57 testes) e `apps.accounts` (86
testes) permanecem `OK`, sem regressão.

### Commit

Nenhum. Não autorizado para esta execução — arquivos deixados em stage
para revisão.

## Encerramento

- [x] critérios de aceite verificados;
- [x] testes/validações registrados;
- [x] diff revisado;
- [x] escopo respeitado;
- [ ] current-state atualizado quando aplicável — não aplicável (sem
      mudança de comportamento funcional observável);
- [ ] roadmap atualizado somente se necessário — não necessário;
- [x] achados laterais registrados — nenhum encontrado;
- [x] Git final registrado — commit ainda não existe (não autorizado
      nesta execução); branch, HEAD inicial, arquivos alterados e
      estado de staging registrados acima.

Este Work Item permanece `in_progress`: a implementação, os testes e
as validações estão concluídos e prontos para revisão, mas o estado
`done` depende de evidência de Git (commit) ainda não autorizada nesta
execução, conforme
[README.md#ciclo-de-vida](README.md#ciclo-de-vida).
