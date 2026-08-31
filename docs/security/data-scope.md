---
title: Escopo de dados
status: canonical
owner: security
last_reviewed: 2026-08-31
---

# Escopo de dados

## Objetivo

Este documento explica, para o Breno - LawSystem:

- quais registros específicos um usuário pode alcançar, dentro de um
  módulo ao qual ele já tem autorização de acesso;
- a diferença entre autorização de módulo (o módulo está aberto?) e
  escopo de dados (quais registros dentro dele são alcançáveis?),
  conforme [authorization-model.md](authorization-model.md);
- como o escopo deveria se aplicar a consultas (`QuerySet`) e a objetos
  individuais carregados por `pk`/`id`;
- a relação entre escopo, equipe, responsabilidade e vínculo processual.

Este documento não define a regra final de escopo por módulo — isso é
tratado em [authorization-matrix.md](authorization-matrix.md), na
coluna "Escopo necessário" de cada operação, quando já existir decisão
aprovada para o módulo em questão. Aqui são registrados apenas o que
está constatado no código e a direção funcional já registrada nas
especificações de módulo.

## Conceito de escopo

- Ter acesso a um módulo não significa ter acesso a todos os registros
  desse módulo — autorização de módulo e escopo de dados são camadas
  distintas, conforme [authorization-model.md](authorization-model.md)
  e [../product/glossary.md](../product/glossary.md).
- O escopo deveria restringir o `QuerySet` que produz uma listagem —
  filtrar depois de carregar todos os registros, ou apenas na
  apresentação, não é escopo aplicado.
- Um objeto específico (detalhe, edição, exclusão) deveria ser carregado
  já dentro do `QuerySet` autorizado, não buscado livremente por
  `pk`/`id` e validado depois.
- A validação de escopo deveria ocorrer também em atualização e exclusão
  (`update`/`delete`), não apenas na listagem.
- Um `POST` manipulado (por exemplo, um `pk` de outro registro digitado
  diretamente na requisição) deveria ser rejeitado pelo servidor.
- IDs previsíveis ou sequenciais não deveriam, por si, conceder acesso.
- Escopo de dados nunca atravessa tenant — o isolamento de schema
  garante essa fronteira antes mesmo de qualquer regra de escopo
  intra-tenant ser avaliada, conforme
  [../architecture/multitenancy.md](../architecture/multitenancy.md).

## Escopo constatado no código

- `apps/accounts/escopo.py` define helpers de consulta de equipes
  (`equipes_do_usuario`, `equipes_gerenciadas_pelo_usuario`,
  `usuario_gerencia_equipe`, `ids_equipes_do_usuario`,
  `ids_equipes_gerenciadas_pelo_usuario`, `equipes_descendentes`) e
  constantes de escopo (`ESCOPO_TUDO`, `ESCOPO_EQUIPES_GERENCIADAS`,
  `ESCOPO_EQUIPE`, `ESCOPO_PROPRIOS_ITENS`, `ESCOPO_NENHUM`). O
  docstring do próprio arquivo declara: "Estes helpers ainda não
  aplicam filtros nos módulos operacionais. Eles apenas expõem
  consultas de equipes para uso futuro."
- Na inspeção realizada, apenas uma função deste arquivo é consumida
  fora dele: `equipe_padrao_para_usuario()`, usada em
  `apps/processos/views.py::novo` exclusivamente para pré-preencher a
  `equipe` de um `Processo` recém-criado quando o usuário pertence a
  exatamente uma equipe ativa. Ela não filtra nenhuma leitura.
  `equipes_descendentes`, `equipes_gerenciadas_pelo_usuario`,
  `usuario_gerencia_equipe` e as demais funções de `escopo.py` não
  foram encontradas em uso em nenhuma view de `apps/`.
- O campo `nivel` de `PermissaoPapel`/`PermissaoUsuario` — aqui chamado
  de nível de acesso técnico atual, conforme
  [authorization-model.md](authorization-model.md) — assume valores como
  `somente_seus`/`todos` para Processos, Clientes, Tarefas, Modelos,
  Painel e Agenda, e `solicitacoes`/`dados` para Financeiro. Esses
  valores sugerem uma distinção de escopo. Clientes e Processos já leem
  `nivel_acesso_modulo()` para filtrar `QuerySet`s; nos demais módulos o
  campo ainda não prova escopo aplicado. A decomposição definitiva desse
  campo entre escopo, visibilidade e modalidade de acesso depende de
  [authorization-matrix.md](authorization-matrix.md) e da implementação
  efetiva de escopo descrita neste documento.
