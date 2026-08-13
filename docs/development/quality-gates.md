---
title: Quality gates
status: canonical
owner: development
last_reviewed: 2026-08-06
---

# Quality gates

## Objetivo

Definir os critérios de validação que uma execução de trabalho neste
repositório deve satisfazer antes de considerar um Work Item concluído,
distinguindo o que é **obrigatório para toda implementação** do que é
**condicional** ao tipo de alteração feita. Este documento não introduz
nenhuma ferramenta de qualidade além das já constatadas no HEAD do
repositório — ver "Ferramentas não estabelecidas" abaixo.

Este documento complementa, sem duplicar:

- [workflow.md](workflow.md) — onde os quality gates entram na
  sequência operacional (Etapa 9);
- [testing.md](testing.md) — estratégia e comandos de teste;
- [git-procedure.md](git-procedure.md) — verificações de Git antes de
  staging e commit;
- [commands.md](commands.md) — catálogo factual de todos os comandos
  disponíveis no projeto.

## Resultado de um gate

Todo gate aplicado a uma execução recebe exatamente um destes três
resultados:

```text
aprovado
reprovado
não executado
```

- **aprovado** — o gate foi executado e não revelou problema.
- **reprovado** — o gate foi executado e revelou um problema não
  resolvido.
- **não executado** — o gate não foi rodado nesta execução; o motivo
  deve ser registrado (por exemplo, "fora do escopo do item", "ambiente
  sem PostgreSQL configurado").

Não é permitido registrar "aprovado" por inferência, sem execução real
do gate. O resultado de cada gate deve registrar, no mínimo:

```text
comando
executado? (sim/não)
resultado
```

Escrever apenas "OK" não é um registro válido.

## Gates obrigatórios para toda implementação

Aplicam-se a qualquer alteração de código, independentemente do módulo
tocado:

```text
git status --short
git diff --name-status
git diff --stat
git diff --check
```

mais:

- revisão manual do diff completo (técnica e de escopo, conforme
  [workflow.md#etapa-10--revisar-o-diff](workflow.md#etapa-10--revisar-o-diff));
- verificação de cada critério de aceite do Work Item contra evidência
  real;
- os testes alvo/relevantes do Work Item, conforme
  [testing.md](testing.md) — ver "Gate de testes" abaixo.

Nenhum gate obrigatório desta lista exige acesso a PostgreSQL, exceto os
testes, quando o Work Item os exigir.

## Gates condicionais

Aplicam-se apenas quando o tipo de alteração os torna relevantes. Um
Work Item não precisa rodar todos os gates condicionais existentes —
apenas os que sua alteração real justifica:

- `python manage.py check` — quando a alteração toca código Django
  (models, views, forms, settings, urls); ver "Gate Django" abaixo;
- `python manage.py makemigrations --check --dry-run` — quando a
  alteração toca `models.py` de algum app; ver "Gate de migrations"
  abaixo;
- teste alvo do item — sempre que o item adicionar ou alterar
  comportamento testável;
- suíte do app tocado — regressão mínima quando o item altera um app
  com testes existentes ou novos;
- regressão de módulo dependente — quando o item altera um
  comportamento consumido por outro módulo (por exemplo, o kernel de
  `apps.accounts`, consumido por views operacionais);
- suíte mais ampla do projeto — apenas quando o item toca mais de um
  app, ou altera comportamento compartilhado;
- migrations — revisão explícita do arquivo de migration gerado, quando
  o item as autorizar;
- `npm run build` (Tailwind) — quando a alteração afeta classes
  compiladas; ver "Gate frontend / Tailwind" abaixo;
- documentação — quando `.md` for alterado; ver "Gate de documentação"
  abaixo.

Uma alteração trivial que não exige suíte completa não deve ser forçada
a rodá-la só porque ela existe — a suíte mais ampla é exigida apenas
quando o próprio Work Item ou o risco real da mudança a justificar.

## Gate Django

```text
python manage.py check
```

Constatado como comando de validação estrutural do projeto (ver
[commands.md#django](commands.md#django)) — verifica a configuração e os
models do projeto, sem aplicar migrations.

Este gate:

- é relevante para qualquer alteração que toque models, views, forms,
  settings ou urls de algum app Django;
- **não substitui testes** — passar em `check` não prova que o
  comportamento está correto, apenas que a configuração e os models são
  estruturalmente válidos;
- **não garante ausência absoluta de acesso ao banco** — esse
  comportamento não deve ser presumido sem instrumentação própria da
  chamada, conforme já registrado em
  [commands.md#django](commands.md#django).

## Gate de migrations

```text
python manage.py makemigrations --check --dry-run
```

O suporte a essas flags pode ser reconfirmado a qualquer momento com
`python manage.py help makemigrations`. Na versão do Django usada por
este projeto, `--check` é documentado como: "Exit with a non-zero
status if model changes are missing migrations and don't actually
write them. Implies --dry-run."

Este gate:

- é um gate de **consistência de migrations** — detecta quando um model
  foi alterado sem que a migration correspondente exista;
- **não substitui revisão de migrations** — quando uma migration nova
  fizer parte do escopo de um Work Item, o arquivo gerado precisa ser
  lido e revisado explicitamente antes de ser aceito;
- **não aplica migrations** — nem `--check`, nem `--dry-run` escrevem
  arquivo ou tocam o banco;
- depende do ambiente conseguir carregar o projeto (configuração válida,
  dependências instaladas).

Para este projeto, baseado em django-tenants (schema-per-tenant), este
documento **não define** um comando universal de aplicação de
migrations como quality gate — a aplicação de migrations depende do
Work Item específico e dos comandos catalogados em
[commands.md#banco--multitenancy](commands.md#banco--multitenancy)
(`migrate_schemas --shared`, `migrate_schemas`), nunca de um gate
genérico.

## Gate de testes

Sequência conceitual, alinhada a
[testing.md#estratégia-por-work-item](testing.md#estratégia-por-work-item):

```text
teste alvo
  → suíte do app
  → regressão de módulo dependente
  → suíte mais ampla, quando necessária
```

- **teste alvo** — o(s) teste(s) novo(s) ou alterado(s) diretamente
  ligados aos critérios de aceite do item;
- **suíte do app** — todos os testes do app tocado, como regressão
  mínima;
- **regressão relevante** — a suíte de qualquer outro app que consuma o
  comportamento alterado (por exemplo, alterar
  `apps/accounts/permissoes.py` exige rodar `apps.accounts` e qualquer
  módulo operacional que já o consulte);
- **suíte mais ampla** — apenas quando o item tocar mais de um app, ou
  alterar comportamento compartilhado por vários módulos.

Uma alteração trivial e isolada, sem risco identificado fora de seu
próprio app, não exige a suíte completa do projeto só porque ela existe.

Testes negativos (autorização negada, tentativa de mutação sem
privilégio, tentativa de acesso fora de escopo) são exigidos quando o
item envolve segurança ou integridade de dados, conforme
[testing.md#testes-de-autorização](testing.md#testes-de-autorização).

Todos os comandos de teste deste projeto são **dependentes de
ambiente** — exigem PostgreSQL acessível, pois `TenantTestCase` cria e
destrói schemas reais durante a execução, conforme
[testing.md#comandos](testing.md#comandos).

## Gate frontend / Tailwind

`static/css/output.css` **é rastreado** pelo Git — confirmável a
qualquer momento com `git ls-files static/css/output.css`. Os scripts
reais de `package.json` são:

```text
npm run build
npm run watch
```

Quando uma alteração afetar classes compiladas do Tailwind — por
exemplo, mudanças em `templates/`, `static/css/input.css` ou
`tailwind.config.js` — este workflow pode exigir `npm run build` como
gate condicional.

`npm run build` **pode modificar** `static/css/output.css` como efeito
esperado do comando (arquivo de saída regenerado a partir de
`static/css/input.css`). Esse arquivo só pode entrar no diff de uma
execução quando:

- a alteração for consequência esperada do build;
- estiver dentro do escopo declarado do Work Item;
- o diff resultante tiver sido revisado como qualquer outro arquivo
  alterado.

A existência do comando não constitui evidência de execução. O Work
Item deve registrar se este gate foi executado e qual foi o resultado,
conforme "Resultado de um gate" acima.

## Gate de documentação

Quando um arquivo `.md` for alterado ou criado, validar, quando
aplicável:

- links locais (o arquivo referenciado existe no caminho indicado);
- presença de newline final;
- ausência de trailing whitespace;
- ausência de linhas contendo apenas espaços em branco;
- ausência de caracteres NUL.

Essas verificações podem ser feitas com comandos de shell simples,
diretamente contra os arquivos alterados. Este documento não exige nem
propõe a criação de um script ou ferramenta nova para isso.

## Ferramentas não estabelecidas

Este documento não trata como obrigatória nenhuma das ferramentas
abaixo, porque nenhuma delas está declarada em `requirements/*.txt`,
em `package.json`, nem existe como arquivo de configuração na raiz do
repositório — verificável a qualquer momento por leitura direta desses
arquivos:

```text
pytest
Ruff
Black
isort
mypy
pre-commit
tox
coverage.py
Docker
Docker Compose
GitHub Actions / CI
Celery
Redis
```

Caso qualquer uma dessas ferramentas seja adotada no futuro, este
documento deve ser revisado para refletir sua presença real no HEAD —
não antes disso.

## Quality gates por Work Item

Cada Work Item declara, em sua própria seção "Quality gates" (ver
[docs/delivery/work/template.md](../delivery/work/template.md)), quais
destes gates — obrigatórios e condicionais — se aplicam a ele
especificamente. Este documento define o catálogo geral; o Work Item
define o subconjunto relevante à sua execução.

## Referências

- [workflow.md](workflow.md)
- [testing.md](testing.md)
- [git-procedure.md](git-procedure.md)
- [commands.md](commands.md)
- [docs/delivery/work/README.md](../delivery/work/README.md)
- [docs/delivery/work/template.md](../delivery/work/template.md)
