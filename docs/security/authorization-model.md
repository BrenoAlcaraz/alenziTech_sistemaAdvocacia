---
title: Modelo de autorização
status: canonical
owner: security
last_reviewed: 2026-08-06
---

# Modelo de autorização

## Objetivo

Este documento descreve, para o Breno - LawSystem:

- os conceitos de autorização usados no produto, alinhados a
  [../product/glossary.md](../product/glossary.md);
- o kernel de autorização constatado em `apps/accounts`;
- as regras de precedência que esse kernel realmente aplica, conforme a
  leitura de `apps/accounts/permissoes.py`;
- as diferenças entre papel de acesso, permissão, habilitação e escopo
  de dados, que não são a mesma coisa e não devem ser tratadas como
  intercambiáveis.

Este documento não afirma que o kernel descrito abaixo está aplicado em
todas as views do sistema. A aplicação constatada, view por view, está
na seção "Aplicação nas views".

## Conceitos

Definições alinhadas a
[../product/glossary.md](../product/glossary.md); este documento não as
redefine de forma incompatível.

- **Usuário** — pessoa autenticada, vinculada a uma conta dentro de um
  tenant (`auth.User`, padrão do Django).
- **PerfilUsuario** — registro complementar `OneToOneField` para
  `auth.User`, em `apps/accounts/models.py`. Não é o mecanismo de
  autorização em si; carrega `nome_completo`, `cargo`, `avatar` e a flag
  `is_admin_escritorio`.
- **Administrador do escritório** — autoridade administrativa máxima
  dentro do tenant. Distinto de Platform Admin e de superusuário técnico
  do Django, conforme
  [../governance/terminology-policy.md](../governance/terminology-policy.md).
- **Papel de acesso** — controla autorização; modelado por
  `PapelAcesso`, em `apps/accounts/models.py`. Distinto de cargo
  profissional.
- **Autorização de módulo** — decide se o usuário pode acessar
  determinado módulo (Processos, Clientes, Financeiro etc.). No kernel
  atual, está relacionada principalmente ao campo `ativo` de
  `PermissaoPapel`/`PermissaoUsuario`.
- **Nível de acesso técnico atual** — o campo `nivel` da mesma linha de
  `PermissaoPapel`/`PermissaoUsuario`. Valores como `somente_seus`,
  `todos`, `solicitacoes` e `dados` misturam preocupações de escopo,
  visibilidade e modalidade de acesso que ainda não foram decompostas
  entre si. Este documento não chama esse campo simplesmente de
  "permissão de ação"; sua decomposição definitiva depende da futura
  matriz de autorização e da implementação efetiva de escopo — ver
  "Direção canônica" e [data-scope.md](data-scope.md).
- **Habilitação funcional** — capacidade ou item específico dentro de um
  módulo (por exemplo, criar processo, editar cliente), modelada por
  `HabilitacaoPapel`/`HabilitacaoUsuario`. A habilitação pode contribuir
  para autorizar uma ação, mas não substitui a autorização de módulo, o
  escopo de dados, a autorização sobre objeto nem a validação da
  operação.
- **Autorização da ação** — a decisão final no backend sobre executar
  uma operação concreta (criar, editar, arquivar, excluir, pagar,
  reatribuir, adicionar participante, etc.). Esta auditoria não
  identificou, no código lido, uma entidade autônoma e completa de
  "permissão de ação": algumas ações aparecem como habilitações
  funcionais (item acima), enquanto outras dependem apenas de
  decorators (`@login_required`) e do método HTTP, sem checagem
  específica identificada — ver "Aplicação nas views". Este documento
  não presume uma modelagem que o código não possui.
- **Regra individual** — sobrescrita de permissão ou habilitação para um
  usuário específico, modelada por `PermissaoUsuario`/
  `HabilitacaoUsuario`. A presença da linha substitui a resolução por
  papel/grupo para aquele usuário, módulo (e item, no caso de
  habilitação).
- **Cargo profissional** — texto descritivo (`PerfilUsuario.cargo`), sem
  efeito sobre autorização.
