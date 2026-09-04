# Status — Breno - LawSystem

Estado real, gaps e próximos passos. Sem narrativa de auditoria — para
o "porquê" de uma regra, ver [PRODUCT.md](PRODUCT.md)/
[decisions/](decisions/); para o "como", ver [ARCHITECTURE.md](ARCHITECTURE.md).

## Plataforma

| Área | Estado | Gap principal |
|---|---|---|
| Multitenancy | Feito, testado | — |
| Storage de arquivo (`MEDIA_ROOT`) | Feito, testado (namespaces por tenant; arquivos protegidos sem URL pública; identidade visual pública resolvida pelo tenant) | — |
| Autorização — kernel (`apps/accounts`) | Feito, testado (86 testes) | — |
| Autorização — aplicado nas views | Parcial | Clientes, Processos, Tarefas, Financeiro, Agenda, Chat, Modelos e Configurações (`novo_usuario`, `equipes` e sub-rotas, `permissoes` — PDR-0019) consultam o kernel; Laboratório (shell sem lógica de negócio) usa só `@login_required`; Dashboard consulta o kernel na própria rota (`MODULO_PAINEL`) e em todos os blocos (clientes, processos, tarefas, agenda, financeiro) |
| Escopo de dados | Parcial | Clientes, Processos, Tarefas, Agenda e Financeiro (`LancamentoFinanceiro`, nível `dados_proprios`/`dados_todos`) filtram `QuerySet` por responsável (padrão em [ARCHITECTURE.md](ARCHITECTURE.md#autorização--padrão-a-reutilizar)); Modelos e Chat ainda não |

## Módulos

| Módulo | Estado | Gap principal |
|---|---|---|
| Clientes | Feito (autorização + escopo + responsabilidade + habilitações `clientes_criar`/`clientes_editar`/`clientes_desativar`/`clientes_reativar` aplicadas) | Escopo por equipe é só placeholder visual; sem UI de admin para papéis/habilitações |
| Processos | Feito (módulo, escopo, responsabilidade, apensos, Partes no modelo simplificado do PDR-0013, atribuição de responsável e integrantes habilitados do PDR-0014, habilitações `processos_criar`/`processos_editar`/`processos_andamento_adicionar` aplicadas do PDR-0017) | `processos_usar_ia` e `processos_usar_laboratorio` continuam fora desta versão (PDR-0010, PDR-0008) |
| Tarefas | Feito (delegação PDR-0002 + autorização + escopo por responsável + notificação de conclusão PDR-0016) | — |
| Agenda | Parcial (autorização de módulo + escopo por responsável aplicados nas views; lembrete automático 15min antes — PDR-0016) | Escopo por participante não existe (campo não exposto em `CompromissoForm`, sem regra de produto); integridade cliente-processo não validada no backend |
| Financeiro | Parcial (autorização de módulo + nível `solicitacoes`/`dados_proprios`/`dados_todos` aplicados nas views; `LancamentoFinanceiro` escopado por responsável em `dados_proprios` — leitura, totais e mutação, no módulo e no bloco financeiro do Dashboard; Solicitações financeiras modeladas e com fluxo de estados — PDR-0006/PDR-0015; reabrir lançamento gerado por solicitação paga exige a habilitação própria `financeiro_reabrir_lancamento_pago` e notifica o solicitante; Honorários modelados com fluxo `previsto`/`recebido`/`cancelado` — PDR-0007, confirmar recebimento é exclusivo do Administrador do escritório, que notifica o advogado responsável pelo processo) | Sem modalidade parcelado/recorrente real; excluir um lançamento gerado por solicitação paga continua bloqueado por completo nas views — sem regra de produto definida para esse caso |
| Dashboard | Feito (autorização de módulo + escopo de responsável `somente_seus`/`todos` aplicados em todos os blocos; bloco financeiro exige nível `dados_proprios`/`dados_todos`, escopado por responsável em `dados_proprios`; acesso à própria rota `/painel/` exige `MODULO_PAINEL`) | Nível `somente_seus`/`todos` de `MODULO_PAINEL` segue sem efeito definido — cada bloco já tem escopo próprio pelo módulo de origem; sem regra de produto que dê significado a esse nível para o painel em si |
| Chat | Parcial (autorização de módulo aplicada) | Só sala global por tenant; conversas individuais/em grupo não existem |
| Modelos | Parcial (autorização de módulo + `modelos_criar` aplicada em `novo`/`importar`; banco compartilhado — listar/abrir sempre total, sem filtro por autor; edição/exclusão exigem autoria ou habilitação granular `modelos_editar_alheio`/`modelos_excluir_alheio` — PDR-0018; Administrador mantém bypass; editar/excluir peça alheia notifica o autor original) | `NIVEIS_POR_MODULO[MODULO_MODELOS]` (`somente_seus`/`todos`) permanece definido no kernel sem efeito prático — Modelos nunca teve escopo de leitura por usuário, é banco compartilhado por decisão de produto (PDR-0018); mudar isso tocaria `CheckConstraint` de banco, fora de escopo até haver necessidade real; "meu estilo" é texto estático, sem view própria de edição — por isso a habilitação `modelos_editar_estilo` (já existente no kernel) segue sem nenhum ponto de aplicação; sem versionamento/categorização |
| Configurações | Parcial | UI própria do app cobre criar usuário (`novo_usuario`), equipes (`equipes`/criar/editar/membros/gerente) e permissões de módulo+nível por tipo de conta fixo — Limitado/Financeiro (`permissoes`), além de identidade visual; as três primeiras já consultam o kernel via `MODULO_GERIR` — `gerir_criar_usuario`, `gerir_criar_equipe` e `gerir_habilitar_terceiros` (PDR-0019), delegáveis a qualquer papel/usuário com a habilitação; Administrador mantém bypass total; identidade visual (`editar_escritorio`) segue exclusiva de `@requer_admin_escritorio`, sem habilitação correspondente | Sem UI própria para papéis dinâmicos (`PapelAcesso`) além dos dois tipos de conta fixos, habilitações granulares por item (`HabilitacaoPapel`/`HabilitacaoUsuario`) e overrides individuais (`PermissaoUsuario`) — conceder as habilitações de `gerir` a um papel/usuário segue só via Django Admin; `editar_escritorio` continua sem forma de delegação |
| IA / Laboratório | Não iniciado | Shell visual apenas; pré-requisitos do PDR-0008 não consolidados |

## Decisões em aberto

- **OPEN-001** — periodicidades financeiras da primeira versão (mensal/
  anual/parcelamento mensal vs. também semanal/quinzenal/trimestral/
  semestral/personalizada). Bloqueia detalhamento e migration de
  recorrência financeira. Sem decisão.
- **OPEN-002** — ciclo de vida de tenant inadimplente (evolução de
  `Assinatura.status`, hoje sem uso real). Decidido: régua por dias sem
  pagamento identificado — dia 1-7: acesso normal + aviso no topo da
  tela; dia 8-30: somente leitura, bloqueando escrita para todos os
  usuários sem exceção (inclusive Admin do escritório); a partir do dia
  31: acesso bloqueado, dados retidos por mais 90 dias (retomada de onde
  parou se o pagamento for identificado nesse período). Cada faixa passa
  a valer no dia exato do limite. Antes do expurgo final, oferecer
  exportação dos dados ao escritório, com aviso. Pendente: (1) validação
  jurídica do prazo de retenção pós-cancelamento frente à obrigação
  própria do escritório de guardar processo/documento; (2) validação
  jurídica se anonimização (em vez de hard delete) atende à LGPD sem
  esvaziar o propósito de defesa jurídica da própria plataforma; (3)
  confirmação de escopo do registro de acesso exigido pelo art. 15 do
  Marco Civil da Internet (retenção de 6 meses de IP/timestamp de
  acesso — distinto de auditoria completa de ações). Bloqueia
  integração de gateway de pagamento (pré-requisito técnico) + as três
  validações jurídicas acima. Sem essas peças, não vira PDR.

## Próximos passos

- Definir a próxima unidade de trabalho a partir das pendências já
  listadas acima — não antecipar qual, sem decisão do Product Owner.
