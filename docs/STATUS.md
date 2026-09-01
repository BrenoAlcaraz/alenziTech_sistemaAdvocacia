# Status — Breno - LawSystem

Estado real, gaps e próximos passos. Sem narrativa de auditoria — para
o "porquê" de uma regra, ver [PRODUCT.md](PRODUCT.md)/
[decisions/](decisions/); para o "como", ver [ARCHITECTURE.md](ARCHITECTURE.md).

## Plataforma

| Área | Estado | Gap principal |
|---|---|---|
| Multitenancy | Feito | Sem segregação de arquivo por tenant; sem teste automatizado de isolamento cross-tenant |
| Autorização — kernel (`apps/accounts`) | Feito, testado (86 testes) | — |
| Autorização — aplicado nas views | Parcial | Clientes, Processos e Tarefas consultam o kernel; Agenda/Financeiro/Dashboard/Chat/Modelos/Laboratório/Configurações usam só `@login_required` |
| Escopo de dados | Parcial | Só Clientes, Processos e Tarefas filtram `QuerySet` por responsável (padrão em [ARCHITECTURE.md](ARCHITECTURE.md#autorização--padrão-a-reutilizar)) |
| Alteração de senha | Ausente | Botão existe na UI, sem rota/view por trás |

## Módulos

| Módulo | Estado | Gap principal |
|---|---|---|
| Clientes | Feito (autorização + escopo + responsabilidade) | Escopo por equipe é só placeholder visual; sem habilitação própria para desativar/reativar; sem UI de admin para papéis/habilitações |
| Processos | Feito (módulo, escopo, responsabilidade, apensos) | Partes usa modelo de 3 dimensões (PDR-0001/0011) que PDR-0013 já substituiu — simplificação pendente; `processos_atribuir_responsavel`/integrante habilitado (PDR-0014) não implementados; habilitação granular deliberadamente fora desta versão (PDR-0010) |
| Tarefas | Feito (delegação PDR-0002 + autorização + escopo por responsável) | Notificação de conclusão (PDR-0016) ausente |
| Agenda | Parcial | Sem escopo por responsável/participante; notificação 15min antes (PDR-0016) ausente; integridade cliente-processo não validada no backend |
| Financeiro | Parcial | Sem modalidade parcelado/recorrente real; Solicitações e Honorários sem modelagem própria; sem distinção de acesso ao caixa geral; sem autorização |
| Dashboard | Parcial | Agrega dados reais, mas sem filtro de escopo/autorização — todo usuário vê os mesmos totais, incluindo financeiro |
| Chat | Parcial | Só sala global por tenant; conversas individuais/em grupo não existem |
| Modelos | Parcial | Sem autorização de módulo aplicada; "meu estilo" é texto estático; sem versionamento/categorização |
| Configurações | Parcial | Sem UI para papéis/habilitações; identidade visual só via Django Admin |
| IA / Laboratório | Não iniciado | Shell visual apenas; pré-requisitos do PDR-0008 não consolidados |

## Decisões em aberto

- **OPEN-001** — periodicidades financeiras da primeira versão (mensal/
  anual/parcelamento mensal vs. também semanal/quinzenal/trimestral/
  semestral/personalizada). Bloqueia detalhamento e migration de
  recorrência financeira. Sem decisão.

## Próximos passos

- Definir a próxima unidade de trabalho a partir das pendências já
  listadas acima — não antecipar qual, sem decisão do Product Owner.
- Simplificação do modelo de Partes de Processos (PDR-0013 já substituiu
  o que está implementado).
- `processos_atribuir_responsavel` + integrante habilitado (PDR-0014).
- Autorização de módulo nos demais módulos operacionais (Agenda,
  Financeiro, Dashboard, Chat, Modelos, Configurações).