- Regras para administrador: em Clientes e Processos, o Administrador do
  escritório alcança qualquer registro do tenant, tanto para leitura
  quanto para mutação. Nos demais módulos operacionais, nenhuma regra de
  escopo é aplicada a nenhum usuário.
- Regras para gerente ou para advogado/usuário limitado: não
  encontradas em nenhuma view operacional; `MembroEquipe.eh_gerente`
  não é lido por `apps/clientes`, `apps/processos`, `apps/tarefas`,
  `apps/agenda`, `apps/financeiro` ou `apps/dashboard`.
- Vínculos por responsável: os models `Cliente.responsavel`,
  `Processo.responsavel`, `Tarefa.responsavel`,
  `Compromisso.responsavel` e `LancamentoFinanceiro.responsavel`
  existem. Em Cliente e Processo o vínculo é obrigatório e usa
  `on_delete=PROTECT`; nos demais permanece anulável. São preenchidos na
  criação (diretamente em `apps/clientes/views.py::novo`,
  `apps/processos/views.py::novo` e
  `apps/tarefas/views.py::nova`; condicionalmente, apenas quando vazio,
  em `apps/agenda/views.py::form_compromisso` e
  `apps/financeiro/views.py::form_lancamento`/`editar_lancamento`).
  Cliente e Processo já usam o vínculo como filtro de escopo; os demais
  módulos ainda não.
- Vínculos por equipe: apenas `Processo.equipe` existe como campo no
  modelo (`ForeignKey` para `accounts.Equipe`, `null=True`,
  `blank=True`). `Tarefa`, `Compromisso`, `LancamentoFinanceiro` e
  `CustaJudicial` não possuem campo de equipe na inspeção realizada.
- Fallback quando não há equipe: `equipe_padrao_para_usuario()` retorna
  `None` quando o usuário é administrador do escritório, quando não
  está autenticado, ou quando pertence a zero ou a duas ou mais equipes
  ativas — nesse caso, o campo `Processo.equipe` permanece vazio na
  criação, sem nenhum efeito adicional constatado sobre leitura.

## Aplicação por módulo

