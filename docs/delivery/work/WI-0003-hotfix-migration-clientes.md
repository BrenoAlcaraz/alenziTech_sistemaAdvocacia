---
title: WI-0003 — Hotfix de migration de Clientes
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# WI-0003 — Hotfix de migration de Clientes

## Estado

done

## Fase do roadmap

Fase: Fase B (hotfix sobre entrega já concluída de Clientes).

Dependência: [WI-0002](WI-0002-escopo-responsabilidade-clientes.md)
(`done`, commit `07675f7`), que introduziu a migration corrigida aqui.

## Objetivo

Corrigir `apps/clientes/migrations/0006_cliente_responsavel_obrigatorio.py`,
que falhava em `migrate_schemas` num tenant com `Cliente`s já
referenciados por outras tabelas (`OperationalError: cannot ALTER
TABLE "clientes_cliente" because it has pending trigger events`), sem
alterar o comportamento funcional ou o schema resultante já entregues
pelo WI-0002.

## Causa técnica e correção

No PostgreSQL, um `DELETE` sobre uma tabela referenciada por FK
enfileira eventos de trigger de integridade referencial dentro da
transação corrente; um `ALTER TABLE` subsequente sobre a mesma tabela,
na mesma transação, é rejeitado enquanto esses eventos estão pendentes.
A migration `0006` executa `RunPython` (remove `Cliente` sem
`responsavel`) seguido de `AlterField` (`ALTER TABLE`) na mesma
transação (`atomic` não declarado = `True`, padrão PostgreSQL do
Django). Corrigido declarando `atomic = False` na migration, com
comentário explicando a razão — as operações e a ordem permanecem
idênticas; só a atomicidade de aplicação muda.

**Lição para migrations futuras**: uma migration que combina `DELETE`
via `RunPython` com `ALTER TABLE` sobre a mesma tabela referenciada por
FK, na mesma transação, pode falhar em bancos com dados existentes,
mesmo que funcione em um schema de teste vazio.

## Evidência

Reproduzido isoladamente em schema PostgreSQL descartável: a migration
original falhou com o erro relatado quando havia `Cliente`s
referenciados por outras tabelas; a migration corrigida aplicou com
sucesso, preservando o resultado de dado (cliente sem responsável
removido, coluna obrigatória, `on_delete=PROTECT`, FKs de linhas
afetadas ajustadas para `NULL` via `on_delete=SET_NULL` já existente).

```text
python manage.py test apps.clientes --noinput → 57 testes, OK
python manage.py test apps.accounts --noinput → 86 testes, OK
python manage.py check → sem achados
python manage.py makemigrations --check --dry-run → sem alteração pendente
git diff --check → aprovado
```

Correção posteriormente validada também no ambiente externo que
originalmente revelou o defeito.

## Git e encerramento

Branch: `docs/reorganizacao-harness`.

Commit: `86cf65d` — "fix(clientes): corrigir atomicidade da migration".
Contém a correção da migration e este Work Item.

- [x] critérios de aceite com evidência (`atomic = False`; operações
  inalteradas; suítes sem regressão; reprodução isolada confirma a
  falha original e o sucesso da correção);
- [x] diff revisado e escopo respeitado (sem mudança de comportamento
  funcional);
- [x] `current-state.md`/`roadmap.md` não alterados — sem mudança de
  comportamento observável;
- [x] nenhum achado lateral.

## Referências

- [WI-0002 — Escopo e responsabilidade de Clientes](WI-0002-escopo-responsabilidade-clientes.md)
