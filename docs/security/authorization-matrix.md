---
title: Matriz de autorização
status: canonical
owner: security
last_reviewed: 2026-08-19
---

# Matriz de autorização

## Objetivo

Este documento define o comportamento canônico esperado para, em cada
módulo e operação do Breno - LawSystem:

- entrada no módulo;
- execução de operações;
- alcance dos registros (escopo);
- autorização sobre objetos específicos;
- integridade da mutação;
- implementação futura;
- testes futuros.

A matriz é o **alvo canônico**. Ela não prova enforcement atual — o
estado real de aplicação, view por view, permanece documentado em
[authorization-model.md](authorization-model.md) e
[data-scope.md](data-scope.md), que esta matriz não substitui nem
duplica integralmente. Onde este documento descreve comportamento já
constatado no código, ele referencia essas duas fontes em vez de
repetir a evidência completa.

Este é o Lote 4B2 da reorganização documental do repositório,
subsequente ao Lote 4B1 (`overview.md`, `authorization-model.md`,
`data-scope.md`). A matriz não presume que o código atual já aplica
qualquer uma das regras aqui descritas como direção canônica.

## Como ler a matriz

Cada linha da matriz detalhada descreve uma operação de um módulo
segundo estas dimensões:

- **módulo** — domínio funcional ao qual a operação pertence (título da
  subseção);
- **operação** — ação concreta que um usuário pode tentar executar;
- **autorização de módulo** — o módulo está aberto para o usuário?
- **nível técnico atual** — valor de `nivel` associado à mesma linha de
  permissão do módulo, quando aplicável;
- **habilitação funcional** — item específico habilitado dentro do
  módulo, quando existir no kernel atual;
- **escopo necessário** — quais registros o usuário deveria alcançar
  para esta operação, segundo a direção funcional;
- **autorização sobre objeto** — validação do objeto específico
  carregado por `pk`/`id`;
- **integridade** — validação de vínculos e transições de estado da
  operação;
- **estado constatado** — síntese, apenas para esta operação, do que foi
  observado diretamente no código: rota existente ou inexistente,
  decorator atual, helper de permissão/habilitação atualmente
  consultado ou não, `QuerySet` atual, forma como o objeto é carregado,
  validação atualmente existente, ou registro de que a operação ainda
  não está implementada;
- **alvo canônico** — síntese, apenas para esta operação, da exigência
  aprovada pela documentação de produto, arquitetura ou segurança:
  autorização esperada, escopo necessário, integridade necessária e
  confirmação humana, quando aplicável;
