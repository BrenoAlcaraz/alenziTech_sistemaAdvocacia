---
title: Estratégia e comandos de testes
status: canonical
owner: development
last_reviewed: 2026-08-18
---

# Estratégia e comandos de testes

## Objetivo

Documentar, a partir da leitura direta do HEAD, o runner de testes
usado pelo Breno - LawSystem, o inventário completo de testes
existentes, sua organização, os comandos de execução e as limitações
atuais conhecidas da suíte — incluindo uma divergência já observada
entre comentários/docstrings de parte da suíte e o código-fonte atual.
Nenhum teste foi executado no lote original deste documento; ele não
afirmava resultado de execução (passou/falhou) para nenhum teste. A
única exceção, registrada minimamente pela correção factual do WI-0001,
é `apps/clientes/tests/test_autorizacao.py`, cuja execução (`OK`) é
citada no inventário abaixo. Para os três arquivos de
`apps/accounts/tests/`, este documento continua sem afirmar resultado
de execução.

## Runner atual

- Nenhum `TEST_RUNNER` customizado foi encontrado em
  `config/settings/base.py`, `config/settings/development.py` ou
  `config/settings/production.py` — o projeto usa o test runner padrão
  do Django (baseado em `unittest`), acionado por `python manage.py
  test`.
- Nenhuma configuração de `pytest` foi encontrada no repositório:
  não existe `pytest.ini`, `pyproject.toml` com seção `[tool.pytest]`,
  `tox.ini` nem `setup.cfg` na raiz. `pytest`/`pytest-django` não estão
  em `requirements/base.txt`, `requirements/development.txt` nem
  `requirements/production.txt`.
- Os quatro arquivos de teste existentes (três em `apps/accounts/tests/`
  e `apps/clientes/tests/test_autorizacao.py`) usam
  `django_tenants.test.cases.TenantTestCase` (de `django-tenants`, já
  uma dependência de `requirements/base.txt`) como classe base para a
  maior parte dos casos, além de `django.test.TestCase` puro em uma
  classe que não depende de schema de tenant
  (`TestMaiorNivelSeguranca`, em `test_interacoes_kernel.py`).
  `TenantTestCase` é reconhecida pelo test runner padrão do Django —
  não exige um executor de testes diferente.
