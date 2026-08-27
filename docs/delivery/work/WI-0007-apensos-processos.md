---
title: WI-0007 — Apensos de Processos
status: canonical
owner: delivery
last_reviewed: 2026-08-20
---

# WI-0007 — Apensos de Processos

## Estado

`in_progress`

## Objetivo

Implementar a relação simétrica de apensos entre Processos independentes,
com navegação bidirecional, persistência de um único par físico e autorização
de mutação nos dois lados da relação.

## Fase e risco

Fase: **Fase C — Integridade de domínio**.

Risco: **moderado**, por introduzir relação autorreferente entre Processos,
constraints para integridade A ↔ B, leitura condicionada por escopo, mutação
simultânea em dois objetos, superfície de IDOR e isolamento por tenant.

## Resultado observável pelo Product Owner

### Ao concluir este WI

- o detalhe do Processo possui a aba `Apensos`;
- outro Processo já cadastrado pode ser relacionado por `Adicionar apenso`;
- a relação aparece nos dois sentidos e permite navegar para o Processo relacionado;
- cada Processo relacionado aparece em card com seus próprios dados atuais;
- a relação pode ser removida sem excluir qualquer Processo.

### Ainda não estará coberto

- hierarquia principal/filho, apensação automática ou árvore recursiva;
- importação ou fusão de dados;
- propagação de participantes, responsáveis, status, andamentos ou documentos;
- tipos adicionais de relação;
- IA.

## Contexto e dependências

- fase vertical de Processos após WI-0005 e WI-0006;
- HEAD inicial auditado: `a0cf4deaf47990536833b428db20788119bbf9fe`;
- WI-0005 e WI-0006 permanecem `in_progress` por dependerem de validação manual;
- esta execução não altera o estado desses itens nem autoriza commit ou push.

## Fontes governantes

