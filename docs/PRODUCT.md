# Produto — Breno - LawSystem

Sistema jurídico SaaS white label, multi-tenant. Cada escritório é um
tenant isolado por schema PostgreSQL; a plataforma SaaS (tenants,
planos, assinaturas) vive num schema público compartilhado. Monólito
modular Django — não microserviços; "módulo"/"app Django", nunca
"microserviço".

## Problema e proposta de valor

Escritórios de advocacia hoje fragmentam clientes, processos, tarefas,
agenda, financeiro e comunicação entre planilhas e sistemas isolados.
O produto centraliza essas rotinas num único ambiente, com acesso
controlado por papel/habilitação/escopo, isolamento entre tenants,
white label por escritório, e uma base de dados e permissões confiável
sobre a qual IA jurídica pode ser construída depois.

## Princípios

- núcleo funcional confiável antes de automação avançada;
- dados reais em vez de mocks operacionais;
- autorização aplicada no backend, nunca só na interface;
- isolamento entre tenants;
- integridade dos vínculos entre entidades;
- evolução incremental, sem reescrita total;
- IA aplicada somente sobre dados e permissões já consolidados.

## Dois produtos de IA (não confundir)

- **Assistente do sistema** — apoio ao uso do produto (navegação,
  dúvidas operacionais). Não é IA jurídica.
- **IA jurídica** — análise de processo/documentos, resumo, discussão
  de estratégia, geração/edição de peças. Apresentada pelo
  **Assistente/Laboratório** (painel no contexto do processo).
  Pré-requisitos antes de implementar: autorização aplicada, escopo de
  dados aplicado, isolamento de tenant, acesso seguro a documentos,
  dados processuais estruturados, histórico/rastreabilidade, módulos
  centrais estáveis. IA nunca amplia o escopo de acesso que o usuário
  já tem; sugestão de IA nunca vira registro definitivo sem confirmação
  humana.

## Glossário essencial

| Termo | Definição |
|---|---|
| Escritório / Tenant | Unidade isolada por schema PostgreSQL. |
| Administrador do escritório | Autoridade máxima dentro do tenant (`PerfilUsuario.is_admin_escritorio`). Distinto de Platform Admin (operador da plataforma SaaS, fora de qualquer tenant) e de superuser técnico do Django. |
| Papel de acesso | Controla autorização. Distinto de cargo profissional (só descritivo, sem efeito em permissão). |
| Habilitação | Capacidade específica dentro de um módulo já autorizado. Não é papel nem escopo. |
| Equipe | Agrupamento organizacional; usada como referência de escopo, não é mecanismo de autorização em si. "Departamento" é termo depreciado. |
| Gerente de equipe | Relação organizacional; não concede acesso global — depende de papel/habilitação/escopo aplicados no backend. |
| Escopo de dados | Quais registros, dentro de um módulo já autorizado, o usuário alcança. Distinto de autorização de módulo (se o módulo abre ou não). |
| Cliente | Pessoa física/jurídica atendida pelo escritório. Distinto de participante processual (qualquer papel formal num processo). |
| Processo apenso | Processo com identidade própria, relacionado simetricamente a outro; nenhum lado é principal/pai/filho; nada é herdado ou fundido. |

Termos históricos depreciados (não usar em decisão nova): "Perfil
mestre", "Departamento", "Grupo gerente", "Grupo advogado",
"microserviço" (para descrever um app).

## Módulos

Cada módulo abaixo: objetivo, regras de negócio que já são decisão
aprovada, e o que está fora de escopo. "Autorização e escopo de dados
devem ser aplicados no backend, nunca só ocultando elementos de
interface" vale para todos e não é repetido em cada um. Processos e
Financeiro têm arquivo próprio em `docs/modules/` por volume real de
regra (múltiplas decisões e sub-áreas); os demais cabem aqui.

### Clientes

Pasta canônica de clientes e seus vínculos com processos/documentos.

- Cadastro de Cliente é reaproveitado como participante de processo —
  nunca redigitado.
- Um processo pode ter vários clientes representados; um processo
  compartilhado não duplica entre pastas.
- Vínculo cliente-processo deve ser íntegro: servidor rejeita
  associação inconsistente mesmo com requisição manipulada; seletores
  dependentes de processo não oferecem processos incompatíveis com o
  cliente selecionado.
- Fora de escopo: dedup por CPF/CNPJ, exclusão física vs. lógica,
  cardinalidade de endereços/contatos — sem decisão aprovada.

### Tarefas

Delegação direta de trabalho, sem fluxo de aceite (PDR-0002).

- Tarefa aparece imediatamente para o destinatário ao ser criada/
  delegada; não existe status "recusada".
- Registra separadamente criador, atribuidor, destinatário da
  atribuição, data da atribuição e responsável atual — mesmo quando
  coincidem na mesma pessoa.
- Status: pendente, em andamento, concluída ou cancelada.
- Reatribuição preserva responsável anterior, novo responsável, autor
  e data — nunca sobrescrita silenciosa.
- Visibilidade: Administrador vê tudo; habilitação de gestão vê a
  equipe/escopo autorizado; usuário comum vê só o que criou ou lhe foi
  atribuído.
