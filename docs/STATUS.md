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
| Autorização — aplicado nas views | Parcial | Clientes, Processos, Tarefas, Financeiro, Agenda, Chat e Modelos consultam o kernel; Laboratório (shell sem lógica de negócio) e Configurações usam só `@login_required`/`@requer_admin_escritorio`; Dashboard consulta o kernel em todos os blocos (clientes, processos, tarefas, agenda, financeiro) |
| Escopo de dados | Parcial | Clientes, Processos, Tarefas, Agenda e Financeiro (`LancamentoFinanceiro`, nível `dados_proprios`/`dados_todos`) filtram `QuerySet` por responsável (padrão em [ARCHITECTURE.md](ARCHITECTURE.md#autorização--padrão-a-reutilizar)); Modelos e Chat ainda não |

## Módulos

| Módulo | Estado | Gap principal |
|---|---|---|
| Clientes | Feito (autorização + escopo + responsabilidade) | Escopo por equipe é só placeholder visual; sem habilitação própria para desativar/reativar; sem UI de admin para papéis/habilitações |
| Processos | Feito (módulo, escopo, responsabilidade, apensos, Partes no modelo simplificado do PDR-0013, atribuição de responsável e integrantes habilitados do PDR-0014, habilitações `processos_criar`/`processos_editar`/`processos_andamento_adicionar` aplicadas do PDR-0017) | `processos_usar_ia` e `processos_usar_laboratorio` continuam fora desta versão (PDR-0010, PDR-0008) |
| Tarefas | Feito (delegação PDR-0002 + autorização + escopo por responsável + notificação de conclusão PDR-0016) | — |
| Agenda | Parcial (autorização de módulo + escopo por responsável aplicados nas views; lembrete automático 15min antes — PDR-0016) | Escopo por participante não existe (campo não exposto em `CompromissoForm`, sem regra de produto); integridade cliente-processo não validada no backend |
| Financeiro | Parcial (autorização de módulo + nível `solicitacoes`/`dados_proprios`/`dados_todos` aplicados nas views; `LancamentoFinanceiro` escopado por responsável em `dados_proprios` — leitura, totais e mutação, no módulo e no bloco financeiro do Dashboard; Solicitações financeiras modeladas e com fluxo de estados — PDR-0006/PDR-0015; reabrir lançamento gerado por solicitação paga exige a habilitação própria `financeiro_reabrir_lancamento_pago` e notifica o solicitante) | Sem modalidade parcelado/recorrente real; Honorários sem modelagem própria; excluir um lançamento gerado por solicitação paga continua bloqueado por completo nas views — sem regra de produto definida para esse caso |
| Dashboard | Feito (autorização de módulo + escopo de responsável `somente_seus`/`todos` aplicados em todos os blocos; bloco financeiro exige nível `dados_proprios`/`dados_todos`, escopado por responsável em `dados_proprios`) | `MODULO_PAINEL` existe no kernel (níveis `somente_seus`/`todos`) mas nenhuma view o consulta — acesso à rota `/painel/` em si segue só `@login_required`, sem autorização de módulo própria; cada bloco continua gated pelo módulo de origem (Clientes/Processos/Tarefas/Agenda/Financeiro) |
| Chat | Parcial (autorização de módulo aplicada) | Só sala global por tenant; conversas individuais/em grupo não existem |
| Modelos | Parcial (autorização de módulo + habilitação `modelos_criar` aplicadas em `novo`/`importar`) | "meu estilo" é texto estático, sem view própria de edição — por isso a habilitação `modelos_editar_estilo` (já existente no kernel) segue sem nenhum ponto de aplicação; sem versionamento/categorização |
| Configurações | Parcial | UI própria do app já cobre criar usuário (`novo_usuario`), equipes (`equipes`/criar/editar/membros/gerente) e permissões de módulo+nível por tipo de conta fixo — Limitado/Financeiro (`permissoes`), além de identidade visual; mas essas views seguem restritas a `@requer_admin_escritorio` — `MODULO_GERIR` existe no kernel com habilitações equivalentes (`novo_usuario`, `equipes`, `permissoes`) mas nunca é consultado, então não dá pra delegar esse acesso via papel/permissão; delegar via `gerir` exigiria PDR próprio (só esboçado em `docs/prototipos/configuracoes-prototipo.html`). Sem UI própria para papéis dinâmicos (`PapelAcesso`) além dos dois tipos de conta fixos, habilitações granulares por item (`HabilitacaoPapel`/`HabilitacaoUsuario`) e overrides individuais (`PermissaoUsuario`) — essas partes seguem só via Django Admin |
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
- Autorização de módulo em Configurações — depende de decisão própria
  (PDR) sobre delegar as views administrativas via `MODULO_GERIR` em
  vez do `@requer_admin_escritorio` atual (ver gap principal do módulo
  acima).