- **Equipe** — agrupamento organizacional (`Equipe`,
  `apps/accounts/models.py`), usado como referência de escopo, não como
  mecanismo de autorização em si.
- **Gerente** — `MembroEquipe.eh_gerente=True`; relação organizacional
  de responsabilidade sobre uma equipe, não um papel de acesso global.
- **Escopo de dados** — quais registros específicos, dentro de um módulo
  já autorizado, um usuário alcança. Tratado em detalhe em
  [data-scope.md](data-scope.md).

## Kernel constatado no código

Constatado em `apps/accounts/models.py`:

- `PerfilUsuario.is_admin_escritorio` — flag booleana que define
  administrador do escritório.
- `PapelAcesso` — papel de acesso dinâmico, configurável, com
  `codigo_preset` e `protegido_sistema` para presets de fábrica.
- `UsuarioPapel` — vínculo usuário↔papel; um usuário pode ter vários
  papéis simultâneos (`UniqueConstraint` é por par usuário/papel, não
  limita a um papel por usuário).
- `PermissaoPapel` — permissão de módulo por `papel` (novo sistema) ou
  por `tipo_conta` (Group legado: `limitado`, `financeiro`); campos
  `ativo` e `nivel`.
- `PermissaoUsuario` — sobrescrita individual de permissão de módulo por
  usuário; presença da linha substitui a resolução por papel/grupo.
- `HabilitacaoPapel` — habilitação de item de funcionalidade por `papel`
  ou por `tipo_conta`.
- `HabilitacaoUsuario` — sobrescrita individual de habilitação por
  usuário, módulo e item.
- Múltiplos papéis por usuário — confirmado pela ausência de
  `UniqueConstraint` que limite `UsuarioPapel.usuario` a um único
  registro, e pela agregação por união implementada em
  `apps/accounts/permissoes.py`.
- Regras individuais — confirmadas por `PermissaoUsuario` e
  `HabilitacaoUsuario`.

Constatado em `apps/accounts/permissoes.py`:

- Helpers de permissões efetivas: `permissao_efetiva()`,
  `tem_permissao_modulo()`, `nivel_acesso_modulo()`.
- Helpers de habilitações efetivas: `habilitacao_efetiva()`,
  `tem_habilitacao()`.
- Fallback para `auth.Group`: `tipo_conta_usuario()` resolve o tipo de
  conta técnico (`limitado` ou `financeiro`) a partir de
  `user.groups`, usado apenas quando o usuário não possui nenhum
  `UsuarioPapel`.
- `usuario_eh_gerente_de_alguma_equipe()` — helper de gerência de
  equipe; o próprio código documenta que "não afeta permissões de
  módulo ainda — reservado para fase futura".

Constatado em `apps/accounts/decorators.py`:

- `usuario_admin_escritorio(user)` — na leitura atual deste arquivo,
  verifica exclusivamente `PerfilUsuario.is_admin_escritorio=True`
  combinado com `user.is_active=True`. Nenhum atalho por
  `user.is_superuser` nem por associação ao Group
  `administrador_escritorio` foi encontrado nesta função.
- `requer_admin_escritorio` — decorator que usa
  `usuario_admin_escritorio()`; redireciona anônimos para login e nega
  com `PermissionDenied` qualquer usuário autenticado que não seja
  administrador do escritório.