- Notificação (PDR-0016): ao concluir, o criador é notificado — exceto
  se o criador for o próprio responsável ou for a IA. Notificação de
  atribuição/reatribuição/prazo fica fora de escopo.
- Fora de escopo: aceite/recusa, gamificação, avaliação de desempenho.

### Agenda

Compromissos manuais e originados de processo, lista + calendário
mensal (mesmos dados, duas visões).

- Prazo processual relevante deve poder aparecer na agenda, preservando
  a referência de origem mesmo após edição.
- Notificação (PDR-0016): todo compromisso/prazo notifica automaticamente
  dentro do sistema 15 minutos antes, por verificação periódica em
  segundo plano, sem ação do usuário. Canais externos (e-mail/push/SMS)
  e antecedência configurável ficam fora de escopo.
- Sincronização bidirecional automática prazo↔evento não está
  claramente aprovada em nenhum PDR — não presumir esse comportamento.
- Fora de escopo: Google Calendar, múltiplos fusos, recorrência de
  evento.

### Equipes

Organização interna para distribuição de responsabilidade e escopo.

- Equipe, papel de acesso e cargo profissional são conceitos distintos.
- Gerente de equipe não ganha acesso global só por ser gerente.
- Gestão de equipe restrita a papéis administrativos, aplicada no
  backend.
- Em aberto (sem decisão aprovada): múltiplas equipes por usuário,
  hierarquia/aninhamento entre equipes, herança de permissão entre
  equipes, desativação de equipe e seus efeitos.

### Dashboard

Indicadores operacionais/jurídicos/financeiros/gerenciais sobre dados
reais e autorizados — nunca mock ou número fixo.

- Cada indicador respeita autorização e escopo do usuário que consulta;
  ocultar um card na interface não substitui a filtragem no backend.
- Indicadores financeiros seguem previsto/realizado (PDR-0004).
- Processo sem movimentação usa a data do último andamento como
  referência.
- Fora de escopo: ranking/avaliação automática de desempenho,
  predição por IA, analytics avançado antes da consolidação do núcleo.

### Chat

Comunicação interna dentro do mesmo tenant.

- Nenhuma conversa atravessa tenant.
- Conversas individuais e em grupo são conceitos distintos (nem toda
  já implementada).
- Acesso a mensagens/anexos verificado no backend — conhecer o
  identificador não concede acesso.
- Equipe não gera grupo de chat automaticamente.
- Fora de escopo: chamada de áudio/vídeo, integração com apps externos,
  IA dentro do chat.

### Modelos

Repositório de modelos de peças/documentos reutilizáveis.

- Acervo é sempre institucional: usuário autorizado ao módulo alcança
  todos os modelos do tenant, não só os próprios (sem nível
  `somente_seus`/`todos` — decisão de 2026-08-31, tratado como
  Chat/Gerir).
- Upload manual não depende de IA; integração com IA é futura (PDR-0008)
  e nunca salva definitivo sem confirmação humana.
- Reutilizar um modelo não altera o original.
- Fora de escopo: dedup automática, geração em massa, edição
  colaborativa em tempo real.

### Configurações

Perfil pessoal, gestão administrativa de usuários/papéis/habilitações/
equipes, identidade do escritório, consulta ao plano SaaS.

- Alteração de senha usa o fluxo seguro do Django.
- Gerente de equipe não ganha acesso global só por essa indicação.
- Administração de usuários/acesso nunca atravessa tenant.
- Plano/Assinatura pertencem a `saas_billing` (billing SaaS
  compartilhado); Configurações pode exibir/gerir conforme autorização,
  mas isso não gera lançamento no Financeiro do tenant — integração
  financeira futura exigiria novo PDR (PDR-0003).
- Administração da plataforma SaaS é do Platform Admin, não do
  Administrador do escritório.
- Fora de escopo: exclusão física de usuário, enforcement automático de
  limite de plano, upgrade/downgrade completo.

### Inteligência Artificial

Ver "Dois produtos de IA" acima e
[PDR-0008](decisions/PDR-0008-ia-apos-nucleo-funcional.md). Nenhuma
funcionalidade essencial do núcleo (Clientes, Processos, Tarefas,
Agenda, Financeiro) exige IA para operar. Honorário sugerido por IA
depende de confirmação humana (PDR-0007); resultado de IA nunca amplia
acesso a documento que o usuário não tivesse antes.

## Fora de escopo do produto (consolidação atual)

- transformar os apps em microserviços;
- reescrita total da aplicação;
- depender de IA para regra básica de negócio;
- decisão técnica duradoura sem PDR/ADR;
- IA sobre dados sem autorização e rastreabilidade prévias.

## Referências

- Decisões formais: [decisions/](decisions/)
- Estado atual e gaps: [STATUS.md](STATUS.md)
- Arquitetura e padrões técnicos: [ARCHITECTURE.md](ARCHITECTURE.md)
- Módulos com arquivo próprio: [modules/processos.md](modules/processos.md), [modules/financeiro.md](modules/financeiro.md)
