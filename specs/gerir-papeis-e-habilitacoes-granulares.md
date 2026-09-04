# Spec — UI de administração para papéis dinâmicos e habilitações granulares

Continuação do gap registrado em
[PDR-0019](../docs/decisions/PDR-0019-autorizacao-gerir-configuracoes.md#fora-do-escopo-desta-decisão)
e em [STATUS.md](../docs/STATUS.md) (linha Configurações): o kernel de
autorização (`PapelAcesso`, `UsuarioPapel`, `PermissaoPapel`,
`HabilitacaoPapel`, `PermissaoUsuario`, `HabilitacaoUsuario`) já existe,
está migrado e testado, mas só é operável via Django Admin. Não há
decisão de produto nova aqui — apenas construir UI própria do app sobre
modelo e regras já aprovados.

## Objetivo

Permitir que quem tem a habilitação `gerir_habilitar_terceiros` (ou é
Administrador do escritório) administre, pela UI de Configurações, sem
depender do Django Admin:

1. Papéis de acesso dinâmicos (`PapelAcesso`).
2. Atribuição de papéis a usuários (`UsuarioPapel`).
3. Módulo/nível (`PermissaoPapel`) e habilitações granulares por item
   (`HabilitacaoPapel`) de um papel dinâmico.
4. Overrides individuais por usuário (`PermissaoUsuario`,
   `HabilitacaoUsuario`).

## Comportamento esperado

### 1. Papéis (`PapelAcesso`)

- Nova tela lista todos os papéis do tenant (nome, descrição, ativo,
  preset ou personalizado).
- Criar papel: nome (único) + descrição + ativo.
- Editar papel: mesmo formulário. Se `protegido_sistema=True`
  (preset de fábrica), `codigo_preset` não é editável e a exclusão não
  é oferecida — mesma restrição já documentada no model, hoje só
  garantida por convenção; esta feature é o primeiro ponto de aplicação
  real dela pela interface.
- Desativar (não excluir fisicamente) é a forma de remover um papel
  personalizado de uso — segue o mesmo princípio de exclusão lógica já
  adotado em Clientes (PDR-0017/0018 desativar vs. excluir).
- Papel com `UsuarioPapel` ativo vinculado pode ser desativado (deixa
  de conceder acesso a partir da desativação); não pode ser excluído
  fisicamente enquanto o vínculo existir (`on_delete=PROTECT` já força
  isso no banco).

### 2. Atribuição de papel a usuário (`UsuarioPapel`)

- Na tela de edição de um papel (ou na tela de usuário — usar o padrão
  já existente em `equipe_membros` como referência de UX: lista +
  formulário de adicionar), listar usuários com o papel atribuído.
- Atribuir: seletor de usuário do tenant + papel. Não permite duplicar
  vínculo ativo (`UniqueConstraint` já impede no banco; a view trata o
  erro de forma amigável).
- Remover/desativar vínculo: reaproveita `ativo=False` (mesmo padrão de
  presença/ausência já usado em `HabilitacaoUsuario`), não exclusão
  física.
- Um usuário pode ter vários papéis simultâneos (já suportado no
  modelo); a UI deve listar todos, não assumir papel único.

### 3. Permissão de módulo/nível e habilitação granular por papel

- Estende a tela `configuracoes:permissoes` já existente: hoje as abas
  são fixas (Administrador/Limitado/Financeiro, por `tipo_conta`); passa
  a existir uma aba adicional por papel dinâmico ativo, usando o mesmo
  formulário de módulo+nível (`PermissaoPapel`) já implementado para
  `tipo_conta`.
- Adiciona ao mesmo formulário — hoje inexistente mesmo para
  `tipo_conta` — os itens de `HabilitacaoPapel` do módulo, quando o
  módulo estiver em `ITENS_POR_MODULO` com itens não vazios (ex.:
  `processos_criar`, `clientes_editar`). Isso vale tanto para as abas
  de `tipo_conta` existentes quanto para as novas abas de papel — hoje
  nenhuma das duas tem UI para habilitação granular, só Django Admin.
- Sem guarda de escalonamento de privilégio (um usuário com
  `gerir_habilitar_terceiros` pode conceder a um papel qualquer módulo/
  nível/habilitação, inclusive `gerir_habilitar_terceiros`, mesmo sem
  possuí-la ele mesmo) — mantém o comportamento já aceito e em produção
  na tela `permissoes` atual para `tipo_conta`; esta feature não muda
  essa regra, só estende o mesmo padrão para papel dinâmico e para
  habilitação granular.

### 4. Overrides individuais (`PermissaoUsuario`, `HabilitacaoUsuario`)

- Nova tela por usuário (a partir da lista de usuários do escritório)
  mostrando, por módulo, o valor herdado (via papel/tipo de conta) e
  permitindo criar um override: ativo/nível de módulo
  (`PermissaoUsuario`) e ativo por item de habilitação
  (`HabilitacaoUsuario`).
- Remover override restaura a herança — reaproveita exclusão da linha,
  já é o comportamento modelado.
- Mesma habilitação de acesso (`gerir_habilitar_terceiros`) controla
  esta tela.

## Regras de negócio relevantes

- Toda view nova checa, nesta ordem: `tem_permissao_modulo(user,
  MODULO_GERIR)` (já implícito) e `tem_habilitacao(user, MODULO_GERIR,
  HAB_GERIR_HABILITAR_TERCEIROS)` — mesmo padrão de `permissoes` já
  aplicado (PDR-0019). Bloqueio no backend, GET e POST.
- Administrador do escritório mantém bypass total via
  `habilitacao_efetiva`/`ctx.is_admin` já existente no kernel — nenhuma
  lógica nova necessária.
- Nenhuma habilitação nova é criada no kernel; nenhuma constraint de
  banco é alterada — toda a modelagem (`PapelAcesso`, `UsuarioPapel`,
  `PermissaoPapel`, `HabilitacaoPapel`, `PermissaoUsuario`,
  `HabilitacaoUsuario`) já existe e está testada.
- Precedência override individual > papel/tipo de conta já é garantida
  pelo kernel (`permissoes.py`) e não é tocada por esta feature — a UI
  só passa a permitir editar o que já tem efeito.
- Presets de fábrica (`protegido_sistema=True`): UI bloqueia exclusão e
  edição de `codigo_preset`; os demais campos (nome, descrição, ativo)
  continuam editáveis, salvo decisão em contrário registrada durante a
  execução.

## Fora do escopo

- Qualquer habilitação nova no kernel.
- Guarda de escalonamento de privilégio (delegador não pode conceder
  mais do que possui) — não existe hoje em nenhuma tela e não é criada
  aqui; se vier a ser necessária, exige registro de decisão à parte.
- `editar_escritorio` — continua exclusivo de Administrador (PDR-0019).
- Exclusão física de papel com vínculo ativo — já impedida pelo banco
  (`on_delete=PROTECT`), sem tratamento especial além de mensagem de
  erro amigável.
- Migração de `tipo_conta` legado (Limitado/Financeiro) para papel
  dinâmico — os dois sistemas continuam coexistindo como já modelado.
- Herança/hierarquia entre papéis, múltiplos tenants por papel, ou
  qualquer outra regra não já prevista no modelo atual.
- Mudança ao módulo Equipes, Processos ou qualquer outro módulo de
  negócio.

## Critérios de aceite

- Usuário sem `gerir_habilitar_terceiros` (e sem ser Administrador) não
  acessa nenhuma das telas novas (GET nem POST) — 403.
- Criar/editar/desativar papel dinâmico funciona pela UI, sem Django
  Admin.
- Preset de fábrica (`protegido_sistema=True`) não pode ser excluído
  nem ter `codigo_preset` alterado pela UI (tentativa direta por POST
  também é bloqueada no backend).
- Atribuir/desativar papel de um usuário funciona pela UI; usuário com
  múltiplos papéis ativos aparece corretamente refletido.
- Aba de papel dinâmico na tela de permissões salva `PermissaoPapel`
  (módulo/nível) e `HabilitacaoPapel` (itens) corretamente, com o mesmo
  comportamento de `update_or_create` já usado para `tipo_conta`.
- Override individual (`PermissaoUsuario`/`HabilitacaoUsuario`) criado
  pela UI passa a valer para o usuário, e removê-lo restaura o valor
  herdado — validado consultando o kernel (`tem_permissao_modulo`/
  `tem_habilitacao`) diretamente, não só a UI.
- Administrador do escritório continua acessando todas as telas novas
  sem depender de `gerir_habilitar_terceiros`.
- Testes de autorização (positivo/negativo, incluindo POST direto) em
  `apps/configuracoes/tests/test_autorizacao.py`, seguindo o padrão já
  usado para `permissoes`/`equipes`/`novo_usuario`.
