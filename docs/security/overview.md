---
title: Visão geral de segurança
status: canonical
owner: security
last_reviewed: 2026-08-13
---

# Visão geral de segurança

## Objetivo

Este documento define, para o Breno - LawSystem:

- as fronteiras de segurança do sistema — o que é plataforma SaaS
  compartilhada, o que é escritório (tenant) e o que são objetos internos
  de um escritório;
- a distinção entre **isolamento entre tenants** (schema PostgreSQL) e
  **autorização intra-tenant** (o que um usuário pode fazer dentro do
  próprio escritório) — os dois nunca devem ser tratados como a mesma
  garantia;
- o princípio de que o **backend é a autoridade** de segurança — a
  interface pode orientar a experiência do usuário, mas nunca substitui
  uma verificação no servidor;
- a relação entre autenticação, resolução do tenant, autorização de
  módulo, nível de acesso técnico atual, habilitação funcional,
  autorização da ação, escopo de dados, autorização sobre objeto
  específico e integridade da operação — camadas distintas, que não
  devem ser confundidas entre si, detalhadas em
  [authorization-model.md](authorization-model.md) e
  [data-scope.md](data-scope.md);
- a distinção, em cada afirmação, entre **estado constatado no código**
  e **direção canônica** pretendida pela documentação de produto e
  arquitetura.

Este documento, [authorization-model.md](authorization-model.md) e
[data-scope.md](data-scope.md) formam o Lote 4B1 da reorganização
documental do repositório. Eles não substituem a matriz técnica
definitiva por módulo, que é
[authorization-matrix.md](authorization-matrix.md) (Lote 4B2).

## Fronteiras de segurança

### Plataforma SaaS

- Vive no schema público (`SHARED_APPS`, em `config/settings/base.py`).
- Inclui `apps.saas_tenants` (`Escritorio`, `Dominio`,
  `ConfiguracaoVisual`) e `apps.saas_billing` (`Plano`, `Assinatura`).
- O **Platform Admin** é o operador administrativo desta camada, fora do
  escopo de um tenant específico, conforme
  [../governance/terminology-policy.md](../governance/terminology-policy.md).
  Nenhum papel, view ou decorator específico de "Platform Admin" foi
  identificado na inspeção realizada; a administração do schema público
  hoje é acessível pelo Django Admin padrão (`django.contrib.admin`, em
  `SHARED_APPS`), sem mecanismo de autorização dedicado além do
  superusuário Django.
- Este documento não atribui ao Platform Admin acesso automático aos
  dados jurídicos operacionais de um tenant. Nenhuma decisão explícita
  desse tipo foi encontrada nas fontes canônicas lidas, e o isolamento de
  schema, por padrão, não concede esse acesso.

### Escritório

- Vive no schema de cada tenant (`TENANT_APPS`, em
  `config/settings/base.py`).
- O **Administrador do escritório** é a autoridade administrativa máxima
  dentro do tenant — modelada por `PerfilUsuario.is_admin_escritorio`,
  em `apps/accounts/models.py`, e verificada por
  `usuario_admin_escritorio()`, em `apps/accounts/decorators.py`. É
  distinto de Platform Admin e de superusuário técnico do Django, ver
  [authorization-model.md](authorization-model.md).
- Demais usuários do escritório têm seu alcance determinado pela
  combinação de autorização de módulo, nível de acesso técnico atual,
  habilitação funcional, autorização da ação e escopo de dados descrita
  neste lote — não por uma concessão automática.

### Objetos internos

Registros que pertencem a um escritório e cuja exposição deve respeitar
autorização e escopo, conforme constatado em
`apps/*/models.py` e detalhado em [data-scope.md](data-scope.md):

- cliente (`apps.clientes.Cliente`);
- processo (`apps.processos.Processo`, com `MovimentacaoProcessual` e
  `ParteProcesso`);
- tarefa (`apps.tarefas.Tarefa`);
- compromisso (`apps.agenda.Compromisso`);
- lançamento financeiro e custa judicial (`apps.financeiro.LancamentoFinanceiro`,
  `apps.financeiro.CustaJudicial`);