- Constantes de grupos técnicos: `GRUPO_ADMINISTRADOR_ESCRITORIO`,
  `GRUPO_LIMITADO`, `GRUPO_FINANCEIRO` como ativos; `GRUPO_GERENTE` e
  `GRUPO_ADVOGADO` mantidos apenas como legado, conforme comentário do
  próprio arquivo ("Slugs legados — mantidos para referência em
  migrations e fallback de exibição").

Constatado em `apps/accounts/escopo.py`:

- Helpers de consulta de equipes (`equipes_do_usuario`,
  `equipes_gerenciadas_pelo_usuario`, `usuario_gerencia_equipe`,
  `equipe_padrao_para_usuario`, `equipes_descendentes`) e constantes de
  escopo (`ESCOPO_TUDO`, `ESCOPO_EQUIPES_GERENCIADAS`, `ESCOPO_EQUIPE`,
  `ESCOPO_PROPRIOS_ITENS`, `ESCOPO_NENHUM`). O próprio módulo declara,
  em seu docstring: "Estes helpers ainda não aplicam filtros nos módulos
  operacionais. Eles apenas expõem consultas de equipes para uso
  futuro." Ver [data-scope.md](data-scope.md).

Este documento não trata a existência desse kernel como prova de que ele
é aplicado em todas as views — ver "Aplicação nas views" abaixo.

**Divergência entre a documentação de teste e o código de
`apps/accounts/permissoes.py` lido nesta auditoria:** os módulos
`apps/accounts/tests/test_admin_tenant.py` e
`apps/accounts/tests/test_permissoes_kernel.py` trazem docstrings de
módulo, classe e teste que descrevem um "kernel atual (pré-2.1C1B)" no
qual `permissao_efetiva()`/`habilitacao_efetiva()` "não consultam
`UsuarioPapel`" e não agregam múltiplos papéis (por exemplo, os
docstrings de `TestKernelPapelUnico` e `TestKernelMultiPapel`, em
`test_permissoes_kernel.py`: "Kernel atual: não consulta UsuarioPapel").
Isso não corresponde ao código de `_permissao_efetiva_com_contexto()`
lido nesta auditoria (documentado na seção "Precedência constatada"
acima), que já consulta `UsuarioPapel`, resolve `ids_papeis_ativos` e
agrega múltiplos papéis por união. Um terceiro arquivo de teste,
`apps/accounts/tests/test_interacoes_kernel.py`, tem docstring de módulo
distinto ("Suíte de auditoria e regressão — Rodada 2.1C1B.2. Todos os
testes devem PASSAR com o kernel corrigido") e suas asserções (por
exemplo, `TestOrigemContrato`, `TestInteracoesOverrideComPapel`) são
consistentes com o comportamento de `UsuarioPapel`/multi-papel
constatado na leitura direta de `apps/accounts/permissoes.py`. Esta
auditoria não executa testes e não afirma se os testes de
`test_admin_tenant.py`/`test_permissoes_kernel.py` passam ou falham
hoje; registra apenas que a documentação desses dois arquivos, lida de
forma estática, descreve um estado do kernel anterior ao que o código
atual de `apps/accounts/permissoes.py` implementa, e que
`test_interacoes_kernel.py` é o arquivo cuja documentação é consistente
com o código lido.

## Distinções obrigatórias

- **Autenticação não é autorização.** `@login_required` prova apenas
  identidade; não prova que a ação ou o dado acessado é autorizado.
- **Papel não é cargo.** `PapelAcesso`/`UsuarioPapel` controlam
  autorização; `PerfilUsuario.cargo` é texto livre sem efeito sobre
  acesso.
- **Equipe não é papel.** `Equipe`/`MembroEquipe` são organizacionais;
  não concedem, por si, nenhuma permissão ou habilitação.
- **Gerente não é administrador global.** `MembroEquipe.eh_gerente=True`
  não passa, em nenhum ponto constatado do kernel, pelo caminho de
  `usuario_admin_escritorio()` nem pelos helpers de
  `permissao_efetiva()`/`habilitacao_efetiva()`.
- **Autorização de módulo não é nível de acesso técnico atual.** O
  campo `ativo` de `PermissaoPapel`/`PermissaoUsuario` decide se o
  módulo está aberto; o campo `nivel` da mesma linha é uma classificação
  técnica adicional, não uma prova de escopo aplicado.
- **Nível de acesso técnico atual não é permissão de ação nem escopo de
  dados.** `nivel` é resolvido e devolvido por `permissao_efetiva()`,
  mas nenhuma view consultada nesta auditoria o lê para filtrar um
  `QuerySet` — ver [data-scope.md](data-scope.md).