- `TenantTestCase` cria um schema PostgreSQL isolado por classe de
  teste (via `get_test_schema_name()`/`setup_tenant()`, implementados em
  cada classe) e envolve cada método em uma transação com rollback
  automático — isso significa que executar a suíte de
  `apps/accounts/tests/` requer acesso a um PostgreSQL configurado,
  igual ao exigido para rodar a aplicação (ver
  [commands.md](commands.md#banco--multitenancy)).

## Inventário atual

Confirmado por `find apps -type f \( -name "test_*.py" -o -name
"tests.py" \)` no HEAD auditado: três arquivos de
`apps/accounts/tests/`, lidos integralmente nesta auditoria, mais
`apps/clientes/tests/test_autorizacao.py`, acrescentado pelo WI-0001 e
confirmado pela mesma busca:

| Arquivo | Área | Tipo de cobertura | Execução neste lote |
| --- | --- | --- | --- |
| `apps/accounts/tests/test_admin_tenant.py` (343 linhas) | Administrador do escritório: `usuario_admin_escritorio()`, `requer_admin_escritorio`, `tipo_conta_usuario()` | Teste Django com banco de tenant (todas as classes estendem `AdminTenantBase(TenantTestCase)`); exercita a função e o decorator diretamente sobre `User`/`PerfilUsuario`/`Group` via ORM, com `RequestFactory` para simular a requisição do decorator — não isolado de banco de dados | não executado |
| `apps/accounts/tests/test_permissoes_kernel.py` (888 linhas) | Kernel de permissões e habilitações: `permissao_efetiva()`, `habilitacao_efetiva()`, precedência admin → individual → papel → grupo legado, multi-papel, níveis, contagem de queries | Teste de integração do kernel com models reais (`PapelAcesso`, `UsuarioPapel`, `PermissaoPapel`, `HabilitacaoPapel`, `PermissaoUsuario`, `HabilitacaoUsuario`) via ORM, com banco de tenant (todas as classes estendem `KernelBase(TenantTestCase)`) e caracterização de número real de queries (`CaptureQueriesContext`) | não executado |
| `apps/accounts/tests/test_interacoes_kernel.py` (724 linhas) | Interações do kernel (override individual + papel + grupo legado), contrato de valores de `origem`, `_maior_nivel()`, regressão de nível preservado, queries classificadas por tipo SQL, smoke HTTP de páginas | Teste de aplicação com banco de tenant (`InteracoesBase(TenantTestCase)`), incluindo queries classificadas por tipo SQL e smoke HTTP (`django.test.Client`, via `force_login`, sobre um conjunto fixo de rotas); a classe `TestMaiorNivelSeguranca` usa `django.test.TestCase` puro (sem tenant), testando `_maior_nivel()` isoladamente | não executado |
| `apps/clientes/tests/test_autorizacao.py` (371 linhas, 26 testes) | Autorização de módulo (`tem_permissao_modulo`) e de habilitação (`tem_habilitacao`, `clientes_criar`/`clientes_editar`) nas sete views de `apps/clientes/views.py`, criado pelo WI-0001 | Teste Django com banco de tenant (`TenantTestCase`), sobre o mesmo padrão de fixtures de `apps/accounts/tests/`; cobre negação de módulo e de habilitação, ausência de mutação em operação negada, e preservação do comportamento de usuário autorizado | executado — `OK` (ver [WI-0001](../delivery/work/WI-0001-autorizacao-backend-clientes.md)) |

Nenhum outro app do repositório (`apps/processos`, `apps/tarefas`,
`apps/financeiro`, `apps/agenda`, `apps/chat`, `apps/modelos`,
`apps/laboratorio`, `apps/configuracoes`, `apps/saas_tenants`,
`apps/saas_billing`, `apps/dashboard`) possui arquivo de teste no HEAD
auditado.

## Organização atual

O padrão de organização de testes constatado no HEAD é
`apps/<app>/tests/` como pacote Python: `apps/accounts/tests/` (com
`__init__.py` implícito ao conter múltiplos arquivos `test_*.py`) e,
desde o WI-0001, `apps/clientes/tests/` (`__init__.py` explícito mais
`test_autorizacao.py`). Nenhum outro app possui essa estrutura ainda no
HEAD auditado.

## Comandos

Confirmados por `python manage.py help test` (executado nesta
auditoria, sem alteração de estado) e pelo uso de `TenantTestCase`
nos quatro arquivos existentes.

- **Teste alvo** — executa um método, uma classe ou um módulo
  específico:

  ```text
  python manage.py test apps.accounts.tests.test_permissoes_kernel
  python manage.py test apps.accounts.tests.test_permissoes_kernel.TestKernelContrato
  python manage.py test apps.accounts.tests.test_permissoes_kernel.TestKernelContrato.test_admin_acessa_todos_modulos
  ```

- **Teste do app** — executa todos os testes descobertos em um app:

  ```text
  python manage.py test apps.accounts
  ```

- **Suíte completa** — executa todos os testes descobertos no projeto:

  ```text
  python manage.py test
  ```

Diferença: um teste alvo isola o comportamento sob investigação e é o
mais rápido para iterar; a suíte do app cobre regressão dentro do
próprio módulo; a suíte completa cobre regressão em todo o projeto, mas
hoje é equivalente a `apps.accounts` + `apps.clientes`, já que nenhum
outro app possui testes.

Todos os comandos acima são **dependentes de ambiente**: exigem
PostgreSQL acessível com as credenciais configuradas (ver
[commands.md](commands.md#variáveis-de-ambiente)), pois
`TenantTestCase` cria e destrói schemas reais durante a execução.

## Estratégia por Work Item

Compatível com
[docs/delivery/work/README.md](../delivery/work/README.md#testes):

1. identificar os testes existentes relevantes para o item (ver
   "Inventário atual" acima);
2. adicionar testes novos diretamente ligados aos critérios de aceite
   do Work Item — não testes genéricos ou não relacionados;
3. incluir testes negativos quando segurança ou integridade de dados
   exigir (por exemplo, autorização negada, tentativa de mutação sem
   privilégio);
4. rodar o teste alvo primeiro;
5. rodar a regressão relevante (ao menos a suíte do(s) app(s) tocado(s)
   e de qualquer app que consuma o comportamento alterado);
6. ampliar a suíte executada (até a suíte completa) somente quando o
   Work Item tocar mais de um app, ou quando a mudança afetar
   comportamento compartilhado (por exemplo, o kernel de
   `apps/accounts`).

Nenhum Work Item deve registrar sucesso de execução de teste sem
evidência real, conforme o mesmo protocolo.

## Testes de autorização

Conceitualmente, um teste de autorização neste projeto deveria cobrir,
quando aplicável ao item em questão (sem implementar nada aqui):

- **permitido** — um usuário com autorização suficiente alcança o
  comportamento esperado;
- **negado** — um usuário sem autorização suficiente é impedido no
  backend, não apenas na interface;
- **módulo** — autorização de acesso a um módulo inteiro, resolvida
  hoje por `tem_permissao_modulo()` (`apps/accounts/permissoes.py`);
- **habilitação** — autorização de uma ação específica dentro de um
  módulo já autorizado, resolvida hoje por `tem_habilitacao()`
  (`apps/accounts/permissoes.py`);
- **objeto/escopo, quando aplicável** — se o usuário autorizado ao
  módulo/habilitação também está autorizado ao objeto específico
  (por exemplo, um `Cliente` ou `Processo` determinado). Esta dimensão
  ainda não é coberta por nenhum teste existente no HEAD auditado — ver
  "Estado atual da cobertura".

Estes conceitos já são exercitados, para o kernel em si, pelos três
arquivos de `apps/accounts/tests/`; sua aplicação a views de módulos
operacionais já ocorreu para Clientes via WI-0001
(`apps/clientes/tests/test_autorizacao.py`) e é o objeto de Work Items
futuros da Fase A do roadmap para os demais módulos (ver
[docs/delivery/roadmap.md](../delivery/roadmap.md#fase-a--consolidar-autorização-nas-operações)).

## Multitenancy

`TenantTestCase` (usada pelos quatro arquivos existentes) cria um schema
PostgreSQL isolado por classe de teste, o que exercita, por construção,
o mecanismo de isolamento de schema do django-tenants a cada execução.
Nenhum teste do HEAD auditado afirma explicitamente isolamento de dados
entre dois schemas de tenants diferentes na mesma execução (por
exemplo, criar dois tenants e confirmar que um não alcança dados do
outro) — os testes existentes operam dentro de um único schema por
classe. Este documento não afirma cobertura cross-tenant que não foi
identificada no código, consistente com
[docs/architecture/multitenancy.md](../architecture/multitenancy.md#critérios-arquiteturais).

## Estado atual da cobertura

- Cobertura extensa e detalhada do kernel de autorização
  (`apps/accounts/permissoes.py`, `apps/accounts/decorators.py`) dentro
  de um único schema de tenant: resolução de `permissao_efetiva()` e
  `habilitacao_efetiva()`, precedência entre origens (admin, individual,
  papel, grupo legado), agregação multi-papel, níveis por módulo,
  contagem de queries.
- Cobertura de fumaça HTTP (`TestSmokePagesAdmin`,
  `TestSmokePagesAdvogado`, em `test_interacoes_kernel.py`) para um
  conjunto fixo de rotas, cuja única asserção é a ausência de HTTP 500 —
  não é uma verificação de corretude de autorização por rota.
- Desde o WI-0001, `apps/clientes` possui teste de autorização de
  módulo e de habilitação (ver "Inventário atual"). Nenhum teste foi
  identificado para os demais módulos operacionais fora de
  `apps/accounts` (Processos, Tarefas, Agenda, Financeiro, Dashboard,
  Chat, Modelos, Laboratório, Configurações). Para Clientes e para os
  demais módulos, permanecem sem teste: escopo de dados; autorização
  sobre objeto específico (IDOR intra-tenant); isolamento cross-tenant
  explícito.
- Os testes de `apps/accounts/tests/` não foram executados nesta
  auditoria — as afirmações sobre esses três arquivos descrevem o que
  existe no código-fonte, não o resultado de rodá-los. Os testes de
  `apps/clientes/tests/test_autorizacao.py` foram executados na
  implementação do WI-0001, com resultado `OK`.

## Divergências conhecidas na suíte

`apps/accounts/tests/test_admin_tenant.py` e
`apps/accounts/tests/test_permissoes_kernel.py` contêm, em comentários
e docstrings, referências a um "kernel atual (pré-2.1C1B)" — por
exemplo, a descrição de que `usuario_admin_escritorio()` concederia
acesso via `is_superuser` ou via Group `administrador_escritorio`, sem
checar `is_active`, e de que `permissao_efetiva()` "não consulta
UsuarioPapel". Vários casos de teste desses dois arquivos usam um
helper `assertFuturo()` (que documenta explicitamente uma expectativa
de falha sob esse "kernel atual" descrito em comentário) para marcar
esses casos.

A leitura direta do código atual não corresponde a essas descrições:

- `apps/accounts/decorators.py::usuario_admin_escritorio` verifica
  exclusivamente `PerfilUsuario.is_admin_escritorio=True` combinado com
  `is_active=True` — o próprio docstring da função no código lido
  afirma isso como único caminho, sem atalho por `is_superuser` nem por
  Group.
- `apps/accounts/permissoes.py::_permissao_efetiva_com_contexto` já
  consulta `UsuarioPapel`, agregando múltiplos papéis pelo maior nível
  entre os papéis concedentes.

Já `apps/accounts/tests/test_interacoes_kernel.py` não usa
`assertFuturo()`/marcação de falha esperada — seu próprio docstring
declara que "todos os testes devem PASSAR com o kernel corrigido", uma
premissa consistente com o código atualmente lido em
`apps/accounts/decorators.py` e `apps/accounts/permissoes.py`.

Este documento não executa os testes e não afirma se as asserções de
`test_admin_tenant.py`/`test_permissoes_kernel.py` marcadas com
`assertFuturo()` passam ou falham sob o código atual — registra apenas
que a documentação em comentário desses dois arquivos descreve um
estado do kernel anterior ao código efetivamente lido nesta auditoria.
O código atual (`apps/accounts/decorators.py`,
`apps/accounts/permissoes.py`) deve ser tratado como a referência de
comportamento, conforme a
[hierarquia das fontes de verdade](../README.md#hierarquia-das-fontes-de-verdade)
("código e testes como evidência do comportamento implementado" tem
prioridade sobre material histórico). Qualquer execução futura desta
suíte deve tratar uma falha inesperada como regressão real a investigar,
não presumir que ela é "esperada" apenas porque um comentário do
arquivo assim descreve — este ponto já está registrado, com a mesma
orientação, em
[WI-0001](../delivery/work/WI-0001-autorizacao-backend-clientes.md#testes-esperados).

## Interpretação de resultados

Ao ler ou executar esta suíte no futuro, distinguir sempre:

- **teste existe** — o caso de teste está presente no arquivo-fonte.
- **teste foi executado** — o comando `python manage.py test` (ou
  equivalente) foi de fato rodado nesta sessão de trabalho.
- **passou** — o teste foi executado e o runner reportou sucesso.
- **falhou** — o teste foi executado e o runner reportou falha ou erro.
- **não executado** — nenhuma execução ocorreu; qualquer afirmação
  sobre o resultado seria especulação, não evidência.

Este documento afirma apenas "teste existe" para os três arquivos de
`apps/accounts/tests/`, sem afirmação de "passou"/"falhou". Para
`apps/clientes/tests/test_autorizacao.py`, a exceção mínima registrada
pelo WI-0001 é "teste foi executado" e "passou" (`OK`), conforme
"Inventário atual" acima.

## Ferramentas não identificadas

`pytest`, `pytest-django`, `coverage.py` e `tox` não foram encontrados
em `requirements/base.txt`, `requirements/development.txt`,
`requirements/production.txt`, nem como arquivo de configuração
(`pytest.ini`, `tox.ini`, `pyproject.toml`) na raiz do repositório. O
runner de testes confirmado é exclusivamente o padrão do Django
(`python manage.py test`).

## Referências

- [README.md](README.md)
- [commands.md](commands.md)
- [docs/delivery/work/README.md](../delivery/work/README.md)
- [docs/delivery/work/WI-0001-autorizacao-backend-clientes.md](../delivery/work/WI-0001-autorizacao-backend-clientes.md)
- [docs/delivery/current-state.md](../delivery/current-state.md#testes)
- [docs/architecture/multitenancy.md](../architecture/multitenancy.md)