- conversa e mensagem (`apps.chat.Conversa`, `apps.chat.Mensagem`);
- modelo de peça (`apps.modelos.ModeloPeca`);
- arquivo — avatar de usuário e identidade visual do escritório são os
  únicos campos de upload confirmados na inspeção realizada
  (`PerfilUsuario.avatar`, em `apps/accounts/models.py`;
  `ConfiguracaoVisual.logo/favicon/imagem_fundo_login`, em
  `apps/saas_tenants/models.py`); nenhum model de `apps.clientes`,
  `apps.processos`, `apps.tarefas`, `apps.agenda`, `apps.financeiro`,
  `apps.chat` ou `apps.modelos` possui `FileField`/`ImageField` para
  documentos ou anexos na inspeção realizada.

## Camadas de controle

O acesso a um dado ou ação passa, conceitualmente, pelas seguintes
camadas. Nenhuma camada substitui a seguinte: passar por uma camada
prova apenas que essa camada foi satisfeita, não que as camadas
posteriores também foram.

1. **Autenticação** — o usuário é quem afirma ser. Constatado via
   `django.contrib.auth` e, nas views operacionais lidas nesta auditoria
   (`apps/clientes`, `apps/processos`, `apps/tarefas`, `apps/agenda`,
   `apps/financeiro`, `apps/dashboard`, `apps/chat`, `apps/modelos`,
   `apps/laboratorio`), o decorator `@login_required` em toda função de
   view. Em `apps/configuracoes/views.py`, algumas views usam
   `@login_required` (`index`, `editar_perfil`) e outras usam
   `@requer_admin_escritorio` (ver camada 3) — não os dois decorators
   simultaneamente. `apps/accounts/views.py::login_view`/`logout_view`
   não usam nenhum dos dois decorators, por serem as próprias views de
   entrada/saída de sessão. Ver a classificação completa em
   [authorization-model.md](authorization-model.md).
2. **Resolução do tenant** — a requisição é associada ao schema
   PostgreSQL correto. Constatado via
   `django_tenants.middleware.main.TenantMainMiddleware`, primeiro
   middleware em `config/settings/base.py`. Detalhado em
   [../architecture/multitenancy.md](../architecture/multitenancy.md).
3. **Autorização de módulo** — o usuário pode abrir este módulo
   (Processos, Clientes, Financeiro etc.)? No kernel dinâmico, está
   relacionada principalmente ao campo `ativo` de
   `PermissaoPapel`/`PermissaoUsuario`, resolvido por
   `tem_permissao_modulo()`, em `apps/accounts/permissoes.py`. Em
   `apps/configuracoes/views.py`, um controle diferente e mais simples —
   o decorator `@requer_admin_escritorio` — decide acesso a um conjunto
   de views administrativas por ser ou não Administrador do escritório,
   sem consultar `PermissaoPapel`/`PermissaoUsuario`. Ver
   [authorization-model.md](authorization-model.md).
4. **Nível de acesso técnico atual** — o campo `nivel` da mesma linha de
   `PermissaoPapel`/`PermissaoUsuario` (valores como `somente_seus`,
   `todos`, `solicitacoes`, `dados`, conforme o módulo). É uma
   classificação técnica hoje resolvida por
   `permissao_efetiva()`/`nivel_acesso_modulo()`, em
   `apps/accounts/permissoes.py`, mas seus valores misturam
   preocupações de escopo, visibilidade e modalidade de acesso que ainda
   não foram decompostas. Este documento não chama esse campo de
   "permissão de ação" nem o trata como prova de que escopo de dados já
   está aplicado — ver camada 7. A decomposição definitiva desse campo
   depende da futura matriz de autorização e da implementação efetiva
   de escopo, ambas ainda não criadas/aplicadas.
5. **Habilitação funcional** — dentro do módulo liberado, um item
   específico de funcionalidade está habilitado (criar processo, editar
   cliente, atribuir tarefa a outros, etc.)? Modelada por
   `HabilitacaoPapel`/`HabilitacaoUsuario` e resolvida por
   `tem_habilitacao()`, em `apps/accounts/permissoes.py`. A habilitação
   pode contribuir para autorizar uma ação, mas não substitui a
   autorização de módulo, o escopo de dados, a autorização sobre objeto
   nem a validação da operação.
6. **Autorização da ação** — a decisão final no backend sobre executar
   uma operação concreta (criar, editar, arquivar, excluir, pagar,
   reatribuir, adicionar participante, etc.). Esta auditoria não
   identificou, no código lido, uma entidade autônoma e completa de
   "permissão de ação": algumas ações aparecem como itens de
   `HabilitacaoPapel`/`HabilitacaoUsuario` (camada 5, por exemplo
   `processos_criar`, `processos_editar`, `tarefas_atribuir_outros`),
   enquanto outras (por exemplo, arquivar/reabrir processo, marcar
   lançamento como pago, concluir/cancelar/excluir tarefa ou
   compromisso) dependem apenas do decorator `@login_required` e do
   método HTTP (`if request.method == "POST"`), sem checagem de
   habilitação específica identificada. Este documento não presume uma
   modelagem de "autorização da ação" que o código não possui.