- [PDR-0012 — Relação simétrica de processos apensos](../../product/decisions/PDR-0012-relacao-simetrica-processos-apensos.md)
- [Processos](../../product/modules/processos.md)
- [PDR-0010 — Autorização, escopo e responsabilidade de Processos](../../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [Modelo de autorização](../../security/authorization-model.md)
- [Escopo de dados](../../security/data-scope.md)
- [Matriz de autorização](../../security/authorization-matrix.md)
- [Roadmap](../roadmap.md)

## Escopo

- persistir A ↔ B uma única vez, sem principal, pai ou filho;
- impedir autorrelação e duplicidade também no banco;
- expor consulta simétrica centralizada;
- adicionar a aba `Apensos` ao detalhe com contador restrito ao escopo visível;
- permitir navegação nos dois sentidos e exibir dados próprios do Processo relacionado;
- oferecer seleção somente de Processos mutáveis, incluindo arquivados, excluindo
  a origem e relações existentes;
- criar e remover a relação somente quando ambos os Processos forem mutáveis;
- manter Cliente, responsável, equipe, status, fase, participantes, representantes,
  autoridades, andamentos, prazos e documentos independentes;
- adicionar migration reversível, testes adversariais e documentação canônica.

## Fora do escopo

- hierarquia de Processo principal/apenso;
- apensação automática e importação de dados;
- inferência transitiva;
- cópia, herança, fusão ou propagação de participantes, responsáveis, status,
  andamentos ou documentos;
- árvore recursiva e tipos diferentes de relação;
- criação de Processo dentro do fluxo de apensos;
- IA;
- fechamento manual dos Work Items H1 anteriores.

## Regras de segurança

- leitura do Processo relacionado passa por `_processos_no_escopo`;
- mutação exige autorização no módulo e pertencimento de ambos os lados a
  `_processos_mutaveis`;
- usuário não administrador não altera relação com Processo de outro responsável,
  mesmo com nível `Todos` para leitura;
- Administrador do Escritório pode mutar Processos do tenant;
- falhas de ownership, IDs trocados, vínculo alheio ou objeto inexistente retornam
  negação sem revelar existência nem produzir mutação parcial;
- isolamento por schema impede leitura ou referência entre tenants.

## Critérios de aceite

- [x] A ↔ B é visível a partir de A e B com um único registro físico.
- [x] A ↔ A e pares duplicados são rejeitados por aplicação e banco.
- [x] A ↔ B e B ↔ C não criam A ↔ C.
- [x] criação e remoção preservam integralmente os dois Processos.
- [x] a exclusão de um Processo remove somente seus vínculos por cascata.
- [x] o contador e os cards incluem apenas Processos no escopo de leitura.
- [x] o seletor inclui apenas candidatos mutáveis e permite arquivados.
- [x] criação e remoção exigem mutabilidade nos dois lados.
- [x] tentativas IDOR, IDs inexistentes e acesso entre tenants não alteram dados.
- [x] migration aplica, reverte e reaplica em PostgreSQL preservando Processos.
- [x] regressões de `processos`, `accounts` e `clientes` passam.
- [x] build de frontend passa e o artefato compilado é versionado quando alterado.

## Evidência inicial

- preflight confirmou branch `docs/reorganizacao-harness`;
- HEAD local e remoto confirmados em `a0cf4deaf47990536833b428db20788119bbf9fe`;
- working tree estava limpo antes da implementação;
- `python manage.py check`: zero issues após a primeira implementação;
- `python manage.py makemigrations --check --dry-run`: nenhuma alteração pendente.

## Evidências da implementação

### Model, migration e endpoints

- `VinculoProcessoApenso` persiste somente os dois FKs e `criado_em`, normaliza
  o par por PK e usa `CASCADE` apenas do Processo para a linha de vínculo;
- constraints `processos_apenso_ordem_valida` e `processos_apenso_par_unico`
  impedem autorrelação, ordem inversa física e duplicidade; os FKs possuem os
  índices automáticos do Django e a unicidade cria índice composto;
- migration `0010_vinculoprocessoapenso.py` depende da `0009` e foi exercitada
  com apply, rollback e reaplicação em PostgreSQL/django-tenants;
- endpoints POST `adicionar_apenso` e `remover_apenso` carregam origem e alvo na
  fronteira `_processos_mutaveis`, operam em transação e redirecionam à aba.

### Testes e gates executados

- `.venv\\Scripts\\python.exe manage.py test apps.processos.tests.test_apensos apps.processos.tests.test_migrations_apensos --verbosity 1`: 13 testes, `OK`;
- `.venv\\Scripts\\python.exe manage.py test apps.processos apps.accounts apps.clientes --verbosity 1`: 244 testes, `OK`, em 275,808 s;
- `.venv\\Scripts\\python.exe manage.py test apps.processos --noinput --verbosity 1`: 101 testes, `OK`, em 121,016 s;
- `.venv\\Scripts\\python.exe manage.py test apps.accounts --noinput --verbosity 1`: 86 testes, `OK`, em 74,569 s;
- `.venv\\Scripts\\python.exe manage.py test apps.clientes --noinput --verbosity 1`: 57 testes, `OK`, em 6.291,310 s;
- `.venv\\Scripts\\python.exe manage.py check`: zero issues;
- `.venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run`: `No changes detected`;
- `git diff --check`: sem saída, exit code zero;
- `npm run build`: concluído; aviso não bloqueante de base `caniuse-lite`
  desatualizada, sem atualização de dependência fora do escopo;
- PostgreSQL validado nos testes de constraint, tenant e migration.

### Arquivos alterados

- `apps/processos/{admin.py,forms.py,models.py,services.py,urls.py,views.py}`;
- `apps/processos/migrations/0010_vinculoprocessoapenso.py`;
- `apps/processos/tests/{test_apensos.py,test_migrations_apensos.py}`;
- `templates/processos/detalhe.html` e `static/css/output.css`;
- `docs/delivery/work/WI-0007-apensos-processos.md` e `docs/delivery/roadmap.md`;
- `docs/product/decisions/PDR-0012-relacao-simetrica-processos-apensos.md`,
  `docs/product/decisions/README.md`, `docs/product/modules/processos.md` e
  `docs/governance/decision-index.md`.

## Validação manual futura

PENDENTE DO PO. Executar futuramente, em lote com WI-0005 e WI-0006, com dois
usuários não administradores de responsáveis distintos e um Administrador do
Escritório:

1. abrir Processo sem apensos e conferir o empty state exato;
2. adicionar B a A, conferir card e contador e navegar de A para B;
3. confirmar que A aparece automaticamente na aba Apensos de B;
4. tentar repetir o par e a ordem inversa, sem duplicidade;
5. remover por A e confirmar desaparecimento também em B, preservando ambos;
6. validar usuário `Todos` lendo o card alheio sem ação de mutação;
7. validar que Processo fora do escopo não aparece nem afeta o contador;
8. conferir que dados próprios dos Processos não foram propagados.

O item permanece `in_progress` até essa evidência ser registrada por fluxo
próprio. Nenhum H1 ou H2 é registrado nesta execução.

## Resultado desta execução

Implementação técnica pronta para review independente após bateria automatizada,
gates e self-review. Validação manual permanece pendente do Product Owner;
commit e push não estão autorizados.