- **classificação** — ver [seção 8](#classificação-das-linhas), coluna
  obrigatória em cada tabela;
- **observação ou pendência** — referências a OPEN-001/OPEN-002, ausência
  de habilitação, mapeamento de `nivel` ainda não formalizado, modelagem
  futura, divergência entre código e produto, ou requisito ainda não
  decidido.

As colunas "estado constatado" e "alvo canônico" existem justamente para
que nenhuma célula precise misturar, na mesma frase, o que o código faz
hoje e o que a documentação exige. As demais colunas (autorização de
módulo, nível técnico, habilitação, escopo necessário, autorização sobre
objeto, integridade) registram valores e mecanismos específicos de cada
camada; "estado constatado" e "alvo canônico" registram a síntese
comparativa dessa operação como um todo.

Fora da tabela, cada subseção de módulo traz observações e decisões
pendentes relevantes que não cabem em uma célula.

### Autorização de módulo

Concessão efetiva de entrada no módulo. No kernel atual, corresponde ao
campo `ativo` de `PermissaoPapel`/`PermissaoUsuario`, resolvido por
`tem_permissao_modulo()`, em `apps/accounts/permissoes.py`. Passar por
esta camada não prova que a operação concreta, o escopo ou o objeto
estejam corretos.

### Nível técnico atual

Valor atual de `nivel` (por exemplo, `somente_seus`, `todos`,
`solicitacoes`, `dados`). Não deve ser tratado isoladamente como
autorização da ação ou como escopo implementado. Conforme
[authorization-model.md](authorization-model.md) e
[data-scope.md](data-scope.md), nenhuma view operacional lê
`nivel_acesso_modulo()` para filtrar um `QuerySet`.

### Habilitação funcional

Item específico do kernel atual (`HabilitacaoPapel`/`HabilitacaoUsuario`,
resolvido por `tem_habilitacao()`), quando existir. Este documento não
inventa habilitação para toda operação. Quando uma operação não possuir
habilitação correspondente, a célula registra "sem habilitação
específica no kernel atual".

### Autorização da ação

Decisão final do backend sobre executar a operação concreta. Ela
combina autorização de módulo, habilitação funcional, escopo de dados e
autorização sobre objeto — não corresponde a uma tabela única constatada
no código. Nenhuma coluna própria representa "autorização da ação"
isoladamente; ela é o resultado composto das demais colunas, conforme
[authorization-model.md](authorization-model.md).

### Escopo

Registros alcançáveis pelo usuário dentro de um módulo já autorizado.
A coluna "escopo necessário" registra a direção funcional (por
responsável, equipe, participante, etc.), não uma implementação
constatada, salvo quando expressamente indicado.

### Autorização sobre objeto

Validação de que o objeto carregado por `pk`/`id` pertence ao escopo
autorizado do usuário, e não apenas ao tenant correto.

### Integridade

Validação dos vínculos (por exemplo, cliente-processo) e das transições
de estado válidas para a operação, incluindo rejeição de um `POST`
manipulado.

## Regras globais

Aplicáveis a todos os módulos, como direção canônica:

- a requisição deve resolver o tenant correto antes de qualquer
  autorização intra-tenant, conforme
  [../architecture/multitenancy.md](../architecture/multitenancy.md);
- o usuário deve estar ativo (`is_active=True`);
- o módulo correspondente deve estar autorizado antes de processar a
  operação;
- a habilitação funcional deve ser exigida quando a decisão canônica
  vigente do módulo determinar o enforcement da chave existente no
  kernel; para Processos, o PDR-0010 mantém `processos_criar`,
  `processos_editar` e `processos_andamento_adicionar` no kernel sem
  exigi-las nesta versão — decisão deliberada, não lacuna;
- o escopo deve ser aplicado ao `QuerySet` antes da busca do objeto por
  `pk`/`id`, não depois;
- o método HTTP deve ser adequado à operação (leitura via `GET`,
  mutação via `POST`);
- toda mutação deve ser revalidada no servidor, mesmo que a interface já
  tenha restringido as opções apresentadas;
- uma transição de estado deve ser válida para o estado atual do
  registro;
- relacionamentos entre entidades (cliente, processo, responsável,
  equipe) devem pertencer ao mesmo tenant;
- um `POST` manipulado (por exemplo, um `pk` de outro registro ou um
  `responsavel` diferente do autorizado) deve ser rejeitado pelo
  servidor;
- a interface nunca substitui a verificação equivalente no backend;
- a ausência de concessão explícita deve significar negação (deny by
  default);
- alterações sensíveis (papel, permissão, habilitação, dados
  financeiros) deveriam gerar log futuro, ainda não implementado.

## Modelo dinâmico de papéis

Esta matriz não atribui operações diretamente a nomes fixos de papéis
(como "Advogado" ou "Gerente"). Papéis de acesso são dinâmicos,
configuráveis pelo Administrador do escritório via `PapelAcesso`, e um
usuário pode possuir múltiplos papéis simultâneos, agregados por união.
Regras individuais (`PermissaoUsuario`/`HabilitacaoUsuario`) podem
sobrescrever a resolução por papel para um usuário específico.

Para cada operação desta matriz, o backend resolve a autorização de
módulo e habilitação na seguinte ordem, conforme
[authorization-model.md](authorization-model.md). Esta ordem descreve o
**estado constatado** do kernel — não é, por si só, a definição do
alcance funcional do Administrador do escritório, tratada separadamente
logo abaixo.

1. **Administrador do escritório** — `usuario_admin_escritorio()`
   (`PerfilUsuario.is_admin_escritorio=True` combinado com
   `is_active=True`) é avaliado antes de qualquer `PermissaoUsuario`
   individual.
2. **Regra individual** (`PermissaoUsuario`/`HabilitacaoUsuario`), que
   substitui a resolução por papel para aquele usuário, módulo (e item,
   no caso de habilitação) — avaliada apenas quando o passo 1 não
   concede acesso.
3. **União de papéis ativos** (`UsuarioPapel` com `PermissaoPapel`
   agregada pelo maior nível entre os papéis concedentes).
4. **Fallback legado** de `auth.Group` (`tipo_conta_usuario()`), somente
   quando o usuário não possui nenhum `UsuarioPapel`. Este caminho é
   **comportamento atual legado, não direção canônica** — não deve ser
   ampliado nem tratado como modelo de papéis fixo, e deve ser tratado
   como candidato a descontinuação quando a migração para `PapelAcesso`
   estiver completa.
5. **Negação padrão**, quando nenhuma das condições anteriores concede
   acesso.

### Administrador do escritório: estado constatado versus direção canônica

#### Estado constatado

O kernel atual, em `apps/accounts/permissoes.py`:

- avalia `usuario_admin_escritorio()` antes de consultar qualquer
  `PermissaoUsuario` individual;
- quando esse caminho é verdadeiro, retorna acesso ao módulo com o
  maior nível técnico configurado para aquele módulo em
  `NIVEIS_POR_MODULO` (por exemplo, `todos` para Processos, `dados`
  para Financeiro);
- não permite que uma linha de `PermissaoUsuario` com `ativo=False`
  bloqueie esse caminho — uma regra individual negativa não tem efeito
  sobre um usuário que satisfaça `usuario_admin_escritorio()`.

Este é o comportamento resolvido pelo kernel de permissão de módulo e
nível técnico. Ele não determina, por si só, escopo de dados,
autorização sobre um objeto específico, nem acesso a conteúdo de
terceiros (por exemplo, conversas privadas de chat ou documentos de
outro usuário) — nenhuma dessas camadas foi auditada como dependente do
mesmo caminho de admissão de módulo.

#### Direção canônica

- Administrador do escritório é a autoridade administrativa máxima
  dentro do tenant, conforme
  [../governance/terminology-policy.md](../governance/terminology-policy.md).
- Sua autorização funcional e seu escopo devem ser definidos, operação
  por operação, por esta matriz — não presumidos de forma genérica a
  partir do bypass de módulo constatado acima.
- Autoridade administrativa não implica automaticamente acesso
  irrestrito a todo objeto jurídico, conversa privada, documento ou
  conteúdo de usuário; onde as fontes canônicas afirmam explicitamente
  o alcance do Administrador sobre um domínio específico (por exemplo,
  "o Administrador do escritório deve poder acessar e gerenciar a pasta
  de qualquer cliente do tenant", em
  [clientes.md](../product/modules/clientes.md)), esta matriz preserva
  essa regra específica nas tabelas correspondentes.
- Exceções de acesso do Administrador precisam ser explícitas,
  reutilizáveis e auditáveis — não um efeito colateral de um decorator
  ou de uma ordem de avaliação de permissão de módulo.
- Platform Admin continua sendo conceito distinto, sem acesso jurídico
  automático a dados operacionais de um tenant.

Gerente de equipe (`MembroEquipe.eh_gerente=True`) não é um papel de
acesso e não passa por nenhum dos passos acima — nenhum caminho do
kernel consulta `eh_gerente`, conforme
[data-scope.md](data-scope.md). Gerente não possui acesso global
automaticamente; um eventual alcance de gerente sobre dados de sua
equipe depende de papel, habilitação e escopo aplicados no backend,
ainda não implementados. Cargo profissional (`PerfilUsuario.cargo`) e
equipe (`Equipe`/`MembroEquipe`) não concedem autorização por si —
nenhum dos dois é consultado por `permissao_efetiva()`/
`habilitacao_efetiva()`. Platform Admin não recebe acesso jurídico
automático a dados operacionais de um tenant — nenhum mecanismo de
autorização dedicado ao Platform Admin foi encontrado no código,
conforme [overview.md](overview.md). Superuser técnico do Django
(`is_superuser`) não é verificado por `usuario_admin_escritorio()` no
código atual e não deve ser transformado em papel de produto.

## Resumo dos módulos

Chaves e níveis confirmados em `apps/accounts/permissoes_constants.py`.

| Módulo funcional | Chave técnica atual | Níveis atuais | Quantidade de habilitações atuais | Estado do enforcement |
| --- | --- | --- | --- | --- |
| Dashboard / Painel | `painel` | `somente_seus`, `todos` | 0 | Não aplicado — view usa apenas `@login_required` |
| Clientes | `clientes` | `somente_seus`, `todos` | 2 (`clientes_criar`, `clientes_editar`) | Não aplicado nas views |
| Processos | `processos` | `somente_seus`, `todos` | 5 (`processos_criar`, `processos_editar`, `processos_andamento_adicionar`, `processos_usar_ia`, `processos_usar_laboratorio`) | Autorização binária de módulo aplicada nas nove views; habilitações granulares não exigidas nesta versão por PDR-0010; escopo/responsabilidade pendentes para o WI-0005 |
| Tarefas | `tarefas` | `somente_seus`, `todos` | 1 (`tarefas_atribuir_outros`) | Não aplicado; adicionalmente, não há rota ou campo de formulário que exponha a atribuição a outro usuário |
| Agenda | `agenda` | `somente_seus`, `todos` | 1 (`agenda_criar_para_outros`) | Não aplicado; o campo de formulário existe, mas a habilitação não é consultada |
| Financeiro | `financeiro` | `solicitacoes`, `dados` | 0 | Não aplicado; módulo não possui nenhuma habilitação no kernel atual |
| Chat | `chat` | `""` (sem nível) | 0 | Não aplicado — view usa apenas `@login_required` |
| Modelos | `modelos` | `somente_seus`, `todos` | 2 (`modelos_criar`, `modelos_editar_estilo`) | Não aplicado nas views |
| Gerir (Configurações/administração) | `gerir` | `""` (sem nível) | 4 (`gerir_criar_usuario`, `gerir_habilitar_usuario_processos`, `gerir_criar_equipe`, `gerir_habilitar_terceiros`) | Parcial — `@requer_admin_escritorio` protege as rotas administrativas por um controle binário de papel, sem consultar `tem_permissao_modulo`/`tem_habilitacao` do módulo `gerir` |
| Inteligência Artificial / Laboratório | Sem chave própria no kernel — as habilitações relacionadas (`processos_usar_ia`, `processos_usar_laboratorio`) vivem sob o módulo `processos`, conforme [../architecture/module-map.md](../architecture/module-map.md) | — (contado em Processos) | (contado em Processos) | Não aplicável — `apps.laboratorio` não consulta nenhuma permissão ou habilitação |

## Matriz detalhada

Todas as tabelas abaixo usam as colunas: Operação, Aut. módulo, Nível
técnico, Habilitação, Escopo necessário, Aut. objeto, Integridade,
Estado constatado, Alvo canônico, Classificação, Observação ou
pendência — definidas em
["Como ler a matriz"](#como-ler-a-matriz). "Aut. módulo" abrevia
autorização de módulo; "Aut. objeto" abrevia autorização sobre objeto.
As colunas "escopo necessário" e "aut. objeto" registram apenas o valor
ou mecanismo relevante daquela camada; "estado constatado" e "alvo
canônico" registram a síntese comparativa da operação como um todo, sem
misturar as duas coisas na mesma frase.

### Dashboard

Rotas auditadas: `apps/dashboard/views.py::painel` (única view,
`@login_required`, sem models próprios — agrega `Cliente`, `Processo`,
`Tarefa`, `Compromisso`, `LancamentoFinanceiro`).

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Visualizar painel | Chave `painel` existe no kernel | `somente_seus`/`todos` definidos para `painel` | Sem habilitação específica no kernel atual (`painel` fora de `MODULO_HABILITACAO_CHOICES`) | Escopo do usuário que consulta, conforme [dashboard.md](../product/modules/dashboard.md) | Não aplicável — não há objeto único por `pk` | Não aplicável a esta operação | Rota `painel` protegida apenas por `@login_required`; `tem_permissao_modulo` não é chamado; `nivel_acesso_modulo` não é lido | Cada indicador deveria respeitar o escopo do usuário que consulta | Lacuna constatada | — |
| Visualizar indicadores (contagens, prazos) | Idem acima | Idem acima | Idem acima | Idem acima | Não aplicável | Não aplicável | View calcula contagens (`Cliente`, `Processo`, `Tarefa`, `Compromisso`) sobre o tenant inteiro, sem filtro por usuário | Indicadores deveriam refletir apenas os registros dentro do escopo do usuário | Lacuna constatada | — |
| Visualizar indicadores financeiros | Idem acima | Idem acima | Idem acima | Cards financeiros restritos a usuários autorizados, conforme [dashboard.md](../product/modules/dashboard.md) | Não aplicável | Não aplicável | `a_receber`/`a_pagar` são calculados incondicionalmente para qualquer usuário autenticado, sem distinção de autorização financeira | Cards financeiros só deveriam aparecer, e ser calculados, para usuários autorizados | Lacuna constatada | — |
| Acessar listas ou drill-downs relacionados | Herda a autorização de módulo do módulo de destino (Clientes, Processos, Tarefas, Agenda, Financeiro) | Herda do módulo de destino | Herda do módulo de destino | Herda do módulo de destino | Herda do módulo de destino | Não aplicável | Nenhum fluxo de drill-down dedicado foi identificado além de links padrão de navegação para as listas de cada módulo | Drill-down deveria usar o mesmo escopo do indicador de origem | Lacuna constatada | Depende de os módulos de destino aplicarem escopo primeiro |

Observações:

- Agregações devem usar o mesmo escopo dos objetos que agregam — hoje
  não usam, porque os módulos de origem também não aplicam escopo.
- Autorização do card não pode depender do template: ocultar um card no
  HTML não impede que o valor já tenha sido calculado incondicionalmente
  pela view, nem impediria uma futura exposição por outro meio.
- Nível técnico atual (`somente_seus`/`todos` de `painel`) não prova
  filtragem aplicada — ver ["Relação com o nível técnico atual"](#relação-com-o-nível-técnico-atual).

### Clientes

Rotas auditadas: `apps/clientes/views.py` (`lista`, `detalhe`, `novo`,
`editar`, `desativar`, `inativos`, `reativar`), todas `@login_required`.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Listar (ativos) | Chave `clientes` no kernel | `somente_seus`/`todos`, definidos para `clientes` | Não se aplica a uma listagem (`clientes_criar`/`clientes_editar` são específicas de criar/editar) | Por `Cliente.responsavel`, conforme [clientes.md](../product/modules/clientes.md) | Não aplicável — listagem, não objeto único | Não aplicável | `lista` não chama `tem_permissao_modulo`; `QuerySet` filtra apenas por `ativo=True`, sem filtro de `responsavel` | Um usuário com atuação restrita não deveria alcançar clientes fora de seu escopo | Lacuna constatada | — |
| Visualizar (detalhe) | Idem | Idem | Sem habilitação específica no kernel atual para "visualizar" | Idem acima | `get_object_or_404(Cliente, pk=pk, ativo=True)` | Não aplicável | Objeto carregado sem condição de posse além de `ativo=True` | Objeto deveria ser carregado já restrito ao escopo do usuário | Lacuna constatada | — |
| Criar | Idem | Idem | `clientes_criar` existe no kernel | Não aplicável à criação em si | Não aplicável | Vínculo `responsavel` preenchido com `request.user` quando ausente no formulário | `apps/clientes/views.py::novo` não chama `tem_habilitacao`; habilitação existente não é consultada | Habilitação deveria ser exigida quando existir chave correspondente no kernel | Lacuna constatada | — |
| Editar | Idem | Idem | `clientes_editar` existe no kernel | Idem ao escopo de leitura acima | `get_object_or_404(Cliente, pk=pk, ativo=True)` | Mutação exige `POST` (via `ClienteForm`) | `apps/clientes/views.py::editar` não chama `tem_habilitacao`; objeto carregado sem condição de posse | Habilitação deveria ser exigida; objeto deveria ser carregado dentro do escopo | Lacuna constatada | — |
| Desativar | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(Cliente, pk=pk, ativo=True)` | `desativar` exige `POST`; muda apenas `ativo=False` | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | Candidata a habilitação futura — ver ["Operações sem habilitação correspondente"](#operações-sem-habilitação-correspondente) |
| Listar inativos | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | Não aplicável | Não aplicável | `inativos` filtra apenas por `ativo=False`, sem filtro de `responsavel` | Idem à listagem de ativos | Lacuna constatada | — |
| Reativar | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(Cliente, pk=pk, ativo=False)` | `reativar` exige `POST` | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | Candidata a habilitação futura |

Observações:

- Integridade com processos vinculados: [clientes.md](../product/modules/clientes.md)
  exige que o servidor rejeite uma associação cliente-processo
  inconsistente. A criação de processo (`ProcessoForm`) associa um
  único cliente obrigatório, sem ambiguidade nesse ponto; a divergência
  relevante de integridade ocorre em Tarefas e Agenda (ver seções
  correspondentes), onde `cliente` e `processo` são campos
  independentes.
- Nenhuma operação de Clientes depende de habilitação item por item no
  código atual, embora `clientes_criar`/`clientes_editar` existam como
  chaves candidatas.

### Processos

Rotas auditadas: `apps/processos/views.py` (`lista`, `detalhe`, `novo`,
`editar`, `arquivados`, `arquivar`, `reabrir`, `adicionar_movimentacao`,
`adicionar_parte`), todas com `@login_required` e checagem inicial de
`tem_permissao_modulo(request.user, "processos")`.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Listar | Chave `processos` no kernel | `somente_seus`/`todos`, definidos para `processos` | Não se aplica a uma listagem | Por `Processo.responsavel`; equipe não participa do escopo aprovado para o WI-0005 | Não aplicável | Não aplicável | `lista` chama `tem_permissao_modulo` antes da consulta; o `QuerySet` ainda não filtra por `responsavel` | Autorização binária de módulo aplicada; na Fase B, escopo de leitura por responsável (`somente_seus`/`todos`) | Constatado no código (módulo) / Evolução planejada (escopo) | `Da equipe` e hierarquia de equipes ficam fora do WI-0005 |
| Visualizar (detalhe) | Idem | Idem | Sem habilitação específica no kernel atual para "visualizar" | Idem acima | `get_object_or_404(Processo, pk=pk)` ainda sem condição de responsabilidade | Não aplicável | `detalhe` chama `tem_permissao_modulo` antes de carregar o objeto; o objeto ainda não é restringido por responsabilidade | Na Fase B, objeto carregado dentro do escopo de leitura por responsável | Constatado no código (módulo) / Evolução planejada (escopo) | — |
| Criar | Idem | Idem | `processos_criar` existe no kernel, sem enforcement nesta versão por PDR-0010 | Não aplicável à criação em si | Não aplicável | `equipe_padrao_para_usuario()` sugere a equipe apenas quando o usuário pertence a exatamente uma equipe ativa | `novo` chama `tem_permissao_modulo` antes da lógica da view e não chama `tem_habilitacao`, conforme PDR-0010 | Módulo autorizado é suficiente nesta versão; responsabilidade obrigatória e elegibilidade pertencem ao WI-0005 | Constatado no código | Habilitação preservada como evolução futura, não lacuna nem bloqueio da Fase A |
| Editar | Idem | Idem | `processos_editar` existe no kernel, sem enforcement nesta versão por PDR-0010 | Por `Processo.responsavel`; `todos` amplia leitura, não mutação | `get_object_or_404(Processo, pk=pk)` ainda sem condição de responsabilidade | Mutação exige `POST` | `editar` chama `tem_permissao_modulo` antes de carregar o objeto e não chama `tem_habilitacao`; a mutação ainda não é restringida por responsabilidade | Na Fase B, não-admin só modifica processo sob sua responsabilidade; Administrador modifica qualquer processo do tenant | Constatado no código (módulo) / Evolução planejada (escopo e responsabilidade) | Habilitação preservada como evolução futura, não lacuna nem bloqueio da Fase A |
| Arquivar | Idem | Idem | Sem habilitação específica no kernel atual | Por `Processo.responsavel`; `todos` não amplia mutação | `get_object_or_404(Processo, pk=pk)` ainda sem condição de responsabilidade | `arquivar` exige `POST`; muda `status` para `arquivado` sem validar transição a partir de qualquer status anterior | `arquivar` chama `tem_permissao_modulo` antes de carregar ou alterar o objeto; responsabilidade e transição ainda não são validadas | Na Fase B, não-admin só modifica processo sob sua responsabilidade; validação de transição pertence à fase de integridade | Constatado no código (módulo) / Evolução planejada (responsabilidade) / Lacuna constatada (transição) | Candidata a habilitação futura |
| Reabrir | Idem | Idem | Sem habilitação específica no kernel atual | Idem à mutação acima | `get_object_or_404(Processo, pk=pk)` ainda sem condição de responsabilidade | `reabrir` exige `POST`; muda `status` para `ativo` sem validar transição | `reabrir` chama `tem_permissao_modulo` antes de carregar ou alterar o objeto; responsabilidade e transição ainda não são validadas | Idem acima | Constatado no código (módulo) / Evolução planejada (responsabilidade) / Lacuna constatada (transição) | Candidata a habilitação futura |
| Adicionar movimentação | Idem | Idem | `processos_andamento_adicionar` existe no kernel, sem enforcement nesta versão por PDR-0010 | Por `Processo.responsavel`; `todos` não amplia mutação | Processo ainda carregado por `get_object_or_404(Processo, pk=pk)` sem condição de responsabilidade | `autor` preenchido com `request.user`; mutação exige `POST` | `adicionar_movimentacao` chama `tem_permissao_modulo` antes de carregar o processo e não chama `tem_habilitacao`; responsabilidade ainda não é validada | Na Fase B, não-admin só adiciona movimentação a processo sob sua responsabilidade | Constatado no código (módulo) / Evolução planejada (responsabilidade) | Habilitação preservada como evolução futura, não lacuna nem bloqueio da Fase A |
| Adicionar participante | Idem | Idem | Sem habilitação específica no kernel atual (não há item dedicado a "parte"/"participante" além de `processos_andamento_adicionar`, que é sobre andamentos) | Por `Processo.responsavel`; `todos` não amplia mutação | Processo ainda carregado por `get_object_or_404(Processo, pk=pk)` sem condição de responsabilidade | Mutação exige `POST`; `ParteProcesso` atual usa um único campo `tipo` (`autor`/`reu`/`terceiro`/`advogado_contrario`) | `adicionar_parte` chama `tem_permissao_modulo` antes de carregar o processo; responsabilidade ainda não é validada e PDR-0001 continua não implementado | Na Fase B, não-admin só modifica processo sob sua responsabilidade; modelagem de participantes permanece na fase de integridade | Constatado no código (módulo) / Evolução planejada (responsabilidade) / Lacuna constatada (modelagem) | Equipe não concede acesso; modelagem de dados pendente não é resolvida pelo WI-0005 |
| Usar Assistente/Laboratório, quando aplicável | `apps.laboratorio` não verifica nenhuma autorização de módulo de processo | Não aplicável — o Laboratório não lê `nivel` de processo | `processos_usar_laboratorio` existe no kernel | Escopo do processo de origem | Não aplicável — não há carregamento de processo na view atual | Não aplicável | `apps/laboratorio/views.py::index` apenas renderiza um template estático; nenhuma habilitação é consultada | Módulo/processo autorizado, escopo do processo e habilitação deveriam ser verificados, conforme [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md) | Evolução planejada | Depende dos pré-requisitos de PDR-0008 |

Observações:

- PDR-0001 exige suportar múltiplos clientes representados, múltiplas
  pessoas por polo, terceiros, Ministério Público e autoridades — a
  modelagem atual (`ParteProcesso.tipo`) não sustenta essas dimensões;
  esta matriz registra a divergência, não a resolve.
- IA condicionada ao PDR-0008: nenhuma operação de IA jurídica está
  implementada; a interface de Assistente/Laboratório não deve ser
  tratada como um produto de IA separado, apenas como a interface
  planejada para a IA jurídica dentro do processo.
- Nenhuma view de Processos consulta `equipes_descendentes()`, apesar de
  `Equipe.equipe_pai` já existir no model — hierarquia de equipes
  continua em aberto, conforme [equipes.md](../product/modules/equipes.md),
  e fica fora do WI-0005.
- Autorização binária por módulo (sem habilitações granulares) é a
  decisão vigente para esta versão de Processos, conforme
  [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md);
  escopo por responsável e responsabilidade obrigatória são direção
  aprovada para o WI-0005. Equipe não concede acesso, não filtra
  Processos e não participa desse escopo; `Da equipe` permanece para
  evolução posterior.

### Tarefas

Rotas auditadas: `apps/tarefas/views.py` (`quadro`, `lista`, `nova`,
`editar`, `concluir`, `reabrir`, `iniciar`, `excluir`), todas
`@login_required`.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Listar / visualizar quadro | Chave `tarefas` no kernel | `somente_seus`/`todos`, definidos para `tarefas` | Não se aplica a uma listagem | Administrador vê tudo; usuário com habilitação de gestão vê equipe/escopo autorizado; usuário comum vê apenas tarefas atribuídas a ele ou criadas por ele, conforme [PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md) | Não aplicável | Não aplicável | `quadro`/`lista` não chamam `tem_permissao_modulo`; `QuerySet` não filtra por `responsavel` em nenhum caso | Visibilidade escalonada por papel, conforme a tabela de PDR-0002 | Lacuna constatada | Não se conclui que gerente possui escopo global — ver ["Modelo dinâmico de papéis"](#modelo-dinâmico-de-papéis) |
| Criar tarefa (para si mesmo) | Idem | Idem | Não se aplica à criação para si mesmo | Não aplicável à criação em si | Não aplicável | `tarefa.responsavel = request.user` sempre, em `nova`; preenchimento automático de `cliente` a partir de `processo.cliente`, sem rejeitar combinação inconsistente enviada por `POST` | `TarefaForm` não expõe campo `responsavel` — toda tarefa nasce atribuída ao criador | Combinação cliente/processo inconsistente deveria ser rejeitada pelo servidor | Lacuna constatada | Integridade cliente-processo, não escopo de criação |
| Atribuir tarefa a outro usuário | Idem | Idem | `tarefas_atribuir_outros` existe no kernel | Escopo do destinatário deveria valer a partir da criação, sem fluxo de aceite, conforme [PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md) | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Não há campo de formulário nem rota que permita escolher um `responsavel` diferente do criador; a operação descrita em PDR-0002 e [tarefas.md](../product/modules/tarefas.md) não está implementada | Delegação direta a outro usuário, conforme PDR-0002 | Evolução planejada | Habilitação já existe no kernel, sem ponto de consumo |
| Visualizar tarefa (individual) | Idem | Idem | Sem habilitação específica no kernel atual para "visualizar" | Tarefas atribuídas ao usuário ou criadas por ele, salvo Administrador/gestão | `get_object_or_404(Tarefa, pk=pk)` | Não aplicável | Objeto carregado sem condição de posse; qualquer usuário autenticado do tenant alcança a tarefa por `pk` | Objeto deveria ser carregado já restrito ao escopo do usuário | Lacuna constatada | — |
| Editar / modificar tarefa | Idem | Idem | Sem habilitação específica no kernel atual para edição geral | Idem acima | `get_object_or_404(Tarefa, pk=pk)` | `responsavel_original`/`status_original` preservados no `POST` de edição; mutação exige `POST` | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | — |
| Iniciar | Idem | Idem | Sem habilitação específica no kernel atual | Idem acima | `get_object_or_404(Tarefa, pk=pk)` | `iniciar` exige `POST`; muda `status` para `em_andamento` sem validar transição a partir do status anterior | Objeto carregado sem condição de posse; transição não validada | Objeto deveria ser carregado dentro do escopo; transição deveria ser validada | Lacuna constatada | — |
| Concluir | Idem | Idem | Sem habilitação específica no kernel atual | Idem acima | `get_object_or_404(Tarefa, pk=pk)` | `concluir` exige `POST`; muda `status` para `concluida` sem validar transição | Idem acima | Idem acima | Lacuna constatada | — |
| Reabrir | Idem | Idem | Sem habilitação específica no kernel atual | Idem acima | `get_object_or_404(Tarefa, pk=pk)` | `reabrir` exige `POST`; muda `status` de volta para `a_fazer` | Idem acima | Idem acima | Lacuna constatada | — |
| Excluir | Idem | Idem | Sem habilitação específica no kernel atual | Idem acima | `get_object_or_404(Tarefa, pk=pk)` | `excluir` exige `POST`; exclusão física (`delete()`), sem soft-delete | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | PDR-0002 não define exclusão física como parte do ciclo de vida da tarefa |

Observações:

- O model `Tarefa` não possui os campos `criador`, `atribuidor`,
  `destinatario_atribuicao` nem `data_atribuicao` exigidos por
  [PDR-0002](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md);
  possui apenas `responsavel`. Esta matriz registra a divergência entre
  o modelo de dados constatado e a decisão de produto aceita, sem
  resolvê-la.
- O status `cancelada`, previsto em PDR-0002, não existe em
  `Tarefa.STATUS_CHOICES` (`a_fazer`, `em_andamento`, `concluida`); em
  seu lugar, existe a operação `excluir`, que não corresponde à mesma
  semântica de PDR-0002.
- Não se conclui, nesta matriz, que gerente de equipe possui escopo
  global sobre tarefas — nenhum caminho do kernel consulta
  `eh_gerente`, conforme ["Modelo dinâmico de papéis"](#modelo-dinâmico-de-papéis).

### Agenda

Rotas auditadas: `apps/agenda/views.py` (`index`, `form_compromisso`,
`editar`, `concluir`, `cancelar`, `reabrir`, `excluir`), todas
`@login_required`.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Listar | Chave `agenda` no kernel | `somente_seus`/`todos`, definidos para `agenda` | Não se aplica a uma listagem | Por `Compromisso.responsavel` ou `participantes`, conforme [agenda.md](../product/modules/agenda.md) | Não aplicável | Não aplicável | `index` não chama `tem_permissao_modulo`; `QuerySet` filtra apenas por data/status (`hoje`, `proximos_7`, `vencidos`, `todos`), nunca por `responsavel`/`participantes` | Escopo por responsável ou participante | Lacuna constatada | — |
| Criar compromisso | Idem | Idem | `agenda_criar_para_outros` existe no kernel | Não aplicável à criação em si | Não aplicável | Preenchimento automático de `cliente` a partir de `processo.cliente` quando ausente | `CompromissoForm` expõe campo `responsavel`; `form_compromisso` não chama `tem_habilitacao` antes de aceitar um responsável diferente do criador | Habilitação deveria ser exigida para atribuir a outro usuário; combinação cliente/processo inconsistente deveria ser rejeitada | Lacuna constatada | — |
| Editar | Idem | Idem | Sem habilitação específica no kernel atual para edição geral | Idem ao escopo de leitura acima | `get_object_or_404(Compromisso, pk=pk)` | `status_original` preservado no `POST`; mutação exige `POST` | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | — |
| Concluir | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(Compromisso, pk=pk)` | `concluir` exige `POST`; muda `status` para `concluido` sem validar transição | Objeto carregado sem condição de posse; transição não validada | Objeto deveria ser carregado dentro do escopo; transição deveria ser validada | Lacuna constatada | — |
| Cancelar | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(Compromisso, pk=pk)` | `cancelar` exige `POST`; muda `status` para `cancelado` sem validar transição | Idem acima | Idem acima | Lacuna constatada | — |
| Reabrir | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(Compromisso, pk=pk)` | `reabrir` exige `POST`; muda `status` para `agendado` | Idem acima | Idem acima | Lacuna constatada | — |
| Excluir | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(Compromisso, pk=pk)` | `excluir` exige `POST`; exclusão física, sem soft-delete | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | — |

Observações:

- Vínculo com cliente e processo: mesmo padrão de Tarefas — `cliente` e
  `processo` são campos independentes em `CompromissoForm`, sem
  validação de que pertencem um ao outro quando ambos são enviados
  explicitamente por `POST`.
- Participantes (`Compromisso.participantes`, M2M) não são lidos por
  nenhuma view para compor escopo — nenhum usuário é filtrado como
  participante em `index`.

### Financeiro

O Financeiro é tratado nesta matriz nas quatro áreas funcionais
distintas exigidas por
[PDR-0003](../product/decisions/PDR-0003-areas-funcionais-financeiro.md).
Todas as áreas compartilham a mesma chave de módulo do kernel
(`financeiro`), que não possui nenhuma habilitação (`ITENS_POR_MODULO["financeiro"] = []`).

#### Financeiro geral

Rotas auditadas: `apps/financeiro/views.py` (`index`, `form_lancamento`,
`editar_lancamento`, `marcar_pago`, `cancelar_lancamento`,
`reabrir_lancamento`, `excluir_lancamento`), todas `@login_required`.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Listar lançamentos | Chave `financeiro` no kernel | `solicitacoes`/`dados`, definidos para `financeiro` | Módulo sem itens em `ITENS_POR_MODULO` | Usuário sem acesso ao caixa geral deveria ter visão limitada, conforme [financeiro.md](../product/modules/financeiro.md) | Não aplicável | Não aplicável | `index` não chama `tem_permissao_modulo`; `nivel_acesso_modulo` não é lido; código não distingue nenhum usuário — todos veem os mesmos lançamentos e totais | Distinção entre acesso pleno ao caixa geral e acesso restrito a solicitações | Lacuna constatada | Mapeamento entre `nivel` (`solicitacoes`/`dados`) e esta distinção ainda não formalizado — ver ["Relação com o nível técnico atual"](#relação-com-o-nível-técnico-atual) |
| Criar | Idem | Idem | Sem habilitação específica no kernel atual | Não aplicável à criação em si | Não aplicável | `responsavel` preenchido com `request.user` quando ausente; `cliente` herdado de `processo.cliente` quando ausente | `form_lancamento` não chama `tem_permissao_modulo` | — | Lacuna constatada | Candidata a habilitação futura |
| Editar | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(LancamentoFinanceiro, pk=pk)` | Mutação exige `POST` | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | — |
| Marcar como pago/recebido | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(LancamentoFinanceiro, pk=pk)` | `marcar_pago` exige `POST`; define `data_pagamento` e muda `status` para `pago`; `LancamentoFinanceiroForm.clean()` exige `data_pagamento` quando `status="pago"` | Objeto carregado sem condição de posse; validação de `data_pagamento` já existe | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | — |
| Cancelar | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(LancamentoFinanceiro, pk=pk)` | `cancelar_lancamento` exige `POST`; muda `status` para `cancelado` sem validar transição | Objeto carregado sem condição de posse; transição não validada | Objeto deveria ser carregado dentro do escopo; transição deveria ser validada | Lacuna constatada | — |
| Reabrir | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(LancamentoFinanceiro, pk=pk)` | `reabrir_lancamento` exige `POST`; muda `status` para `pendente` e limpa `data_pagamento` | Idem acima | Idem acima | Lacuna constatada | — |
| Excluir | Idem | Idem | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | `get_object_or_404(LancamentoFinanceiro, pk=pk)` | `excluir_lancamento` exige `POST`; exclusão física | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | — |
| Visualizar totais (a receber, a pagar, recebido/pago no período) | Idem | Idem | Sem habilitação específica no kernel atual | Indicadores deveriam respeitar o escopo do usuário, conforme [PDR-0004](../product/decisions/PDR-0004-previsto-e-realizado.md) | Não aplicável | Cálculo de "a receber"/"a pagar" segue a fórmula de previsto/realizado de PDR-0004 corretamente | Código agrega sobre o tenant inteiro, incondicionalmente, sem aplicar escopo | Indicadores deveriam refletir apenas o escopo do usuário que consulta | Lacuna constatada | — |

Observações:

- `LancamentoFinanceiro` não possui campo de modalidade (único,
  parcelado, recorrente) exigido por PDR-0003 — todo lançamento hoje é,
  na prática, um lançamento único; ver ["Recorrência"](#recorrência)
  abaixo.
- `LancamentoFinanceiro.CATEGORIA_CHOICES` inclui `"custa_judicial"`
  como categoria comum, apesar de PDR-0003 determinar que custas
  judiciais pertencem a área própria (já existente como model separado
  `CustaJudicial`) — divergência já registrada em
  [../architecture/module-map.md](../architecture/module-map.md), não
  resolvida por esta matriz.

#### Custas judiciais

Rotas auditadas: `apps/financeiro/views.py` (`custas`, `form_custa`).

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Listar | Chave `financeiro` no kernel | `solicitacoes`/`dados`, definidos para `financeiro` | Sem habilitação específica no kernel atual | Saldo por cliente, conforme [PDR-0005](../product/decisions/PDR-0005-custas-por-cliente.md) | Não aplicável | Cálculo do saldo (`créditos depositados − custas pagas pelo escritório`) é feito no backend, em memória, sobre todos os registros de `CustaJudicial`, consistente com a exigência de PDR-0005 de que o cálculo ocorra no backend | `custas` não chama `tem_permissao_modulo`; nenhuma restrição de escopo por usuário constatada na listagem | O cálculo do saldo já é feito no backend, conforme exigido; escopo por usuário não é exigido explicitamente por PDR-0005 | Lacuna constatada | Lacuna refere-se à autorização de módulo, não ao cálculo do saldo, que já está correto |
| Criar | Idem | Idem | Sem habilitação específica no kernel atual | Não aplicável à criação em si | Não aplicável | `CustaJudicialForm.clean_valor()` rejeita valor menor ou igual a zero | `form_custa` não chama `tem_permissao_modulo` | — | Lacuna constatada | Candidata a habilitação futura |
| Editar ou alterar estado, quando a rota existir | Não aplicável — operação não implementada | Não aplicável | Não aplicável | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Nenhuma rota de edição ou transição de estado foi identificada em `apps/financeiro/urls.py` para `CustaJudicial` | Nenhum requisito específico de edição ou transição de estado de `CustaJudicial` foi identificado nas fontes aprovadas ([PDR-0005](../product/decisions/PDR-0005-custas-por-cliente.md) não exige essa operação) | Constatado no código | A ausência da rota não constitui proibição definitiva nem lacuna sem requisito canônico correspondente |
| Vincular cliente | Módulo Financeiro autorizado | `solicitacoes`/`dados` são valores técnicos existentes; nenhum deles prova, sozinho, o direito de selecionar qualquer cliente | Sem habilitação específica no kernel atual | O cliente selecionável deve pertencer ao escopo efetivo do usuário; a regra exata de composição desse escopo no Financeiro ainda não está formalizada por módulo | O cliente enviado pelo formulário deve ser novamente carregado ou validado dentro do `QuerySet` autorizado | Cliente deve pertencer ao tenant ativo; `POST` manipulado com cliente fora do escopo deve ser rejeitado | `CustaJudicialForm` oferece clientes ativos do tenant sem filtro constatado de responsabilidade, equipe ou escopo intra-tenant | Oferecer e aceitar somente clientes dentro do escopo efetivo do usuário | Lacuna constatada | A política exata de escopo financeiro por papel, equipe ou responsabilidade continua pendente; essa pendência não autoriza um `QuerySet` irrestrito |
| Vincular processo | Módulo Financeiro autorizado | `solicitacoes`/`dados` são valores técnicos existentes; nenhum deles prova, sozinho, o direito de selecionar qualquer processo | Sem habilitação específica no kernel atual | O processo selecionável deve pertencer ao escopo efetivo do usuário | O processo deve ser validado dentro do `QuerySet` autorizado | Processo deve pertencer ao tenant; quando cliente e processo forem informados, o processo deve ser compatível com o cliente selecionado; `POST` manipulado deve ser rejeitado | `CustaJudicialForm` oferece processos não arquivados sem filtro constatado de responsabilidade, equipe ou escopo; o `QuerySet` de processos não é restringido pelo cliente selecionado | Processo dentro do escopo do usuário e compatível com o cliente, quando ambos forem informados | Lacuna constatada | A composição exata do escopo financeiro permanece pendente; a exigência mínima de escopo e integridade já é canônica |

Observações:

- A linha "Editar ou alterar estado" registra apenas a ausência da rota
  como fato constatado — nenhuma fonte aprovada (PDR-0005 ou
  [financeiro.md](../product/modules/financeiro.md)) exige que essa
  operação exista, de modo que a ausência não é tratada como lacuna.

#### Solicitações de pagamento e reembolso

Registrado como **direção funcional canônica**, distinguindo do código
atual: [PDR-0006](../product/decisions/PDR-0006-solicitacoes-financeiras.md)
exige que usuários sem acesso ao caixa geral possam solicitar pagamento
e reembolso, com fluxo de referência
`solicitada → em análise → aprovada ou rejeitada → paga`, e que
Administrador do escritório e usuário com habilitação financeira
processem essas solicitações.

Nenhum model, formulário, view ou rota para "Solicitação de pagamento"
ou "Solicitação de reembolso" foi encontrado em `apps/financeiro/` —
`apps/financeiro/models.py` contém apenas `LancamentoFinanceiro` e
`CustaJudicial`. Os níveis técnicos atuais `solicitacoes` e `dados` já
existem no kernel, associados ao módulo `financeiro` em
`PermissaoPapel`/`PermissaoUsuario`, mas o mapeamento definitivo entre
esses valores e as operações abaixo deverá ser formalizado na
implementação da matriz e, quando aplicável, após a resolução de
OPEN-002 — esta matriz não fixa essa associação.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Criar solicitação de pagamento | Módulo `financeiro`; mapeamento a um nível técnico específico não formalizado | Os níveis técnicos `solicitacoes` e `dados` existem no kernel, mas o mapeamento definitivo entre esses valores e esta operação deverá ser formalizado na implementação da matriz e, quando aplicável, após a resolução de OPEN-002 | Sem habilitação específica no kernel atual | O próprio solicitante, conforme [PDR-0006](../product/decisions/PDR-0006-solicitacoes-financeiras.md) | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Nenhum model, view ou rota foi encontrado para esta operação | Usuário sem acesso ao caixa geral deveria conseguir criar a solicitação, sem visualizar receitas/despesas completas | Evolução planejada | Modelagem de Solicitação pendente |
| Criar solicitação de reembolso | Idem | Idem | Idem | Idem | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Idem acima | Idem acima | Evolução planejada | Modelagem de Solicitação pendente |
| Acompanhar status da própria solicitação | Idem | Idem | Idem | O próprio solicitante | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Idem acima | O solicitante deveria conseguir acompanhar o status da própria solicitação, conforme PDR-0006 | Evolução planejada | Modelagem de Solicitação pendente |
| Processar solicitação (analisar/aprovar/rejeitar/pagar) | Módulo `financeiro`; mapeamento a um nível técnico específico não formalizado | Os níveis técnicos `solicitacoes` e `dados` existem no kernel, mas o mapeamento definitivo entre esses valores e esta operação deverá ser formalizado na implementação da matriz e, quando aplicável, após a resolução de OPEN-002 | Sem habilitação específica no kernel atual | Administrador do escritório e usuário com habilitação financeira, conforme PDR-0006 | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Nenhum model, view ou rota foi encontrado para esta operação | Administrador do escritório e usuário com habilitação financeira deveriam processar a solicitação | Evolução planejada | Bloqueado por OPEN-002 (etapas de aprovação) |

Esta matriz não resolve [OPEN-002](../product/open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras)
(etapas finais de aprovação) — o número e a semântica exatos dos
estados intermediários permanecem em aberto.

#### Honorários

Registrado como **direção funcional canônica**, distinguindo do código
atual: [PDR-0007](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md)
exige cadastro manual com campos próprios (tipo, valor estimado, valor
efetivo, processo, cliente, data prevista, data recebida, status,
observações), anterior a qualquer funcionalidade de IA.

Nenhum model `Honorario` foi encontrado. `LancamentoFinanceiro.CATEGORIA_CHOICES`
inclui `"honorario"` e `"exito"` como categorias de um lançamento
financeiro geral, sem os campos separados de valor estimado/valor
efetivo e data prevista/data recebida exigidos por PDR-0007.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cadastrar honorário manualmente | Módulo `financeiro` | Sem mapeamento canônico de nível técnico específico nas fontes aprovadas | Sem habilitação específica no kernel atual | Não decidido em detalhe pelas fontes lidas | Não aplicável | Não aplicável além do já registrado em "Financeiro geral" | Hoje é apenas um `LancamentoFinanceiro` de categoria `honorario`, sujeito às mesmas regras de "Financeiro geral" acima; sem campos de valor estimado/valor efetivo separados | Cadastro manual com campos próprios (tipo, valor estimado, valor efetivo, processo, cliente, datas, status, observações), conforme [PDR-0007](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md) | Evolução planejada | Modelagem de Honorário como entidade própria pendente |
| Acompanhar valor estimado versus valor efetivo | Módulo `financeiro` | Sem mapeamento canônico de nível técnico específico nas fontes aprovadas | Sem habilitação específica no kernel atual | Não aplicável a esta operação | Não aplicável — campos não existem no model atual | Não aplicável — operação não implementada | Nenhum campo de valor estimado ou valor efetivo existe em `LancamentoFinanceiro` | Campos separados exigidos por [PDR-0007](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md) | Evolução planejada | Modelagem de Honorário pendente |
| Sugestão de honorário por IA (futura) | Módulo `financeiro`/`processos`, condicionado a [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md) | Sem mapeamento canônico de nível técnico específico nas fontes aprovadas | `processos_usar_ia` (módulo `processos`) existe no kernel | Escopo do processo de origem; sugestão de IA não amplia escopo | Não aplicável — operação não implementada | Não aplicável — operação não implementada | `processos_usar_ia` não é consultada por nenhuma view; IA não implementada | Confirmação humana exigida antes de gerar lançamento definitivo, conforme [inteligencia-artificial.md](../product/modules/inteligencia-artificial.md) | Evolução planejada | Depende dos pré-requisitos de PDR-0008 |

#### Recorrência

Esta matriz não resolve [OPEN-001](../product/open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão)
(periodicidades da primeira versão). O código atual não implementa
nenhuma modalidade de lançamento parcelado ou recorrente:
`LancamentoFinanceiro` não possui campos de quantidade de parcelas,
periodicidade, data final, duração ou vínculo de origem entre
ocorrências — todo lançamento constatado no código corresponde, na
prática, à modalidade "único" de
[PDR-0003](../product/decisions/PDR-0003-areas-funcionais-financeiro.md).
A criação, edição e cancelamento de uma futura ocorrência recorrente ou
parcelada herdariam a mesma autorização de módulo, nível e ausência de
habilitação já registradas em "Financeiro geral" — esta matriz não
antecipa uma modelagem própria para elas.

Billing SaaS mantido separado, conforme
[PDR-0003](../product/decisions/PDR-0003-areas-funcionais-financeiro.md):
nenhuma assinatura cria lançamento automático no Financeiro do tenant —
confirmado pela ausência de qualquer referência a `saas_billing`,
`Plano` ou `Assinatura` em `apps/financeiro/`. Uma integração futura
exige novo PDR e não é antecipada por esta matriz.

### Chat

Rotas auditadas: `apps/chat/views.py` (`lista`, `detalhe`,
`global_sala`), todas `@login_required`.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Acessar lista | Chave `chat` no kernel | `""` (módulo sem nível) | Sem habilitação específica no kernel atual (`chat` fora de `MODULO_HABILITACAO_CHOICES`) | Não aplicável — `lista` apenas redireciona | Não aplicável | Não aplicável | `lista` não chama `tem_permissao_modulo`; apenas redireciona para a sala global, sem listar conversas | Um usuário deveria acessar apenas as conversas de que participa | Lacuna constatada | — |
| Acessar conversa (por `pk`) | Idem | Idem | Idem | Participação na conversa, conforme [chat.md](../product/modules/chat.md) | Não aplicável — `pk` recebido nunca é usado para carregar uma `Conversa` | Não aplicável | `detalhe(request, pk)` ignora completamente o `pk` recebido e sempre redireciona para a sala global — nenhuma conversa individual é de fato carregada ou verificada | Acesso a uma conversa específica deveria verificar participação | Lacuna constatada | Conversas individuais/grupo não existem no código — ver linha "Acessar conversa individual ou em grupo" abaixo |
| Participar da sala global | Idem | Idem | Idem | Sala global é deliberadamente compartilhada por todo o tenant, conforme [chat.md](../product/modules/chat.md) | Sala obtida por `get_or_create(tipo=Conversa.TIPO_GLOBAL)`, única por tenant (`UniqueConstraint`) | Mutação (`POST`) exige conteúdo não vazio; mensagem sempre associada à sala global e ao `request.user` como autor | `global_sala` não verifica `request.user` contra `sala.participantes` antes de listar ou permitir postagem | Sala global compartilhada por todo o tenant, sem exigência de verificação de participante | Constatado no código | Ausência de checagem de participante é consistente com a natureza da sala global |
| Enviar mensagem | Idem | Idem | Idem | Idem — restrito à sala global nesta versão | Idem | `Mensagem.conteudo` validado como não vazio antes de salvar; `POST` exigido | Mensagem sempre associada à sala global e ao `request.user` como autor | Idem acima | Constatado no código | — |
| Acessar conversa individual ou em grupo (direção funcional) | Módulo `chat` | `""` (módulo sem nível) | Sem habilitação específica no kernel atual | Participação na conversa, ou escopo administrativo explícito, conforme [chat.md](../product/modules/chat.md) | Não aplicável — operação não implementada | Não aplicável — operação não implementada | Nenhuma view de criação ou carregamento de conversa individual/grupo foi identificada | Conversas individuais e em grupo, conforme [chat.md](../product/modules/chat.md) | Evolução planejada | — |

Observações:

- Conhecer o `pk` de uma conversa não concede acesso a ela — hoje isso
  é estruturalmente verdadeiro por acidente (o `pk` é ignorado), não por
  uma verificação de autorização deliberada; quando conversas
  individuais/grupo forem implementadas, a verificação de participação
  deve ser explícita.
- Sala global é diferente de conversa privada: a ausência de checagem de
  participante em `global_sala` é aceitável apenas porque a sala é, por
  definição funcional, compartilhada por todo o tenant.

### Modelos

Rotas auditadas: `apps/modelos/views.py` (`lista`, `novo`, `detalhe`,
`editar`, `importar`), todas `@login_required`.

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Listar | Chave `modelos` no kernel | `somente_seus`/`todos`, definidos para `modelos` | Não se aplica a uma listagem | Por `ModeloPeca.criado_por`, conforme [modelos.md](../product/modules/modelos.md) | Não aplicável | Não aplicável | `lista` não chama `tem_permissao_modulo`; `QuerySet` filtra apenas por busca textual (`q`), nunca por `criado_por` | Um usuário deveria acessar apenas modelos dentro de seu escopo autorizado | Lacuna constatada | — |
| Visualizar (detalhe) | Idem | Idem | Sem habilitação específica no kernel atual para "visualizar" | Idem acima | `get_object_or_404(ModeloPeca, pk=pk)` | Não aplicável | Objeto carregado sem condição de posse | Objeto deveria ser carregado já restrito ao escopo do usuário | Lacuna constatada | — |
| Criar | Idem | Idem | `modelos_criar` existe no kernel | Não aplicável à criação em si | Não aplicável | `criado_por` preenchido com `request.user` | `apps/modelos/views.py::novo` não chama `tem_habilitacao` | Habilitação deveria ser exigida quando existir chave correspondente | Lacuna constatada | — |
| Editar | Idem | Idem | Sem habilitação específica no kernel atual para edição geral (`modelos_editar_estilo` refere-se a `EstiloEscritorio`, não a `ModeloPeca`) | Idem ao escopo de leitura acima | `get_object_or_404(ModeloPeca, pk=pk)` | Mutação exige `POST` | Objeto carregado sem condição de posse | Objeto deveria ser carregado dentro do escopo do usuário | Lacuna constatada | — |
| Importar | Idem | Idem | Sem habilitação específica no kernel atual (`importar` não está entre os itens de `modelos`) | Não aplicável à criação em si | Não aplicável | `criado_por` preenchido com `request.user` | `ImportarModeloPecaForm` valida extensão (`.pdf`/`.docx`) e tamanho máximo (10 MB) antes de extrair texto | Validação de arquivo já existe; habilitação não é exigida | Lacuna constatada | Candidata a reaproveitar `modelos_criar` |
| Reutilizar | Módulo `modelos` | `somente_seus`/`todos`, definidos para `modelos` | Sem habilitação específica no kernel atual | Idem ao escopo de leitura acima | Não aplicável — operação não implementada como cópia distinta | Não aplicável — operação não implementada | Nenhuma rota de duplicação/cópia foi encontrada em `apps/modelos/urls.py`; `editar` modifica a mesma instância, não cria uma cópia | Copiar ou reutilizar um modelo não deve alterar o modelo original, conforme [modelos.md](../product/modules/modelos.md) | Evolução planejada | — |

Observações:

- `modelos_editar_estilo` é uma habilitação existente no kernel sem
  nenhuma view ou rota correspondente — `EstiloEscritorio` (tom de voz e
  instruções gerais do escritório) não possui `views.py`/`urls.py`
  próprios identificados.
- Integração com IA é futura, condicionada a
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md);
  não há, hoje, nenhuma chamada de IA em `apps/modelos/`.

### Inteligência Artificial / Laboratório

Rotas auditadas: `apps/laboratorio/views.py::index` (única view,
`@login_required`, apenas renderiza template). Todas as operações
abaixo são planejadas — nenhuma possui implementação além do shell
visual, conforme [../architecture/overview.md](../architecture/overview.md).

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Abrir interface (Assistente/Laboratório) | `apps.laboratorio` não é um módulo do kernel (`MODULO_CHOICES` não inclui `laboratorio`) | Não aplicável — sem chave de módulo própria | `processos_usar_laboratorio` existe sob o módulo `processos` | Escopo do processo de origem, quando a interface for aberta a partir de um processo | Não aplicável — não há carregamento de processo na view atual | Não aplicável | A view verifica apenas `@login_required`; `processos_usar_laboratorio` não é consultada por `apps/laboratorio/views.py` | Módulo/processo autorizado deveria ser pré-requisito de acesso, conforme [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md) | Evolução planejada | — |
| Acessar contexto do processo | Módulo `processos`, condicionado a PDR-0008 | — | `processos_usar_laboratorio`/`processos_usar_ia` existem no kernel | Escopo do processo — nenhuma ampliação por IA | Não aplicável — operação não implementada | Não aplicável | Nenhuma view implementa esta operação | Autorização aplicada, escopo de dados definido e isolamento entre tenants, conforme [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md) | Evolução planejada | — |
| Consultar documentos | Módulo `processos`/IA, condicionado a PDR-0008 | — | Sem habilitação específica no kernel atual | Escopo dos documentos já autorizados ao usuário | Não aplicável — operação não implementada | Não aplicável | Nenhum model de objeto interno possui `FileField`/`ImageField` na inspeção realizada | Acesso a cada documento deveria ser controlado como o acesso direto a ele, conforme [inteligencia-artificial.md](../product/modules/inteligencia-artificial.md) | Evolução planejada | — |
| Gerar resumo | Idem | — | Idem | Idem | Não aplicável — operação não implementada | Não aplicável | Nenhuma view implementa esta operação | Idem acima | Evolução planejada | — |
| Discutir estratégia | Idem | — | Idem | Idem | Não aplicável — operação não implementada | Não aplicável | Nenhuma view implementa esta operação | Idem acima | Evolução planejada | — |
| Gerar ou editar peça | Idem | — | Idem | Idem | Não aplicável — operação não implementada | Confirmação humana exigida antes de qualquer conteúdo se tornar definitivo | Nenhuma view implementa esta operação | Conteúdo gerado exige revisão humana, conforme [inteligencia-artificial.md](../product/modules/inteligencia-artificial.md) | Evolução planejada | — |
| Sugerir salvamento como modelo | Módulo `processos`/`modelos`, integrado a [modelos.md](../product/modules/modelos.md) | — | Sem habilitação específica no kernel atual | Escopo de Modelos, quando implementado | Não aplicável — operação não implementada | Confirmação humana exigida; modelo original não deve ser alterado durante reutilização | Nenhuma view implementa esta operação | Sugestão de IA não substitui confirmação humana nem altera modelo original | Evolução planejada | — |
| Sugerir honorário | Módulo `processos`/`financeiro`, integrado a [PDR-0007](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md) | — | Sem habilitação específica no kernel atual | Escopo de Financeiro, quando implementado | Não aplicável — operação não implementada | Confirmação humana exigida antes de gerar lançamento definitivo | Nenhuma view implementa esta operação | Sugestão de IA para honorário exige confirmação humana antes de virar lançamento definitivo | Evolução planejada | — |

Observações:

- Esta matriz não trata a interface de Laboratório como um produto de
  IA separado — ela é a interface planejada para a IA jurídica dentro
  do contexto do processo, conforme
  [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
  e o [glossário funcional](../product/glossary.md).
- IA não amplia escopo: quando implementada, nenhuma resposta ou
  sugestão de IA deve conceder acesso a um dado que o usuário não
  estivesse previamente autorizado a ver — princípio canônico registrado
  em [overview.md](overview.md) e em
  [inteligencia-artificial.md](../product/modules/inteligencia-artificial.md).

### Configurações e administração do escritório

Rotas auditadas: `apps/configuracoes/views.py` (`index`,
`editar_perfil`, `novo_usuario`, `equipes`, `nova_equipe`,
`editar_equipe`, `equipe_membros`, `remover_membro_equipe`,
`alternar_gerente_equipe`, `permissoes`, `editar_escritorio`).

| Operação | Aut. módulo | Nível técnico | Habilitação | Escopo necessário | Aut. objeto | Integridade | Estado constatado | Alvo canônico | Classificação | Observação ou pendência |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Editar o próprio perfil | Sem chave de módulo específica | Não aplicável | Não aplicável | O próprio usuário, sempre | Não aplicável a `pk` de URL — a view opera sobre `request.user` | Mutação exige `POST` via `PerfilUsuarioForm` | `editar_perfil` usa apenas `@login_required`; `PerfilUsuario.objects.get_or_create(user=request.user)` opera sobre `request.user`, o que estruturalmente impede editar o perfil de outro por esta view | Todo usuário autenticado deveria editar seus próprios dados pessoais, conforme [configuracoes.md](../product/modules/configuracoes.md) | Constatado no código | — |
| Visualizar configurações (`index`) | Sem chave de módulo específica | Não aplicável | Não aplicável | Qualquer usuário autenticado do tenant | Não aplicável | Não aplicável | `index` usa apenas `@login_required` | Não há exigência canônica de restringir esta tela além da autenticação | Constatado no código | — |
| Administrar usuários (listar com papel) | Sem chave de módulo específica além de `gerir` | Não aplicável | `gerir_criar_usuario`/`gerir_habilitar_usuario_processos` existem no kernel | A gestão administrativa de usuários é restrita a papéis de acesso autorizados para administração do escritório, conforme [configuracoes.md](../product/modules/configuracoes.md) | Não aplicável | Não aplicável | Na inspeção do template `templates/configuracoes/index.html`, a lista de usuários (com papel, cargo e equipes) está no mesmo bloco sempre renderizado da tela `index`, sem condicional de `usuario_e_admin_escritorio`; apenas o botão "Novo usuário" é condicionado a esse contexto — a listagem em si é visível a qualquer usuário autenticado | A listagem administrativa de usuários deveria ser restrita a papéis autorizados para administração | Lacuna constatada | O template inclui um botão de remoção sem `href`/ação associada junto a cada usuário, aparentemente não funcional |
| Criar usuário | `@requer_admin_escritorio` protege `novo_usuario` | Não aplicável | `gerir_criar_usuario` existe no kernel | A gestão administrativa de usuários é restrita a papéis de acesso autorizados para administração do escritório, conforme [configuracoes.md](../product/modules/configuracoes.md) | Não aplicável | `CriarUsuarioEscritorioForm` restringe o papel atribuível a `limitado`/`financeiro` (`GRUPOS_CRIACAO_USUARIO`); `administrador_escritorio` não é uma opção nesta tela | O controle atual é `@requer_admin_escritorio`, um controle binário administrador/não-administrador; `gerir_criar_usuario` não é consultada | O alvo canônico permite papéis de acesso autorizados, não apenas o Administrador do escritório — o controle atual é mais restrito que essa possibilidade, não mais permissivo | Constatado no código | Uma futura habilitação reutilizável (`gerir_criar_usuario`) poderia ampliar quem administra usuários sem depender exclusivamente do decorator |
| Administrar equipes (listar) | `@requer_admin_escritorio` protege `equipes` | Não aplicável | `gerir_criar_equipe` existe no kernel | Restrito a papéis de acesso autorizados para administração do escritório, conforme [configuracoes.md](../product/modules/configuracoes.md) | Não aplicável | Não aplicável | `@requer_admin_escritorio` é o único controle constatado; `gerir_criar_equipe` não é consultada | Idem acima | Constatado no código | — |
| Criar equipe | `@requer_admin_escritorio` protege `nova_equipe` | Não aplicável | `gerir_criar_equipe` existe no kernel | Idem acima | Não aplicável | Mutação exige `POST` via `EquipeForm` | `@requer_admin_escritorio` é o único controle constatado | Idem acima | Constatado no código | — |
| Editar equipe | `@requer_admin_escritorio` protege `editar_equipe` | Não aplicável | Sem habilitação específica no kernel atual para edição | Idem acima | `get_object_or_404(Equipe, pk=pk)` | Mutação exige `POST` | Objeto carregado sem condição adicional além do que `@requer_admin_escritorio` já filtra por papel (não por tenant explícito, garantido estruturalmente pelo schema) | Idem acima | Constatado no código | — |
| Administrar membros (adicionar/listar) | `@requer_admin_escritorio` protege `equipe_membros` | Não aplicável | Sem habilitação específica no kernel atual | Idem acima | `get_object_or_404(Equipe, pk=pk)` | Mutação exige `POST` via `MembroEquipeForm`; remoção (`remover_membro_equipe`) usa `get_object_or_404(MembroEquipe, pk=membro_pk, equipe=equipe)`, garantindo que o membro pertence à equipe da URL | `@requer_admin_escritorio` é o único controle constatado | Idem acima | Constatado no código | — |
| Alternar gerente | `@requer_admin_escritorio` protege `alternar_gerente_equipe` | Não aplicável | Sem habilitação específica no kernel atual | Idem acima | `get_object_or_404(MembroEquipe, pk=membro_pk, equipe=equipe)` | Mutação exige `POST`; alterna `eh_gerente` via `update_fields` | `@requer_admin_escritorio` é o único controle constatado | Idem acima | Constatado no código | — |
| Administrar papéis (`PapelAcesso`) | Sem chave de módulo específica | Não aplicável | Não aplicável | "Papéis de acesso" está listado no escopo funcional de Configurações, conforme [configuracoes.md](../product/modules/configuracoes.md) | Não aplicável — operação não implementada | Não aplicável | Nenhuma rota/view foi encontrada para criar, listar ou editar `PapelAcesso` | Administração de papéis restrita a papéis de acesso autorizados para administração do escritório | Lacuna constatada | `configuracoes.md` lista papéis de acesso no escopo funcional imediato, sem marcá-lo como fora de escopo |
| Administrar permissões | `@requer_admin_escritorio` protege `permissoes` | A tela configura `PermissaoPapel.ativo`/`nivel` por `tipo_conta` (`limitado`/`financeiro`), não por `PapelAcesso` | `TIPOS_CONTA_CONFIGURAVEIS` restringe a `limitado`/`financeiro` | Restrito a papéis de acesso autorizados para administração do escritório | Não aplicável — a view opera sobre `PermissaoPapel` filtrado por `tipo_conta`, sem carregar um objeto único por `pk` | `update_or_create` valida `tipo_conta` contra `TIPOS_CONTA_CONFIGURAVEIS` e `nivel` contra os valores válidos do módulo antes de salvar | `@requer_admin_escritorio` protege a rota; nenhuma habilitação específica a gateia além do decorator; a tela cobre apenas o caminho legado de `tipo_conta`, não `PapelAcesso`/`UsuarioPapel` | Administração de permissões deveria cobrir também o kernel dinâmico (`PapelAcesso`/`UsuarioPapel`), não apenas o caminho legado | Constatado no código | Cobertura parcial: apenas o caminho legado de `tipo_conta` é administrável por interface |
| Administrar habilitações (`HabilitacaoPapel`/`HabilitacaoUsuario`) | Sem chave de módulo específica | Não aplicável | Não aplicável | "Habilitações" está listado no escopo funcional de Configurações, conforme [configuracoes.md](../product/modules/configuracoes.md) | Não aplicável — operação não implementada | Não aplicável | Nenhuma rota/view foi encontrada para configurar habilitações por papel ou por usuário | Administração de habilitações restrita a papéis de acesso autorizados para administração do escritório | Lacuna constatada | `configuracoes.md` lista habilitações no escopo funcional imediato, sem marcá-lo como fora de escopo |
| Editar identidade visual (white label) | Sem chave de módulo específica | Não aplicável | Não aplicável | As configurações white label pertencem ao escritório (tenant), conforme [configuracoes.md](../product/modules/configuracoes.md) | Não aplicável | Não aplicável | Na inspeção realizada, `ConfiguracaoVisual` (logo, favicon, cores, imagem de fundo) está registrada no Django Admin (`apps/saas_tenants/admin.py`), no schema público, e não foi identificada uma rota tenant para editar seus campos; `editar_escritorio`, em `apps.configuracoes`, edita apenas `ConfiguracaoEscritorio` (nome, CNPJ, contato), sem campos visuais | Edição de identidade visual básica deveria estar acessível ao Administrador do escritório dentro do tenant | Lacuna constatada | A ausência de rota tenant não constitui impossibilidade definitiva — o Django Admin permanece uma via de acesso ao registro, ainda que fora do fluxo do tenant |
| Visualizar plano e assinatura | Sem chave de módulo específica | Não aplicável | Não aplicável | Consulta e gestão do plano SaaS devem distinguir Administrador do escritório e Platform Admin, conforme [configuracoes.md](../product/modules/configuracoes.md) | Não aplicável | Leitura apenas — nenhuma escrita em `saas_billing` identificada a partir de `apps.configuracoes` | Leitura de `request.tenant.assinatura.plano.nome` em `index` (e em `apps/dashboard/views.py::painel`), disponível a qualquer usuário autenticado do tenant, sem gestão do plano | Consulta e gestão deveriam respeitar a distinção entre Administrador do escritório e Platform Admin | Constatado no código | Interface de administração do plano não confirmada nem no código nem na especificação |

Observações:

- `@requer_admin_escritorio` é o controle atualmente constatado para a
  maior parte destas rotas — um controle binário
  (administrador/não-administrador) que não consulta
  `tem_permissao_modulo`/`tem_habilitacao` do módulo `gerir`, mesmo
  sendo a tela que os configura para os demais tipos de conta. Este
  controle é mais restrito que a direção canônica de
  [configuracoes.md](../product/modules/configuracoes.md) (que admite
  "papéis de acesso autorizados para administração do escritório", não
  apenas a flag `is_admin_escritorio`), não mais permissivo — não há,
  portanto, um bypass indevido nessas rotas administrativas, apenas uma
  resolução menos reutilizável e rastreável do que a matriz canônica
  poderia exigir (por exemplo, uma habilitação `gerir_administrar_papeis`
  explícita, em vez de um decorator dedicado e paralelo ao kernel). Esta
  matriz registra a necessidade sem decidir o desenho técnico.
- Diferenciação obrigatória: operação sobre o próprio perfil
  (`editar_perfil`, qualquer usuário) é estruturalmente distinta de
  administração do escritório (`@requer_admin_escritorio`); consulta a
  billing compartilhado é somente leitura, sem lançamento automático no
  Financeiro do tenant, conforme
  [PDR-0003](../product/decisions/PDR-0003-areas-funcionais-financeiro.md).
- Na inspeção de `templates/configuracoes/index.html`: o card
  "Administração" (Equipes, Permissões) e o botão "Editar dados do
  escritório" são condicionados a `usuario_e_admin_escritorio`; o card
  de conta do usuário logado e os dados do escritório em modo leitura
  não são condicionados; a listagem completa de usuários (nome, papel,
  cargo, equipes) é renderizada para qualquer usuário autenticado, com
  apenas o botão "Novo usuário" condicionado.

## Operações sem habilitação correspondente

| Módulo | Operação | Situação no kernel atual | Tratamento canônico |
| --- | --- | --- | --- |
| Financeiro (todas as áreas) | Listar, criar, editar, marcar pago, cancelar, reabrir, excluir lançamento; listar/criar custa | Módulo `financeiro` não possui nenhum item em `ITENS_POR_MODULO` | Depende apenas de módulo + escopo + autorização da ação; os valores de nível técnico `solicitacoes`/`dados` já existem no kernel para este módulo, mas seu mapeamento definitivo a operações específicas não está formalizado; candidata a habilitação futura caso operações específicas (por exemplo, "cancelar lançamento") precisem de controle mais fino |
| Chat | Acessar lista, acessar conversa, enviar mensagem | Módulo `chat` não possui nenhum item em `ITENS_POR_MODULO` | Depende apenas de módulo + escopo (participação na conversa) |
| Dashboard | Visualizar painel, indicadores, indicadores financeiros | Módulo `painel` não possui nenhum item em `ITENS_POR_MODULO` | Depende apenas de módulo + escopo agregado dos módulos de origem |
| Processos | Arquivar, reabrir, adicionar participante | `ITENS_POR_MODULO["processos"]` cobre criar/editar/andamento/IA/laboratório, mas não arquivar/reabrir/participante | Na versão atual, dependem apenas da autorização binária do módulo, conforme [PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md); habilitações específicas permanecem evolução futura e não bloqueiam a Fase A |
| Clientes | Desativar, reativar, listar inativos | `ITENS_POR_MODULO["clientes"]` cobre apenas criar/editar | Não decidido — candidata a habilitação futura ou tratamento como parte de `clientes_editar` |
| Tarefas | Iniciar, concluir, reabrir, excluir, atribuir a si mesmo | `ITENS_POR_MODULO["tarefas"]` cobre apenas `tarefas_atribuir_outros` | Depende apenas de módulo + escopo (responsável atual); "atribuir a outros" já possui chave, mas não está implementada na interface |
| Agenda | Editar, concluir, cancelar, reabrir, excluir | `ITENS_POR_MODULO["agenda"]` cobre apenas `agenda_criar_para_outros` | Depende apenas de módulo + escopo (responsável/participante) |
| Modelos | Visualizar, importar, reutilizar | `ITENS_POR_MODULO["modelos"]` cobre apenas criar e editar estilo | Não decidido — "importar" candidata a reaproveitar `modelos_criar`; "reutilizar" não decidido, pois a operação em si não está implementada |
| Configurações | Editar o próprio perfil, visualizar configurações | Sem chave de habilitação — controlado por identidade do próprio usuário (`request.user`) | Depende apenas de autenticação; não é candidata a habilitação, por não envolver escopo de terceiros |

## Habilitações sem enforcement constatado

| Chave de habilitação | Módulo | Finalidade funcional | Uso constatado nas views |
| --- | --- | --- | --- |
| `processos_criar` | Processos | Habilitar criação de processo | Não encontrado em uso |
| `processos_editar` | Processos | Habilitar edição de processo | Não encontrado em uso |
| `processos_andamento_adicionar` | Processos | Habilitar adição de andamento/movimentação | Não encontrado em uso |
| `processos_usar_ia` | Processos | Habilitar uso de IA jurídica no contexto do processo | Não encontrado em uso; funcionalidade de IA não implementada |
| `processos_usar_laboratorio` | Processos | Habilitar uso do Assistente/Laboratório | Não encontrado em uso; `apps/laboratorio/views.py` não consulta habilitação alguma |
| `clientes_criar` | Clientes | Habilitar criação de cliente | Não encontrado em uso |
| `clientes_editar` | Clientes | Habilitar edição de cliente | Não encontrado em uso |
| `tarefas_atribuir_outros` | Tarefas | Habilitar atribuição de tarefa a outro usuário | Não encontrado em uso; `TarefaForm` não expõe campo `responsavel`, portanto não há ponto no código onde esta habilitação poderia ser consultada |
| `modelos_criar` | Modelos | Habilitar criação de modelo | Não encontrado em uso |
| `modelos_editar_estilo` | Modelos | Habilitar edição do estilo do escritório (`EstiloEscritorio`) | Não encontrado em uso; adicionalmente, não há view/rota para `EstiloEscritorio` |
| `agenda_criar_para_outros` | Agenda | Habilitar criação de compromisso para outro usuário | Não encontrado em uso; `CompromissoForm` expõe campo `responsavel`, mas nenhuma view consulta esta habilitação antes de aceitar um valor diferente do criador |
| `gerir_criar_usuario` | Gerir | Habilitar criação de usuário | Não encontrado em uso; `novo_usuario` usa `@requer_admin_escritorio`, não `tem_habilitacao` |
| `gerir_habilitar_usuario_processos` | Gerir | Finalidade funcional não detalhada além do nome da chave | Não encontrado em uso |
| `gerir_criar_equipe` | Gerir | Habilitar criação de equipe | Não encontrado em uso; `nova_equipe` usa `@requer_admin_escritorio`, não `tem_habilitacao` |
| `gerir_habilitar_terceiros` | Gerir | Finalidade funcional não detalhada além do nome da chave | Não encontrado em uso |

Nenhuma das 15 habilitações definidas em `ITEM_CHOICES`
(`apps/accounts/permissoes_constants.py`) foi encontrada em uso fora de
`apps/accounts/permissoes.py` e dos testes de `apps/accounts/tests/`,
conforme já registrado em [authorization-model.md](authorization-model.md).
Para `processos_criar`, `processos_editar` e
`processos_andamento_adicionar`, essa ausência de enforcement é a
política deliberada da versão atual definida pelo
[PDR-0010](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md):
as chaves permanecem no kernel como evolução futura e não constituem
lacuna nem dívida bloqueante da Fase A de Processos.

## Relação com o nível técnico atual

| Módulo | Valores atuais de `nivel` | Interpretação técnica atual | Limite canônico |
| --- | --- | --- | --- |
| Processos, Clientes, Tarefas, Modelos, Painel, Agenda | `somente_seus`, `todos` | Resolvido por `permissao_efetiva()`/`nivel_acesso_modulo()`, em `apps/accounts/permissoes.py`; não lido por nenhuma view operacional para filtrar um `QuerySet` | Não deve ser tratado como escopo já aplicado nem como autorização de ação; mistura, sem decompor, possíveis noções de "quantos registros o usuário alcança" |
| Financeiro | `solicitacoes`, `dados` | Os nomes desses valores guardam semelhança com a distinção entre acesso limitado a solicitações e acesso pleno a dados financeiros descrita em [financeiro.md](../product/modules/financeiro.md), mas essa correspondência não é uma decisão canônica formalizada nem é lida por `apps/financeiro/views.py` | Não deve ser tratado como o mecanismo que já implementa a separação de acesso ao caixa geral exigida por PDR-0006; o mapeamento definitivo entre esses valores e as operações do módulo, se vier a existir, deverá ser formalizado na implementação da matriz |
| Chat, Gerir | `""` (vazio) | Módulos sem escopo de dados por nível — apenas a autorização de módulo (`ativo`) se aplica, conforme `NIVEIS_POR_MODULO` | Não se aplica decomposição de nível a estes módulos; qualquer futura granularidade em `gerir` deveria usar habilitação, não nível |

Esta tabela não é a política final de escopo — ela apenas registra os
valores existentes e sua ausência de efeito prático hoje. A
decomposição definitiva de `nivel` entre escopo, visibilidade e
modalidade de acesso pertence a uma implementação futura de escopo,
conforme [data-scope.md](data-scope.md).

## Estado atual versus alvo canônico

| Área | Estado constatado | Alvo canônico | Tipo de trabalho futuro |
| --- | --- | --- | --- |
| Autorização de módulo | Kernel resolve corretamente via `permissao_efetiva()`; Clientes e as nove views de Processos chamam `tem_permissao_modulo`; os demais módulos operacionais ainda não aplicam o helper | Toda view operacional deveria verificar autorização de módulo antes de processar a requisição | Aplicação do kernel nas views restantes (Rodada 2.1, [PDR-0009](../product/decisions/PDR-0009-sequencia-fase-2.md)); Fase A de Processos satisfeita pelo WI-0004 conforme PDR-0010 |
| Habilitações | 15 itens definidos e cobertos por testes do kernel; Clientes consome suas habilitações de criar/editar; Processos preserva suas chaves granulares sem enforcement por decisão do PDR-0010 | Habilitação deve gatear operações sensíveis quando exigida pela decisão canônica vigente do módulo | Aplicação de `tem_habilitacao()` nas views correspondentes conforme a política de cada módulo; as chaves granulares de Processos são evolução futura e não bloqueiam sua Fase A |
| Escopo | Helpers de equipe existem (`apps/accounts/escopo.py`), mas não filtram nenhum `QuerySet`; `nivel` não é lido como escopo | `QuerySet`s de listagem e objetos por `pk` deveriam nascer filtrados pelo escopo do usuário | Implementação de filtros de escopo por responsável/equipe/participante em cada módulo operacional |
| Objetos por ID | `get_object_or_404` sem condição de posse em Clientes, Processos, Tarefas, Agenda, Financeiro e Modelos | Objeto deveria ser carregado dentro do `QuerySet` já restrito por escopo | Reescrever consultas de detalhe/edição/exclusão para reutilizar o escopo da listagem |
| Dashboard | Agrega dados de todo o tenant sem filtro por usuário | Indicadores deveriam refletir apenas o escopo do usuário que consulta | Aplicar escopo ao Dashboard depois de os módulos de origem já aplicarem escopo (ordem recomendada nas fontes históricas subordinadas) |
| Financeiro | Módulo sem habilitações; `nivel` `solicitacoes`/`dados` não lido; nenhuma distinção entre usuário com/sem acesso ao caixa geral; solicitações e honorários não modelados como entidades próprias | Usuário sem acesso ao caixa geral deveria ver apenas suas próprias solicitações ([PDR-0006](../product/decisions/PDR-0006-solicitacoes-financeiras.md)), sem visualizar totais completos | Implementar modelagem de Solicitação e de Honorário, e formalizar o mecanismo de controle de acesso ao caixa geral (podendo ou não reaproveitar o campo `nivel` já existente) |
| Integridade cliente-processo | Preenchimento automático de `cliente` a partir de `processo.cliente` quando ausente, em Tarefas e Agenda; nenhuma rejeição de combinação inconsistente enviada por `POST` | O servidor deveria rejeitar um vínculo cliente-processo inconsistente, mesmo com requisição manipulada | Validação de integridade em `TarefaForm`/`CompromissoForm` e nas views associadas |
| Sidebar/interface | `templates/components/sidebar.html` exibe todos os módulos a qualquer usuário autenticado, sem condicionar a `tem_permissao_modulo`, conforme [authorization-model.md](authorization-model.md) | A interface deveria refletir, não substituir, a autorização real resolvida no backend | Condicionar itens de menu à autorização de módulo já resolvida no backend, sem que essa condicional seja a única barreira |
| Testes negativos | Testes extensivos do kernel em `apps/accounts/tests/`; Clientes cobre autorização e escopo; Processos cobre autorização binária de módulo nas nove views (WI-0004), sem escopo por ainda pertencer ao WI-0005; testes de fumaça (`_SmokeBase`) verificam apenas ausência de HTTP 500 | Deveria existir teste negativo por módulo e, quando a fase de escopo estiver implementada, um usuário sem escopo não deveria alcançar registro de outro usuário do mesmo tenant | Criação dos testes ainda ausentes nos demais módulos e dos testes de escopo de Processos no WI-0005 |
| Arquivos | Nenhum objeto interno (Cliente, Processo, Tarefa, etc.) possui campo de upload; avatar de usuário e identidade visual não têm checagem de autorização dedicada além de `@login_required`/`@requer_admin_escritorio` | Um arquivo vinculado a um registro pai deveria exigir a mesma autorização que o registro pai | Definir estratégia de segregação e autorização de arquivos quando anexos de objetos internos forem introduzidos |
| IA | `apps.laboratorio` é um shell visual sem lógica de negócio; nenhuma permissão ou habilitação é consultada | IA jurídica só deveria operar após os pré-requisitos do [PDR-0008](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md) estarem consolidados, e nunca ampliar o escopo já autorizado ao usuário | Implementação futura da IA jurídica condicionada à consolidação do núcleo funcional descrita nesta matriz |

## Decisões e pontos em aberto

Esta matriz preserva, sem resolver, os seguintes pontos:

- **OPEN-001** — periodicidades financeiras da primeira versão, conforme
  [open-decisions.md](../product/open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão);
  afeta a modelagem de autorização de futuras ocorrências recorrentes e
  parceladas.
- **OPEN-002** — etapas de aprovação das solicitações financeiras,
  conforme
  [open-decisions.md](../product/open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras);
  afeta quem processa cada transição de estado de uma solicitação.
- **Regra final por módulo para múltiplas equipes** — um usuário pode
  pertencer a mais de uma `Equipe` (`MembroEquipe` não é `unique` por
  usuário), mas nenhuma regra de produto aprovada define como o escopo
  se comporta nesse caso, conforme
  [equipes.md](../product/modules/equipes.md).
- **Semântica de hierarquia entre equipes** — `Equipe.equipe_pai` e
  `equipes_descendentes()` já existem no código, mas se a hierarquia
  deveria propagar escopo automaticamente não está decidido.
- **Política de superuser** — `usuario_admin_escritorio()` não verifica
  `is_superuser` no código atual; se um superuser técnico deveria ter
  algum caminho de acesso emergencial não está decidido nesta matriz.
- **Negação entre múltiplos papéis** — o kernel atual implementa apenas
  união positiva entre papéis ativos; não existe mecanismo de um papel
  negar explicitamente uma concessão de outro papel do mesmo usuário.
- **Desativação e remoção de papéis** — o efeito administrativo completo
  de desativar um `PapelAcesso` em uso, ou de remover um `UsuarioPapel`,
  não foi auditado além da resolução em tempo de leitura.
- **Delegação temporária** — não há, nas fontes lidas, decisão sobre
  conceder escopo ou autorização temporária a um usuário.
- **Administração emergencial** — acesso excepcional do Platform Admin a
  um tenant específico não possui decisão nas fontes canônicas.
- **Anexos e storage** — nenhum objeto interno possui campo de upload
  hoje; estratégia de segregação e autorização de arquivos por tenant
  permanece em aberto, conforme
  [../architecture/multitenancy.md](../architecture/multitenancy.md).
- **Autorização de exportações** — nenhuma funcionalidade de exportação
  foi identificada no código; a autorização e o escopo aplicáveis a uma
  futura exportação não foram decididos.

Nenhum novo identificador de decisão em aberto foi criado por esta
matriz.

## Critérios de aceite da matriz

- Nenhuma operação depende somente da interface para sua autorização.
- Cada operação identifica as camadas necessárias (módulo, nível,
  habilitação, escopo, objeto, integridade), mesmo quando o estado
  constatado for "não aplicado".
- Módulo, habilitação, escopo e objeto não são confundidos entre si em
  nenhuma linha da matriz.
- Estado constatado e alvo canônico ocupam colunas próprias em cada
  linha da Matriz detalhada — nenhuma célula mistura, na mesma frase, o
  que o código faz hoje e o que a documentação exige.
- Operações sem habilitação correspondente estão explicitadas na seção
  própria, sem inventar novas chaves.
- Níveis técnicos (`nivel`) não são tratados como autorização final de
  uma operação nem como escopo já aplicado em nenhuma célula ou
  observação; nenhuma associação entre um valor de `nivel` e uma
  operação futura é apresentada como decisão aprovada sem fonte
  canônica explícita.
- O bypass de admissão de módulo do Administrador do escritório
  (`usuario_admin_escritorio()` avaliado antes de regras individuais,
  com acesso no maior nível técnico do módulo) é registrado como estado
  constatado do kernel, não como regra canônica universal de acesso
  irrestrito a qualquer objeto, conversa ou documento.
- A ausência de uma rota não é classificada como lacuna quando nenhuma
  fonte canônica exige a operação correspondente — nesses casos, a
  ausência é registrada como estado constatado, não como falha.
- Platform Admin não recebe acesso jurídico automático a dados
  operacionais de um tenant em nenhuma linha desta matriz.
- Gerente de equipe não recebe acesso global automático em nenhuma linha
  desta matriz.
- Toda operação de IA respeita o escopo já autorizado ao usuário, sem
  ampliá-lo.
- As decisões em aberto listadas permanecem abertas — nenhuma foi
  resolvida ou transformada em decisão aprovada por este documento.
- As diferenças entre estado atual constatado e alvo canônico ficam
  explícitas em cada seção, sem presumir enforcement inexistente.

## Referências

- [overview.md](overview.md)
- [authorization-model.md](authorization-model.md)
- [data-scope.md](data-scope.md)
- [../architecture/multitenancy.md](../architecture/multitenancy.md)
- [../architecture/overview.md](../architecture/overview.md)
- [../architecture/module-map.md](../architecture/module-map.md)
- [../product/glossary.md](../product/glossary.md)
- [../product/open-decisions.md](../product/open-decisions.md)
- [../product/vision.md](../product/vision.md)
- [../product/scope.md](../product/scope.md)
- [../product/modules/README.md](../product/modules/README.md)
- [../product/modules/clientes.md](../product/modules/clientes.md)
- [../product/modules/processos.md](../product/modules/processos.md)
- [../product/modules/tarefas.md](../product/modules/tarefas.md)
- [../product/modules/agenda.md](../product/modules/agenda.md)
- [../product/modules/equipes.md](../product/modules/equipes.md)
- [../product/modules/financeiro.md](../product/modules/financeiro.md)
- [../product/modules/dashboard.md](../product/modules/dashboard.md)
- [../product/modules/configuracoes.md](../product/modules/configuracoes.md)
- [../product/modules/chat.md](../product/modules/chat.md)
- [../product/modules/modelos.md](../product/modules/modelos.md)
- [../product/modules/inteligencia-artificial.md](../product/modules/inteligencia-artificial.md)
- [../product/decisions/PDR-0001-participantes-processuais.md](../product/decisions/PDR-0001-participantes-processuais.md)
- [../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md](../product/decisions/PDR-0002-delegacao-direta-de-tarefas.md)
- [../product/decisions/PDR-0003-areas-funcionais-financeiro.md](../product/decisions/PDR-0003-areas-funcionais-financeiro.md)
- [../product/decisions/PDR-0004-previsto-e-realizado.md](../product/decisions/PDR-0004-previsto-e-realizado.md)
- [../product/decisions/PDR-0005-custas-por-cliente.md](../product/decisions/PDR-0005-custas-por-cliente.md)
- [../product/decisions/PDR-0006-solicitacoes-financeiras.md](../product/decisions/PDR-0006-solicitacoes-financeiras.md)
- [../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md](../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md)
- [../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md](../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
- [../product/decisions/PDR-0009-sequencia-fase-2.md](../product/decisions/PDR-0009-sequencia-fase-2.md)
- [../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md](../product/decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)

## Classificação das linhas

Cada linha da matriz detalhada indica uma destas classificações:

- **constatado no código** — comportamento observável diretamente nos
  arquivos atuais do repositório.
- **direção canônica** — comportamento pretendido, registrado em
  documentação de produto ou segurança aprovada.
- **evolução planejada** — objetivo futuro registrado em escopo, PDR ou
  especificação de módulo, sem implementação confirmada.
- **ponto em aberto** — decisão de produto ou arquitetura ainda não
  tomada nas fontes canônicas.
- **lacuna constatada** — uma direção canônica existe, mas o código
  atual não a implementa.

Uma rota atualmente implementada não é tratada, nesta matriz, como
decisão permanente de produto. Uma especificação futura não é tratada
como implementação existente. A ausência de uma rota não é tratada como
proibição definitiva — apenas como estado não implementado até nova
decisão ou entrega.
