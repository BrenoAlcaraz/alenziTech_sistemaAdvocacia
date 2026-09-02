# Status — Breno - LawSystem

Estado real, gaps e próximos passos. Sem narrativa de auditoria — para
o "porquê" de uma regra, ver [PRODUCT.md](PRODUCT.md)/
[decisions/](decisions/); para o "como", ver [ARCHITECTURE.md](ARCHITECTURE.md).

## Plataforma

| Área | Estado | Gap principal |
|---|---|---|
| Multitenancy | Feito | Sem segregação de arquivo por tenant; sem teste automatizado de isolamento cross-tenant |
| Storage de arquivo (`MEDIA_ROOT`) | Parcial | `FileField`/`ImageField` são servidos por URL direta (`MEDIA_URL`) fora das views — sem checagem de autorização/escopo por request, independente do módulo. Views de app (ex.: `apps/financeiro`, solicitações financeiras) podem exigir autorização para linkar o arquivo, mas quem descobrir/adivinhar a URL direta contorna isso. Fica mais sensível à medida que mais módulos passam a anexar documento (hoje: avatar de usuário, boleto/comprovante de solicitação financeira). Correção real exige storage protegido (view autenticada servindo o arquivo, ou backend de storage que não responda a request direto) aplicado uniformemente — não é responsabilidade de um módulo isolado corrigir sozinho. |
| Autorização — kernel (`apps/accounts`) | Feito, testado (86 testes) | — |
| Autorização — aplicado nas views | Parcial | Clientes, Processos, Tarefas, Financeiro, Agenda, Chat e Modelos consultam o kernel; Laboratório (shell sem lógica de negócio) e Configurações usam só `@login_required`/`@requer_admin_escritorio`; Dashboard consulta o kernel em todos os blocos (clientes, processos, tarefas, agenda, financeiro) |
| Escopo de dados | Parcial | Só Clientes, Processos, Tarefas e Agenda filtram `QuerySet` por responsável (padrão em [ARCHITECTURE.md](ARCHITECTURE.md#autorização--padrão-a-reutilizar)) |
| Alteração de senha | Ausente | Botão existe na UI, sem rota/view por trás |

## Módulos

| Módulo | Estado | Gap principal |
|---|---|---|
| Clientes | Feito (autorização + escopo + responsabilidade) | Escopo por equipe é só placeholder visual; sem habilitação própria para desativar/reativar; sem UI de admin para papéis/habilitações |
| Processos | Feito (módulo, escopo, responsabilidade, apensos, Partes no modelo simplificado do PDR-0013, atribuição de responsável e integrantes habilitados do PDR-0014) | Demais habilitações granulares (`processos_criar`, `processos_editar`, `processos_andamento_adicionar`, `processos_usar_ia`, `processos_usar_laboratorio`) continuam fora desta versão (PDR-0010) |
| Tarefas | Feito (delegação PDR-0002 + autorização + escopo por responsável) | Notificação de conclusão (PDR-0016) ausente |
| Agenda | Parcial (autorização de módulo + escopo por responsável aplicados nas views) | Escopo por participante não existe (campo não exposto em `CompromissoForm`, sem regra de produto); notificação 15min antes (PDR-0016) ausente; integridade cliente-processo não validada no backend |
| Financeiro | Parcial (autorização de módulo + nível `solicitacoes`/`dados` aplicados nas views; Solicitações financeiras modeladas e com fluxo de estados — PDR-0006/PDR-0015) | Sem modalidade parcelado/recorrente real; Honorários sem modelagem própria; reabrir/excluir um lançamento gerado por solicitação paga é bloqueado por completo nas views — falta a habilitação própria com notificação ao solicitante já descrita em `financeiro.md` para permitir reabertura controlada |
| Dashboard | Parcial (autorização de módulo aplicada em todos os blocos) | Nenhum bloco filtra por escopo de responsável (nível `somente_seus`/`todos`) — todo usuário com acesso ao módulo vê os mesmos números agregados do escritório |
| Chat | Parcial (autorização de módulo aplicada) | Só sala global por tenant; conversas individuais/em grupo não existem |
| Modelos | Parcial (autorização de módulo aplicada) | "meu estilo" é texto estático; sem versionamento/categorização; habilitações `modelos_criar`/`modelos_editar_estilo` já existem no kernel mas não são aplicadas |
| Configurações | Parcial | Sem UI para papéis/habilitações; identidade visual só via Django Admin; `MODULO_GERIR` existe no kernel com habilitações equivalentes às views administrativas (`novo_usuario`, `equipes`, `permissoes`) mas nunca é consultado — essas views seguem restritas a `@requer_admin_escritorio`; delegar via `gerir` exigiria PDR próprio (só esboçado em `docs/prototipos/configuracoes-prototipo.html`) |
| IA / Laboratório | Não iniciado | Shell visual apenas; pré-requisitos do PDR-0008 não consolidados |

## Decisões em aberto

- **OPEN-001** — periodicidades financeiras da primeira versão (mensal/
  anual/parcelamento mensal vs. também semanal/quinzenal/trimestral/
  semestral/personalizada). Bloqueia detalhamento e migration de
  recorrência financeira. Sem decisão.

## Próximos passos

- Definir a próxima unidade de trabalho a partir das pendências já
  listadas acima — não antecipar qual, sem decisão do Product Owner.
- Autorização de módulo em Configurações — depende de decisão própria
  (PDR) sobre delegar as views administrativas via `MODULO_GERIR` em
  vez do `@requer_admin_escritorio` atual (ver gap principal do módulo
  acima).