7. **Escopo de dados** — quais registros específicos, dentro de um
   módulo já autorizado, o usuário efetivamente alcança? Depende de
   filtrar o `QuerySet` por responsável, equipe ou vínculo equivalente.
   O campo `nivel` (camada 4) não é, por si, prova de que esse escopo já
   está aplicado — ver [data-scope.md](data-scope.md).
8. **Autorização sobre objeto** — ao acessar, editar ou excluir um
   registro identificado por `pk`/`id`, o objeto solicitado é confirmado
   como executável, já carregado a partir de um `QuerySet` autorizado
   pela camada 7? Não basta a existência do objeto no tenant correto.
9. **Integridade da operação** — a operação preserva vínculos válidos
   entre entidades (por exemplo, um processo pertencente ao cliente
   esperado) e não pode ser manipulada por um `POST` alterado no
   navegador.

## Princípios canônicos

Os princípios abaixo são direção canônica, sustentada por
[../product/vision.md](../product/vision.md) e pelas especificações de
módulo lidas neste lote. Nenhum deles é afirmado aqui como já
implementado de forma completa — o estado constatado é registrado na
seção seguinte e em [authorization-model.md](authorization-model.md) e
[data-scope.md](data-scope.md).

- **Deny by default** como direção — ausência de concessão explícita
  deve significar ausência de acesso.
- **Backend como autoridade** — toda verificação de acesso relevante
  deve poder ser reproduzida no servidor, independente da interface.
- **Menor privilégio** — um usuário recebe apenas o necessário para sua
  função.
- **Isolamento entre tenants** — dados operacionais de um escritório não
  podem ser alcançados por outro escritório.
- **Autorização intra-tenant** — dentro do mesmo escritório, o acesso
  entre usuários também precisa de controle; isolamento de schema não
  resolve esta camada.
- **Escopo aplicado aos `QuerySet`s** — a restrição de dados deve ocorrer
  na consulta que produz a lista ou o objeto, não apenas na apresentação.
- **Objeto carregado dentro do escopo autorizado** — a busca por
  `pk`/`id` deve, ela mesma, já estar restrita ao escopo do usuário.
- **Mutações revalidadas no servidor** — toda alteração (`POST`) deve
  revalidar autorização e integridade, mesmo que a interface já tenha
  restringido as opções apresentadas.
- **Interface não concede autorização** — ocultar ou exibir um elemento
  visual nunca substitui a verificação equivalente no backend.
- **Logs e auditoria para mudanças sensíveis** — alterações de papel,
  permissão, habilitação e dados financeiros deveriam ser rastreáveis.
- **IA não amplia escopo** — uma resposta ou sugestão de IA nunca
  concede acesso além do que o usuário já teria diretamente, conforme
  [../product/modules/inteligencia-artificial.md](../product/modules/inteligencia-artificial.md).
- **Arquivos e anexos exigem autorização equivalente ao registro pai** —
  acessar um arquivo vinculado a um cliente ou processo deveria exigir a
  mesma autorização que acessar o registro em si.

## Estado atual e direção

