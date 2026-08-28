---
title: Quality gates
status: canonical
owner: development
last_reviewed: 2026-08-27
---

# Quality gates

## Objetivo

Definir quando cada gate é disparado. A estratégia de seleção de testes e a
validade de evidências pertencem a [testing.md](testing.md); a posição dos
gates no ciclo pertence a [workflow.md](workflow.md).

## Registro

Um gate aplicado recebe `aprovado`, `reprovado` ou `não executado`.
Registrar comando, base/delta, resultado e validade na seção **Última
evidência válida** do WI. `Aprovado` exige execução real. Gate não
aplicável pode ser omitido do plano; se foi esperado mas não executado,
registrar o motivo.

## Matriz de disparo

| Gate | Disparador | Quando dispensável |
| --- | --- | --- |
| Revisão integral do diff | Toda alteração | Nunca antes de concluir o trabalho técnico |
| `git diff --check` | Toda alteração técnica ou documental | Apenas quando não existe delta |
| Teste alvo | Comportamento testável novo/alterado ou finding corrigido | Docs puros e mudança sem comportamento automatizável, com justificativa |
| Suíte do app | STANDARD/STRICT com comportamento do app alterado, antes de H1 | FAST ou delta que não invalida comportamento do app |
| Suíte de outro app | Contrato/dependência compartilhada invalidada | Ausência de consumo afetado |
| `python manage.py check` | Mudança Django relevante (models, views, forms, urls, settings) e antes de H1 conforme modo | Docs, CSS/template puramente estático e delta Django não alterado |
| `python manage.py makemigrations --check --dry-run` | Model ou schema Django alterado | Nenhuma mudança de model/schema |
| Revisão da migration | Migration criada ou alterada | Migration sem delta |
| Aplicação/teste PostgreSQL | Migration criada ou alterada | Nenhuma migration alterada |
| Rollback/reapply | Migration de dados; migration reversível com risco de dados; risco explicitamente justificado | Schema simples já validado, sem delta posterior na migration |
| `npm run build` | Template/classes Tailwind, `static/css/input.css`, configuração ou pipeline frontend alterados | Backend/docs ou template sem impacto nas classes compiladas |
| Validação manual dirigida | Tela, rota ou fluxo observável alterado e cenário manual agrega evidência | Mudança interna ou coberta de forma suficiente sem interação de produto |
| Validação documental | Markdown criado/alterado | Nenhum documento alterado |

O modo FAST/STANDARD/STRICT define profundidade; o delta define quais gates
da tabela se aplicam. Nenhum modo converte todos os gates em universais.

## Gate de diff

Antes de concluir trabalho técnico:

```text
git status --short
git diff --name-status
git diff --stat
git diff --check
```

Com staging autorizado, conferir também `git diff --cached`. A revisão
manual verifica correção, escopo, arquivos gerados e ausência de alteração
preexistente misturada.

## Gate Django

```text
python manage.py check
```

Valida carregamento/configuração estrutural; não substitui testes nem prova
ausência de acesso ao banco. Deve rodar para mudança Django relevante e,
em STANDARD/STRICT, antes de H1 quando esse tipo de delta existir.

## Gates de migration

```text
python manage.py makemigrations --check --dry-run
```

Uma migration já aplicada ou distribuída é imutável: nunca deve ser
editada. Qualquer correção deve ser implementada por uma nova migration.

Executar quando `models.py` ou schema Django mudou. Migration nova ou
alterada exige leitura integral do arquivo, coerência com `SHARED_APPS` /
`TENANT_APPS` e aplicação/teste no PostgreSQL conforme o Work Item.

Rollback/reapply é obrigatório principalmente para migration de dados ou
quando reversibilidade e risco sobre dados existentes justificarem. Não se
repete aplicação, rollback ou teste de migration sem delta na migration,
model, configuração ou fixture relevante. Migration de schema aditiva e
simples pode exigir aplicação e teste de estado final sem a mesma cerimônia
de uma transformação de dados.

## Gate de testes

A ordem é:

```text
teste alvo
  → suíte do app
  → consumidores invalidados
  → regressão ampla, somente se justificada
```

Detalhes e matriz de impacto:
[testing.md](testing.md#matriz-de-testes-por-impacto). Segurança e
integridade exigem testes negativos e de fronteira aplicáveis.

## Gate frontend / Tailwind

`npm run build` é condicional a mudança em classes/template que participem
da compilação, CSS de entrada, configuração ou pipeline frontend. Alteração
de backend, documentação ou template sem impacto nas classes compiladas não
o dispara.

`static/css/output.css` é rastreado. Se o build o modificar, a saída deve
estar autorizada pelo escopo e ser revisada; não se inclui ruído gerado sem
relação com o item.

## Gate de validação manual dirigida

Use de 2 a 5 cenários quando uma tela, rota ou fluxo observável mudou e a
interação humana agrega evidência: caminho feliz, negação principal,
fronteira de escopo ou comportamento visual crítico. Registre cenários e
resultado no WI. Validação manual complementa, não substitui, testes
automatizados.

## Gate de documentação

Para Markdown alterado, validar conforme aplicável:

- links locais e anchors relevantes;
- newline final;
- ausência de trailing whitespace, linhas só com espaços e NUL;
- consistência entre documentos que apontam para a mesma regra.

Não há obrigação de criar ferramenta nova. Se existir script documental
oficial aplicável no HEAD, use-o.

## Ferramentas

Não tratar como obrigatórias ferramentas não configuradas no repositório,
como pytest, Ruff, Black, isort, mypy, pre-commit, tox ou CI. Sua eventual
adoção exige atualização desta fonte.

## Referências

- [Workflow](workflow.md)
- [Estratégia de testes](testing.md)
- [Procedimento de Git](git-procedure.md)
- [Comandos](commands.md)
- [Protocolo de Work Items](../delivery/work/README.md)