| Módulo | Relações que podem formar escopo | Aplicação constatada | Direção canônica |
| --- | --- | --- | --- |
| Clientes | `Cliente.responsavel` (FK `auth.User`, obrigatório) | Aplicada ([WI-0002](../delivery/work/WI-0002-escopo-responsabilidade-clientes.md)) — leitura (`lista`/`detalhe`/`inativos`) filtra pelo escopo efetivo (`somente_seus`/`todos`) via `?escopo=`; mutação (`editar`/`desativar`/`reativar`) usa `QuerySet` distinto, restrito ao Administrador ou a `responsavel == request.user`, independente do escopo de leitura — ver [authorization-matrix.md#clientes](authorization-matrix.md#clientes) | [../product/modules/clientes.md](../product/modules/clientes.md): "um usuário com atuação restrita a processos sob sua responsabilidade não deveria alcançar pastas de clientes fora desse escopo" — satisfeito |
| Processos | `Processo.responsavel` (FK obrigatório para `auth.User`), `Processo.equipe` (FK opcional para `accounts.Equipe`) | Aplicada (WI-0005) — leitura (`lista`/`arquivados`/`detalhe`) usa `_processos_no_escopo` com `somente_seus`/`todos`; mutações usam `_processos_mutaveis`, restrito ao Administrador ou a `responsavel == request.user`, inclusive partes, movimentações e ambos os lados de apensos. Equipe só é pré-preenchida e não concede acesso | [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md): escopo exclusivamente por responsável nesta versão — satisfeito |
| Tarefas | `Tarefa.responsavel` (FK `auth.User`); sem campo de equipe no model | Nenhuma — `apps/tarefas/views.py::quadro`/`lista` ordenam mas não filtram por `responsavel`; `editar`/`concluir`/`reabrir`/`iniciar`/`excluir` usam `get_object_or_404(Tarefa, pk=pk)` sem condição adicional | [PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md) / [../product/modules/tarefas.md](../product/modules/tarefas.md): Administrador vê tudo; usuário com habilitação de gestão vê a equipe ou escopo autorizado; usuário comum vê apenas tarefas atribuídas a ele ou criadas por ele — a própria especificação registra que "a aplicação exata do escopo de visibilidade... depende do trabalho de permissões ainda não formalizado" |
| Agenda | `Compromisso.responsavel` (FK `auth.User`), `Compromisso.participantes` (M2M `auth.User`) | Nenhuma — `apps/agenda/views.py::index` filtra apenas por data/status (`hoje`, `proximos_7`, `vencidos`, `todos`), nunca por `responsavel`/`participantes`; `editar`/`concluir`/`cancelar`/`reabrir`/`excluir` usam `get_object_or_404(Compromisso, pk=pk)` sem condição adicional | [../product/modules/agenda.md](../product/modules/agenda.md): acesso "conforme papel de acesso, habilitação, vínculo com o registro e escopo de dados aplicados" |
| Financeiro | `LancamentoFinanceiro.responsavel` (FK `auth.User`); sem campo de equipe no model; `CustaJudicial` sem campo de responsável ou equipe | Nenhuma — `apps/financeiro/views.py::index` filtra apenas por status/tipo/período, nunca por `responsavel`; os totais (`a_receber`, `a_pagar`, `recebido_mes`, `pago_mes`) são agregados sobre todo o tenant; `editar_lancamento`/`marcar_pago`/`cancelar_lancamento`/`reabrir_lancamento`/`excluir_lancamento` usam `get_object_or_404(LancamentoFinanceiro, pk=pk)` sem condição adicional | [../product/modules/financeiro.md](../product/modules/financeiro.md): "usuários sem acesso ao caixa geral possuem visão limitada, restrita às suas próprias solicitações de pagamento e reembolso"; o nível de acesso técnico atual (`nivel`) `solicitacoes`/`dados`, já modelado em `PermissaoPapel` para o módulo `financeiro`, é o valor mais próximo dessa distinção no kernel, mas não é lido por `apps/financeiro/views.py` nem constitui, por si, escopo aplicado |
| Dashboard | Agrega `Cliente`, `Processo`, `Tarefa`, `Compromisso`, `LancamentoFinanceiro` sem relação de escopo própria | Nenhuma — `apps/dashboard/views.py::painel` calcula todos os contadores e listas (`clientes_ativos`, `processos_ativos`, `tarefas_pendentes`, `compromissos_proximos`, `a_receber`, `a_pagar`, `tarefas_dashboard`, `compromissos_dashboard`, `financeiro_dashboard`) sobre o tenant inteiro, sem filtrar por usuário | [../product/modules/dashboard.md](../product/modules/dashboard.md): "cada indicador respeita a autorização e o escopo de dados do usuário que o consulta"; "cards financeiros só aparecem a usuários autorizados" |
| Chat | `Conversa.participantes` (M2M `auth.User`) | Parcial, apenas por natureza do dado — a única sala implementada é `Conversa.TIPO_GLOBAL`, obtida por `get_or_create` em `apps/chat/views.py::global_sala` e destinada a todo o tenant; a view não verifica `request.user` contra `sala.participantes` antes de listar ou permitir postagem, o que é consistente com a sala ser deliberadamente compartilhada por todo o tenant nesta versão. Conversas individuais e em grupo, que exigiriam checar `participantes`, não possuem view de criação identificada | [../product/modules/chat.md](../product/modules/chat.md): "um usuário acessa somente as conversas das quais participa, ou que seu escopo administrativo autorize" |
| Modelos | `ModeloPeca.criado_por` (FK `auth.User`) | A listagem já não filtra por autoria, coerente com o acervo institucional; falta autorização de módulo nas views, e o kernel ainda mantém `somente_seus`/`todos` apesar de essa dimensão ter sido removida do alvo | [../product/modules/modelos.md](../product/modules/modelos.md): usuário autorizado ao módulo acessa todo o acervo do tenant; `criado_por` não forma escopo |
| Configurações | Sem relação de escopo de dados própria — `ConfiguracaoEscritorio` é um registro único por tenant (`get_or_create(pk=1)`) | `editar_perfil`, em `apps/configuracoes/views.py`, opera sobre `PerfilUsuario.objects.get_or_create(user=request.user)` — usa diretamente `request.user`, não um `pk` vindo da URL, o que estrutural­mente impede que um usuário edite o perfil de outro por essa view. As views administrativas (`novo_usuario`, `equipes` e demais) são protegidas por `@requer_admin_escritorio`, um controle de papel, não de escopo de dados | [../product/modules/configuracoes.md](../product/modules/configuracoes.md): "a administração de usuários... é restrita a papéis de acesso autorizados para administração do escritório" |

## Integridade cliente-processo

- Direção canônica, registrada em
  [../product/modules/clientes.md](../product/modules/clientes.md): "o
  vínculo entre cliente e processo deve ser íntegro: o servidor deve
  rejeitar uma associação inconsistente, mesmo que a requisição tenha
  sido manipulada no navegador"; e "ao selecionar um cliente..., os
  seletores dependentes de processo não podem oferecer processos
  incompatíveis com o cliente selecionado."
- Estado constatado: `apps/tarefas/forms.py::TarefaForm` declara os
  campos `cliente` (`Cliente.objects.filter(ativo=True)`) e `processo`
  (`Processo.objects.select_related("cliente").exclude(status="arquivado")`)
  como `ModelChoiceField`s independentes — o `queryset` de `processo`
  não é restrito pelo `cliente` selecionado. O mesmo padrão de campos
  independentes é confirmado em `apps/agenda/forms.py::CompromissoForm`:
  `cliente` (`Cliente.objects.filter(ativo=True)`) e `processo`
  (`Processo.objects.select_related("cliente").exclude(status="arquivado")`)
  também são declarados como `ModelChoiceField`s independentes, sem que
  o `queryset` de um dependa da seleção do outro.
- As views de `apps/tarefas/views.py::nova`/`editar` e
  `apps/agenda/views.py::form_compromisso`/`editar` **preenchem**
  automaticamente `cliente` a partir de `processo.cliente` apenas
  quando `cliente` está vazio (`if not tarefa.cliente and
  tarefa.processo and tarefa.processo.cliente: tarefa.cliente =
  tarefa.processo.cliente`) — isso não é uma rejeição de combinação
  inconsistente: se um `POST` enviar um `cliente` e um `processo`
  pertencente a outro cliente simultaneamente, nenhuma validação
  encontrada nesta auditoria rejeita essa combinação.
- `apps/processos/forms.py::ProcessoForm` associa `Processo` a um único
  `cliente` (campo obrigatório); não há, neste nível, ambiguidade de
  integridade cliente-processo a validar além da existência do cliente.
- O modelo implementado de Partes ainda segue PDR-0001/PDR-0011 e diverge
  do alvo simplificado de
  [PDR-0013](../product/decisions/PDR-0013-partes-processo-modelo-simplificado.md).
  PDR-0013 deixou em aberto se `Processo.cliente` deve gerar
  automaticamente uma Parte correspondente; este documento não resolve
  essa decisão.

## Escopo por equipe

- Equipe é referência organizacional, não mecanismo de autorização em
  si, conforme [../product/modules/equipes.md](../product/modules/equipes.md)
  e [authorization-model.md](authorization-model.md).
- Gerente de equipe (`MembroEquipe.eh_gerente=True`) não recebe escopo
  global automaticamente — constatado: nenhum caminho de
  `apps/accounts/permissoes.py` consulta `eh_gerente`.
- Escopo por equipe depende de autorização e regra explícita ainda não
  aplicada — os helpers de `apps/accounts/escopo.py` existem, mas não
  são consumidos por nenhuma view operacional, conforme já registrado
  acima.
- Múltiplas equipes por usuário: o model `MembroEquipe` permite
  múltiplos vínculos por usuário (a `UniqueConstraint` é por par
  `usuario`+`equipe`, não por `usuario`); `equipes_do_usuario()` já
  retorna um `QuerySet` com potencialmente mais de uma equipe. A regra
  de produto sobre múltiplas equipes, porém, continua em aberto
  conforme [../product/modules/equipes.md](../product/modules/equipes.md).
- Hierarquia entre equipes: `Equipe.equipe_pai` (auto-`ForeignKey`,
  `related_name="subequipes"`) já existe no model, e
  `apps/accounts/escopo.py::equipes_descendentes()` já implementa
  travessia recursiva de subequipes. Nenhuma chamada a
  `equipes_descendentes()` foi encontrada fora de sua própria definição
  nesta auditoria. Isso é uma divergência entre o código (que já
  contém a estrutura técnica de hierarquia) e
  [../product/modules/equipes.md](../product/modules/equipes.md) (que
  registra "se existe hierarquia entre equipes" como ponto sem decisão
  aprovada) — este documento registra a divergência sem resolvê-la.

## Escopo em agregações

- Direção canônica: o Dashboard deve agregar apenas dados visíveis ao
  usuário que consulta, conforme
  [../product/modules/dashboard.md](../product/modules/dashboard.md).
- Estado constatado: `apps/dashboard/views.py::painel` calcula todos os
  indicadores (contagens e somas) sobre o tenant inteiro, sem qualquer
  filtro por usuário — ver tabela acima.
- Um card financeiro oculto na interface não impede vazamento por
  endpoint: nenhum template de dashboard foi inspecionado linha a linha
  nesta auditoria para exibição condicional de cards, mas, como a view
  já calcula os valores agregados de `LancamentoFinanceiro` de forma
  incondicional para todo usuário autenticado, uma eventual ocultação
  apenas no template não eliminaria o cálculo nem uma futura exposição
  por outro meio (por exemplo, uma view de API).
- Drill-down a partir de um indicador deveria usar o mesmo escopo do
  indicador — não aplicável ainda: nenhum fluxo de drill-down dedicado
  foi identificado em `apps/dashboard/views.py` além dos links padrão
  de navegação para as listas de cada módulo, que por sua vez também
  não aplicam escopo, conforme a tabela acima.

## Arquivos e anexos

- Direção canônica: acesso a um arquivo deveria exigir autorização
  equivalente à do registro pai, conforme
  [overview.md](overview.md) e
  [../architecture/multitenancy.md](../architecture/multitenancy.md).
- Estado constatado: nenhum model de objeto interno (`Cliente`,
  `Processo`, `MovimentacaoProcessual`, `ParteProcesso`, `Tarefa`,
  `Compromisso`, `LancamentoFinanceiro`, `CustaJudicial`, `Mensagem`,
  `ModeloPeca`) possui campo de upload (`FileField`/`ImageField`) na
  inspeção realizada. Os únicos campos de upload confirmados no
  repositório são `PerfilUsuario.avatar`
  (`apps/accounts/models.py`) e `ConfiguracaoVisual.logo`/`favicon`/
  `imagem_fundo_login` (`apps/saas_tenants/models.py`) — nenhum deles é
  um "documento" ou "anexo" de cliente, processo ou outro objeto
  interno, portanto o cenário de "arquivo vinculado a um registro pai"
  não tem, hoje, nenhum caso constatado no código para auditar.
- Armazenamento ou caminho não concede acesso — princípio canônico;
  não há, no código lido, nenhuma view que sirva arquivo por caminho
  direto além do mecanismo padrão do Django (`MEDIA_URL`/`MEDIA_ROOT`,
  servido via `django.conf.urls.static.static()` somente quando
  `settings.DEBUG` é verdadeiro, conforme `config/urls.py`).
- URL previsível não concede acesso — princípio canônico; não avaliado
  como risco concreto nesta auditoria porque nenhum anexo de objeto
  interno existe para ser exposto por URL previsível.
- A estratégia física de segregação de arquivos por tenant continua em
  aberto, conforme
  [../architecture/multitenancy.md](../architecture/multitenancy.md)
  ("Não há, no código lido, uma estratégia consolidada de segregação de
  arquivos por tenant").

## IA e escopo

- A IA jurídica ainda não está implementada — `apps/laboratorio/views.py`
  apenas renderiza um template estático, conforme
  [../architecture/overview.md](../architecture/overview.md) e
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md).
- Direção canônica, registrada em
  [../product/modules/inteligencia-artificial.md](../product/modules/inteligencia-artificial.md):
  a IA só deve acessar objetos já autorizados ao usuário; o contexto de
  um processo não amplia esse acesso; uma resposta ou sugestão de IA
  não concede autorização adicional; uma sugestão de IA (por exemplo,
  de honorário) exige confirmação humana antes de gerar um lançamento
  definitivo.
- Como apenas Clientes e Processos aplicam escopo hoje (ver tabela
  acima), uma futura indexação para IA jurídica precisará carregar
  tenant e reutilizar as regras de autorização/escopo de cada módulo;
  não pode presumir que os demais módulos já ofereçam essa fronteira.

## Lacunas constatadas

- Fora de Clientes (WI-0002) e Processos (WI-0005), nenhum módulo
  operacional (`apps/tarefas`, `apps/agenda`,
  `apps/financeiro`, `apps/dashboard`, `apps/modelos`) filtra listagens
  por `responsavel`, `equipe`, `participantes` ou `criado_por`.
- Fora de Clientes e Processos, nenhum desses módulos carrega objetos de
  detalhe/edição/ação dentro de um `QuerySet` já restrito por escopo;
  todos usam `get_object_or_404(Model, pk=pk, ...)` com, no máximo, uma
  condição de estado (`ativo=True`, `status=...`), nunca uma condição
  de posse.
- Os helpers de escopo por equipe (`apps/accounts/escopo.py`) e o nível
  de acesso técnico atual (`nivel`, resolvido por
  `nivel_acesso_modulo()`) já existem. Clientes e Processos leem
  `nivel`; os demais módulos ainda não. O campo isolado não deve ser
  tratado como prova de escopo aplicado, ver "Escopo constatado no
  código" acima.
- Nenhuma validação de integridade cliente-processo rejeita, no
  backend, uma combinação inconsistente enviada por `POST` em
  `apps/tarefas` — apenas preenche automaticamente o campo vazio.
- O Dashboard agrega dados de todo o tenant sem filtro por usuário.
- A infraestrutura técnica de hierarquia de equipes
  (`Equipe.equipe_pai`, `equipes_descendentes()`) já existe no código,
  mas a decisão de produto sobre hierarquia entre equipes continua em
  aberto e nenhuma view a utiliza.

## Pontos em aberto

- Regra final de escopo nos módulos ainda pendentes (Tarefas, Agenda,
  Financeiro, Dashboard, Chat e Configurações).
- Múltiplas equipes por usuário — suportado estruturalmente pelo model,
  sem regra de produto aprovada.
- Geração automática de Parte para `Processo.cliente` — ponto em aberto
  de PDR-0013.
- Objetos compartilhados entre usuários ou equipes sem um único
  responsável.
- Delegação temporária de escopo.
- Acesso substituto durante ausência de um usuário responsável.
- Escopo histórico de um registro após reatribuição (por exemplo, uma
  `Tarefa` reatribuída — `apps/tarefas/views.py::editar` já preserva
  `responsavel_original`/`status_original` no formulário, mas isso não
  é, por si, uma política de escopo histórico).
- Escopo para relatórios exportados — nenhuma exportação foi
  identificada no código lido.

## Critérios arquiteturais

- Um `QuerySet` de listagem deveria já nascer filtrado pelo escopo do
  usuário, não filtrado posteriormente ou apenas na apresentação —
  constatado em Clientes (WI-0002) e Processos (WI-0005); ainda não
  constatado nos demais módulos operacionais.
- Detalhe, edição e exclusão deveriam reutilizar o mesmo escopo da
  listagem — constatado em Clientes e Processos, com `QuerySet`s de
  leitura e de mutação distintos por desenho; nos demais módulos, ainda
  usam `get_object_or_404` sem condição de posse.
- Uma tentativa de alterar o identificador de um objeto (`pk`) fora do
  escopo deveria ser rejeitada pelo servidor — constatado em Clientes e
  Processos (404); ainda não constatado nos demais módulos.
- Uma agregação (Dashboard, totais financeiros) deveria respeitar o
  mesmo escopo de um usuário comum — ainda não constatado.
- Um arquivo vinculado a um registro pai deveria exigir a mesma
  validação de escopo que o registro — não há, hoje, caso concreto de
  anexo de objeto interno para validar essa regra.
- A IA, quando implementada, deveria respeitar o escopo já aplicado aos
  módulos que consulta — depende de o escopo estar de fato aplicado
  nesses módulos primeiro, conforme
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md).
- Deveria existir teste negativo entre usuários do mesmo tenant (um
  usuário não deveria alcançar um registro de outro usuário fora de seu
  escopo) — constatado em Clientes e Processos; ainda ausente nos demais
  módulos operacionais.
- Deveria existir teste negativo entre tenants — não encontrado na
  inspeção realizada; ver
  [../architecture/multitenancy.md](../architecture/multitenancy.md).

## Referências

- [overview.md](overview.md)
- [authorization-model.md](authorization-model.md)
- [../architecture/multitenancy.md](../architecture/multitenancy.md)
- [../product/modules/clientes.md](../product/modules/clientes.md)
- [../product/modules/processos.md](../product/modules/processos.md)
- [../product/modules/tarefas.md](../product/modules/tarefas.md)
- [../product/modules/agenda.md](../product/modules/agenda.md)
- [../product/modules/financeiro.md](../product/modules/financeiro.md)
- [../product/modules/dashboard.md](../product/modules/dashboard.md)
- [../product/modules/chat.md](../product/modules/chat.md)
- [../product/modules/modelos.md](../product/modules/modelos.md)
- [../product/modules/inteligencia-artificial.md](../product/modules/inteligencia-artificial.md)