| Categoria | Constatação ou direção | Evidência |
| --- | --- | --- |
| Isolamento entre tenants | Constatado no código | `TenantMainMiddleware` como primeiro middleware; `SHARED_APPS`/`TENANT_APPS` separados em `config/settings/base.py`; nenhuma `ForeignKey` cruzando schemas identificada — ver [../architecture/multitenancy.md](../architecture/multitenancy.md) |
| Autenticação | Constatado no código | `@login_required` presente em toda view de `apps/clientes/views.py`, `apps/processos/views.py`, `apps/tarefas/views.py`, `apps/agenda/views.py`, `apps/financeiro/views.py`, `apps/dashboard/views.py`, `apps/chat/views.py`, `apps/modelos/views.py` e `apps/laboratorio/views.py`; em `apps/configuracoes/views.py`, apenas `index` e `editar_perfil` usam `@login_required` — as demais views usam `@requer_admin_escritorio` (que também trata usuário anônimo, mas é um decorator distinto); `apps/accounts/views.py::login_view`/`logout_view` não usam nenhum dos dois |
| Kernel de autorização de módulo, nível técnico e habilitação | Constatado no código | `PapelAcesso`, `UsuarioPapel`, `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`, `HabilitacaoUsuario` em `apps/accounts/models.py`; resolução em `apps/accounts/permissoes.py` (`permissao_efetiva`, `habilitacao_efetiva`); tela de configuração em `apps/configuracoes/views.py::permissoes` |
| Aplicação do kernel de módulo/nível/habilitação às views operacionais | Lacuna constatada | `tem_permissao_modulo`/`tem_habilitacao`/`permissao_efetiva`/`habilitacao_efetiva` não foram encontrados em nenhuma view de `apps/clientes`, `apps/processos`, `apps/tarefas`, `apps/agenda`, `apps/financeiro`, `apps/dashboard`, `apps/chat`, `apps/modelos`, `apps/laboratorio` ou `apps/configuracoes` — apenas em `apps/accounts/permissoes.py` e nos testes de `apps/accounts/tests/` |
| Administrador do escritório | Constatado no código | `PerfilUsuario.is_admin_escritorio` e `usuario_admin_escritorio()`, em `apps/accounts/decorators.py`, checam exclusivamente essa flag combinada com `is_active`; não há, no código atual, atalho por `is_superuser` ou por grupo `administrador_escritorio` |
| Backend como autoridade | Direção canônica, parcialmente contrariada pelo estado constatado | Registrada em todas as especificações de módulo lidas ("autorização e escopo de dados devem ser aplicados no backend"); módulos operacionais hoje não aplicam essa verificação além de `@login_required` |
| Escopo de dados aplicado a QuerySets | Lacuna constatada | Ver [data-scope.md](data-scope.md) — helpers de equipe existem em `apps/accounts/escopo.py`, mas o próprio módulo declara "ainda não aplicam filtros nos módulos operacionais" |
| Autorização sobre objeto específico | Lacuna constatada | `get_object_or_404(Model, pk=pk)` sem cláusula adicional de posse/escopo em `apps/clientes/views.py`, `apps/processos/views.py`, `apps/tarefas/views.py`, `apps/agenda/views.py`, `apps/financeiro/views.py`, `apps/modelos/views.py` |
| Interface reflete autorização | Lacuna constatada | `templates/components/sidebar.html` exibe todos os módulos a qualquer usuário autenticado, sem condicionar a `tem_permissao_modulo`; apenas `templates/configuracoes/index.html` oculta dois botões administrativos com base em `usuario_e_admin_escritorio` |
| Arquivos e anexos | Não decidido / lacuna constatada | Nenhum model de objeto interno (cliente, processo, tarefa, etc.) possui campo de upload; os únicos uploads confirmados são `PerfilUsuario.avatar` e os campos de `ConfiguracaoVisual`, sem checagem de autorização dedicada além de `@login_required`/`@requer_admin_escritorio` das views que os expõem |
| IA jurídica e escopo | Evolução planejada | Ainda não implementada; pré-requisitos definidos em [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md) e [../product/modules/inteligencia-artificial.md](../product/modules/inteligencia-artificial.md) |

## Principais lacunas constatadas

Os itens abaixo são sustentados diretamente pela leitura do código nesta
auditoria, não por inferência:

- **Views operacionais protegidas apenas por `@login_required`.**
  `apps/clientes/views.py`, `apps/processos/views.py`,
  `apps/tarefas/views.py`, `apps/agenda/views.py`,
  `apps/financeiro/views.py`, `apps/dashboard/views.py`,
  `apps/chat/views.py`, `apps/modelos/views.py` e
  `apps/laboratorio/views.py` usam exclusivamente
  `@login_required`; nenhuma chamada a `tem_permissao_modulo()` ou
  `tem_habilitacao()` foi encontrada nesses arquivos.
- **Kernel de permissões e habilitações existente sem aplicação
  sistemática.** O kernel dinâmico (`PapelAcesso`, `UsuarioPapel`,
  `PermissaoPapel`, `PermissaoUsuario`, `HabilitacaoPapel`,
  `HabilitacaoUsuario`) é resolvido corretamente por
  `apps/accounts/permissoes.py` e coberto por testes extensivos em
  `apps/accounts/tests/`, mas nenhuma view fora de `apps/accounts` e
  `apps/configuracoes` o consulta.