- **Permissão (autorização de módulo + nível) não é habilitação.**
  Autorização de módulo e nível decidem se o módulo está aberto e qual a
  amplitude técnica declarada; habilitação (`HabilitacaoPapel`/
  `HabilitacaoUsuario`) decide se um item específico de funcionalidade
  está ligado dentro desse módulo. `_habilitacao_efetiva_com_contexto()`
  só concede habilitação se a permissão do módulo já estiver ativa
  (origem `"permissao_desligada"` quando não está).
- **Habilitação funcional não substitui autorização sobre objeto, escopo
  de dados nem validação da operação.** Habilitação decide se uma ação
  existe em tese para o usuário dentro do módulo; não decide sobre quais
  registros específicos ela pode ser exercida (escopo, ver
  [data-scope.md](data-scope.md)), nem confirma que o objeto carregado
  por `pk`/`id` é o correto (autorização sobre objeto), nem valida a
  integridade da operação em si.
- **Autorização da ação é a decisão final do backend, não uma entidade
  isolada modelada no kernel atual.** Ela depende, conforme o fluxo, de
  alguma combinação de autorização de módulo, habilitação funcional,
  escopo de dados e autorização sobre objeto — mas esta auditoria não
  encontrou uma tabela ou helper único de "permissão de ação" que
  centralize essa decisão para todas as operações.
- **Escopo não é autorização sobre qualquer ação.** Estar dentro do
  escopo de dados de um registro não implica que qualquer ação sobre
  esse registro esteja habilitada.
- **Superuser técnico não é automaticamente Administrador do escritório
  como conceito de produto.** Constatação atual: `usuario_admin_escritorio()`,
  em `apps/accounts/decorators.py`, não verifica `is_superuser` e já
  verifica `is_active` explicitamente antes de conceder acesso. Uma
  divergência é registrada abaixo, em "Pontos em aberto": docstrings de
  `apps/accounts/tests/test_admin_tenant.py` descrevem um "kernel atual"
  no qual `is_superuser` concederia acesso de administrador e no qual
  `is_admin_escritorio=True` "short-circuits sem checar `is_active`", o
  que não corresponde ao código lido em `apps/accounts/decorators.py`
  nesta auditoria.
- **Platform Admin não é Administrador do escritório.** Ver
  [overview.md](overview.md) — nenhum mecanismo de autorização dedicado
  ao Platform Admin foi encontrado no código lido.

## Precedência constatada

Ordem de avaliação de `_permissao_efetiva_com_contexto()`, em
`apps/accounts/permissoes.py`, confirmada pela leitura direta do código:

1. Módulo não reconhecido em `NIVEIS_POR_MODULO` → nega sem consultar o
   banco.
2. Usuário sem `pk` → nega.
3. Usuário com `is_active=False` → nega, origem `"inativo"`.
4. `usuario_admin_escritorio(user)` verdadeiro → acesso total ao módulo,
   no maior nível configurado (`_nivel_admin`), origem `"admin"`. Este
   caminho é avaliado **antes** de qualquer `PermissaoUsuario`
   individual — um administrador do escritório não é bloqueado por uma
   linha de `PermissaoUsuario` com `ativo=False`.
5. `PermissaoUsuario` para o usuário e módulo, se existir — usada
   diretamente (`ativo`/`nivel`), origem `"individual"`, independente de
   o usuário ter ou não `UsuarioPapel`.
6. Se o usuário possui pelo menos um `UsuarioPapel` (`tem_qualquer_up`,
   independentemente de estar ativo):
   - Somente os papéis com `UsuarioPapel.ativo=True` e
     `PapelAcesso.ativo=True` entram na resolução
     (`ids_papeis_ativos`); se nenhum papel estiver nessas condições,
     nega, origem `"papel"`.
   - As linhas de `PermissaoPapel` para esses papéis e o módulo são
     carregadas; **múltiplos papéis são agregados por união**: se
     qualquer um dos papéis ativos tiver `PermissaoPapel.ativo=True`
     para o módulo, o acesso é concedido, e o `nivel` resultante é o
     maior nível entre todas as concessões ativas
     (`_maior_nivel()`) — não há, neste caminho, um mecanismo de
     negação explícita de um papel que bloqueie a concessão de outro
     papel do mesmo usuário.
   - Se existirem linhas de `PermissaoPapel` para esses papéis e módulo,
     mas nenhuma ativa, o acesso é negado, mas o `nivel` retornado é o
     menor nível válido entre as linhas existentes
     (`_menor_nivel_seguro()`), preservando um nível conservador em vez
     de um valor vazio.
   - Uma vez que o usuário tem qualquer `UsuarioPapel`, o fallback de
     `auth.Group` (passo 7) não é consultado, mesmo que os papéis não
     concedam acesso ao módulo em questão — confirmado pelo comentário
     do próprio código em `_habilitacao_efetiva_com_contexto()`:
     "Caminho de papéis... nunca consulta HabilitacaoPapel por
     tipo_conta."