- **Busca de objeto por ID sem filtragem de escopo, confirmada.** Em
  `apps/clientes/views.py` (`detalhe`, `editar`, `desativar`,
  `reativar`), `apps/processos/views.py` (`detalhe`, `editar`,
  `arquivar`, `reabrir`, `adicionar_movimentacao`, `adicionar_parte`),
  `apps/tarefas/views.py` (`editar`, `concluir`, `reabrir`, `iniciar`,
  `excluir`), `apps/agenda/views.py` (`editar`, `concluir`, `cancelar`,
  `reabrir`, `excluir`) e `apps/financeiro/views.py`
  (`editar_lancamento`, `marcar_pago`, `cancelar_lancamento`,
  `reabrir_lancamento`, `excluir_lancamento`) e
  `apps/modelos/views.py` (`detalhe`, `editar`), o padrão constatado é
  `get_object_or_404(Model, pk=pk, ...)`, por vezes combinado com uma
  condição de estado do próprio registro (por exemplo, `ativo=True` em
  `apps/clientes/views.py::detalhe`/`editar`), mas sem nenhuma condição
  adicional de posse, responsável ou equipe. Nas rotas inspecionadas, um
  usuário autenticado do tenant pode carregar por identificador
  registros existentes no schema ativo que satisfaçam as condições
  adicionais da consulta, sem filtro constatado de responsabilidade,
  equipe ou escopo — inclusive em `apps/financeiro/views.py`. As views
  de mutação (`editar`, `concluir`, `cancelar`, `arquivar`, etc.) ainda
  exigem `request.method == "POST"` e, quando aplicável, um formulário
  válido antes de alterar o registro; isso restringe o método e a forma
  da requisição, mas não restringe quem pode fazer a requisição sobre
  qual registro. Este documento usa "risco de autorização por
  objeto/IDOR intra-tenant" apenas para os fluxos efetivamente
  inspecionados acima, não como generalização para o restante do
  sistema, e não usa o ambiente de produção como critério para
  classificar esse padrão de código — apenas registra que a auditoria
  não avaliou controles fora do código (rede, proxy, WAF) que possam
  existir em produção.
- **Autorização baseada somente na interface, quando confirmada.**
  `templates/components/sidebar.html` não condiciona nenhum item de
  módulo a `tem_permissao_modulo`, exibindo todos os módulos a qualquer
  usuário autenticado independentemente da permissão de módulo
  configurada em `apps/configuracoes/views.py::permissoes`.
- **Fallback de `auth.Group` como caminho de resolução ativo.**
  `permissao_efetiva()`/`habilitacao_efetiva()`, em
  `apps/accounts/permissoes.py`, usam `tipo_conta_usuario()` (baseado em
  `auth.Group` "limitado"/"financeiro") como caminho de resolução quando
  o usuário não possui nenhum `UsuarioPapel` — ver
  [authorization-model.md](authorization-model.md) para a condição exata
  desse fallback.
- **Campo `nivel` (nível de acesso técnico atual) resolvido, mas não
  consumido como filtro de dados.** `nivel_acesso_modulo()`, em
  `apps/accounts/permissoes.py`, não foi encontrado em uso em nenhuma
  view fora de `apps/accounts` — o valor de `nivel` é configurável na
  tela de permissões, mas nenhuma consulta de `apps/clientes`,
  `apps/processos`, `apps/tarefas`, `apps/agenda` ou `apps/financeiro`
  o lê para restringir resultados.
- **Arquivos servidos sem checagem de autorização dedicada, em
  desenvolvimento.** `config/urls.py` expõe `MEDIA_URL` via
  `django.conf.urls.static.static()` quando `settings.DEBUG` é
  verdadeiro, sem view intermediária de autorização. Este documento não
  avalia a configuração de produção além do que está em
  `config/settings/production.py`.

## Não objetivos

- Este documento não é um threat model completo.
- Não é a matriz técnica definitiva de papéis, permissões, habilitações
  e escopo por módulo — essa matriz é
  [authorization-matrix.md](authorization-matrix.md).
- Não define política de senhas além do que o Django já aplica por
  padrão.
- Não define infraestrutura de produção.
- Não substitui testes de segurança automatizados ou manuais.
- Não corrige nenhuma view, model, formulário ou template.

## Referências

- [../architecture/overview.md](../architecture/overview.md)
- [../architecture/multitenancy.md](../architecture/multitenancy.md)
- [authorization-model.md](authorization-model.md)
- [data-scope.md](data-scope.md)
- [../product/vision.md](../product/vision.md)
- [../product/glossary.md](../product/glossary.md)
- [../governance/terminology-policy.md](../governance/terminology-policy.md)