7. Se o usuário não possui nenhum `UsuarioPapel` — fallback legado:
   `tipo_conta_usuario()` resolve o tipo de conta a partir de
   `user.groups` (retorna `None` se o usuário estiver em zero ou em mais
   de um dos grupos `limitado`/`financeiro`); se `None`, nega. Caso
   contrário, busca `PermissaoPapel` por `tipo_conta` e `modulo`; usa seu
   `ativo`/`nivel` se existir, origem `"grupo_legado"`; senão nega,
   mesma origem.
8. Ausência de qualquer concessão nos passos acima → nega, origem
   `"nenhuma"`.

`_habilitacao_efetiva_com_contexto()` segue a mesma estrutura de
precedência (admin → individual → papel → grupo legado), com uma
condição adicional: a habilitação só é avaliada se a permissão do
módulo (passo acima) já estiver com `tem_acesso=True`; caso contrário,
retorna `habilitado=False`, origem `"permissao_desligada"`.

**Autorização de módulo, nível técnico e habilitação nesta ordem:** o
`nivel` (nível de acesso técnico atual) é resolvido pela mesma linha e
pela mesma precedência que a autorização de módulo (`ativo`) — não
existe, no código lido, uma tabela ou precedência separada para `nivel`.
A habilitação (item específico) é resolvida por tabelas próprias
(`HabilitacaoPapel`/`HabilitacaoUsuario`) com a mesma ordem de
precedência, mas condicionada à autorização de módulo estar ativa. O
`nivel` resolvido aqui não é, por si, aplicado como escopo de dados em
nenhuma view — ver [data-scope.md](data-scope.md).

## Direção canônica

- Múltiplos papéis por usuário são permitidos e agregados por união,
  conforme já implementado.
- Overrides individuais (`PermissaoUsuario`/`HabilitacaoUsuario`) são
  permitidos e têm precedência sobre papel/grupo.
- O backend deve usar a resolução efetiva (`permissao_efetiva()`/
  `habilitacao_efetiva()`) como fonte de verdade para autorização, não
  apenas `@login_required`.
- Nenhuma autorização deve depender somente da interface — ver
  "Interface não concede autorização" em [overview.md](overview.md).
- A autorização deve ser reutilizável e testável — os testes existentes
  em `apps/accounts/tests/` cobrem extensivamente a resolução do
  kernel, mas essa cobertura não se estende às views operacionais fora
  de `apps/accounts`/`apps/configuracoes`.
- Mudanças de acesso (atribuição/remoção de papel, alteração de
  permissão ou habilitação) precisam de rastreabilidade — não
  confirmada no código lido; ver "Pontos em aberto".
- A política final de autorização por módulo será formalizada em um
  documento futuro de matriz de autorização, ainda não criado neste
  lote.
- A decomposição definitiva do campo `nivel` (nível de acesso técnico
  atual) entre preocupações de escopo, visibilidade e modalidade de
  acesso depende dessa futura matriz de autorização e da implementação
  efetiva de escopo de dados descrita em [data-scope.md](data-scope.md)
  — este documento não antecipa essa decomposição.

## Aplicação nas views

Módulos e fluxos realmente inspecionados nesta auditoria:

| Módulo ou fluxo inspecionado | Controle constatado | Lacuna ou observação |
| --- | --- | --- |
| `apps/accounts` — `login_view`, `logout_view` | Nenhum decorator de autorização (fluxo de autenticação em si) | Não aplicável — são as próprias views de entrada/saída de sessão |
| `apps/configuracoes` — `index`, `editar_perfil` | `@login_required` | Sem helper de permissão/habilitação; acessível a qualquer usuário autenticado do tenant |
| `apps/configuracoes` — `novo_usuario`, `equipes`, `nova_equipe`, `editar_equipe`, `equipe_membros`, `remover_membro_equipe`, `alternar_gerente_equipe`, `permissoes`, `editar_escritorio` | `@requer_admin_escritorio` | Controle binário administrador/não-administrador; não consulta `tem_permissao_modulo`/`tem_habilitacao`, mesmo sendo a tela que os configura |
| `apps/clientes` — `lista`, `detalhe`, `novo`, `editar`, `desativar`, `inativos`, `reativar` | `@login_required` | Ausência constatada de helper de permissão/habilitação e de filtro de `QuerySet` por escopo; `get_object_or_404(Cliente, pk=pk, ativo=True)` sem condição de posse |
| `apps/processos` — `lista`, `detalhe`, `novo`, `editar`, `arquivados`, `arquivar`, `reabrir`, `adicionar_movimentacao`, `adicionar_parte` | `@login_required` | Ausência constatada de helper de permissão/habilitação e de filtro de `QuerySet`; `equipe_padrao_para_usuario()` é usada apenas para sugerir a equipe na criação, não para restringir leitura; `get_object_or_404(Processo, pk=pk)` sem condição de posse |
| `apps/tarefas` — `quadro`, `lista`, `nova`, `editar`, `concluir`, `reabrir`, `iniciar`, `excluir` | `@login_required` | Ausência constatada de helper de permissão/habilitação e de filtro de `QuerySet`; `get_object_or_404(Tarefa, pk=pk)` sem condição de posse |
| `apps/agenda` — `index`, `editar`, `form_compromisso`, `concluir`, `cancelar`, `reabrir`, `excluir` | `@login_required` | Ausência constatada de helper de permissão/habilitação e de filtro de `QuerySet`; `get_object_or_404(Compromisso, pk=pk)` sem condição de posse |
| `apps/financeiro` — `index`, `custas`, `form_lancamento`, `editar_lancamento`, `marcar_pago`, `cancelar_lancamento`, `reabrir_lancamento`, `excluir_lancamento`, `form_custa` | `@login_required` | Ausência constatada de helper de permissão/habilitação; sem distinção entre usuário com/sem acesso ao caixa geral prevista em [../product/modules/financeiro.md](../product/modules/financeiro.md); `get_object_or_404(LancamentoFinanceiro, pk=pk)` sem condição de posse |
| `apps/dashboard` — `painel` | `@login_required` | Agregações (`Cliente.objects.filter(ativo=True).count()` etc.) sem qualquer filtro de escopo — todo usuário autenticado vê os mesmos totais globais |
| `apps/chat` — `lista`, `detalhe`, `global_sala` | `@login_required` | Única sala implementada é `Conversa.TIPO_GLOBAL`, compartilhada por todo o tenant; `lista`/`detalhe` apenas redirecionam para ela; sem helper de permissão/habilitação |
| `apps/modelos` — `lista`, `novo`, `detalhe`, `editar`, `importar` | `@login_required` | Ausência constatada de helper de permissão/habilitação e de filtro de `QuerySet`; `get_object_or_404(ModeloPeca, pk=pk)` sem condição de posse |
| `apps/laboratorio` — `index` | `@login_required` | View apenas renderiza template; nenhuma lógica de negócio ou de autorização adicional |

## Pontos em aberto

- Semântica final de negação explícita entre papéis (o kernel atual só
  implementa união positiva entre papéis ativos, sem um mecanismo de
  "papel nega explicitamente" que sobreponha outro papel do mesmo
  usuário).
- Auditoria de mudanças de papel, permissão e habilitação — não
  confirmada no código lido.
- Cache de permissões — nenhum uso de `cache` foi identificado próximo a
  `apps/accounts/permissoes.py`; `CACHES` não está configurado em
  `config/settings/base.py`, `development.py` ou `production.py`.
- Política final para superuser técnico do Django — divergência
  registrada acima entre o comportamento atual de
  `usuario_admin_escritorio()` (não verifica `is_superuser`; verifica
  `is_active`) e os docstrings de
  `apps/accounts/tests/test_admin_tenant.py`, que descrevem um "kernel
  atual" com verificação de `is_superuser` e sem verificação de
  `is_active`; esta auditoria não resolve essa divergência, apenas a
  registra.
- Documentação de teste desatualizada em relação ao kernel de
  `UsuarioPapel`/multi-papel — divergência registrada acima, em "Kernel
  constatado no código", entre os docstrings de
  `apps/accounts/tests/test_admin_tenant.py`/`test_permissoes_kernel.py`
  (que descrevem um kernel que "não consulta `UsuarioPapel`") e o código
  de `apps/accounts/permissoes.py` efetivamente lido nesta auditoria
  (que já consulta `UsuarioPapel` e agrega múltiplos papéis); esta
  auditoria não executa testes nem resolve a divergência, apenas a
  registra como um ponto que merece atualização da documentação de
  teste.
- Administração emergencial (acesso excepcional a um tenant) — sem
  decisão encontrada nas fontes canônicas.
- Matriz de autorização definitiva por módulo — documento futuro, fora
  do escopo deste lote.
- Política sobre `auth.Group` legado (`gerente`, `advogado`) — mantidos
  apenas como referência de exibição, conforme comentário em
  `apps/accounts/decorators.py`; sem decisão sobre remoção definitiva.
- Desativação de papéis (`PapelAcesso.ativo=False`) — o kernel já trata
  papel inativo como não contribuinte para a resolução
  (`ids_papeis_ativos` exige `papel.ativo`), mas o efeito administrativo
  completo de desativar um papel em uso não foi auditado além disso.
- Efeitos da remoção de um `UsuarioPapel` — não auditados além da
  resolução em tempo de leitura descrita acima.

## Critérios arquiteturais

- Toda ação sensível deve ser negada no backend quando a resolução
  efetiva de permissão/habilitação não a conceder, independentemente da
  interface.
- Múltiplos papéis de um mesmo usuário devem ser resolvidos por união,
  como já implementado em `apps/accounts/permissoes.py`.
- Uma regra individual (`PermissaoUsuario`/`HabilitacaoUsuario`) deve
  ser respeitada como precedente sobre papel/grupo, como já implementado.
- Um usuário sem papel, sem grupo técnico e sem regra individual não
  deve ganhar acesso indevido — confirmado pelo comportamento de negação
  padrão (`origem="nenhuma"`) quando nenhuma das condições anteriores se
  aplica.
- O fallback legado de `auth.Group` não deve sobrepor regras dinâmicas
  — confirmado: o fallback só é consultado quando o usuário não possui
  nenhum `UsuarioPapel`.
- Cargo profissional e equipe não devem conceder acesso automaticamente
  — confirmado: nem `PerfilUsuario.cargo` nem `Equipe`/`MembroEquipe`
  são consultados por `permissao_efetiva()`/`habilitacao_efetiva()`.
- A resolução de autorização deve possuir testes automatizados — os
  testes de `apps/accounts/tests/` cobrem extensivamente a resolução do
  kernel; a cobertura de views operacionais fora de `apps/accounts` e
  `apps/configuracoes` não foi confirmada além dos testes de fumaça
  (`_SmokeBase` em `apps/accounts/tests/test_interacoes_kernel.py`),
  que verificam apenas ausência de erro HTTP 500, não a correção da
  autorização.

## Referências

- [overview.md](overview.md)
- [data-scope.md](data-scope.md)
- [../product/glossary.md](../product/glossary.md)
- [../product/modules/configuracoes.md](../product/modules/configuracoes.md)
- [../product/modules/equipes.md](../product/modules/equipes.md)
- [../architecture/multitenancy.md](../architecture/multitenancy.md)
