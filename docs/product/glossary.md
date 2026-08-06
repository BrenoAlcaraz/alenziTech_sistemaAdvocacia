---
title: Glossário funcional
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Glossário funcional

## Objetivo

Este glossário define os termos funcionais e jurídicos utilizados nas
especificações de módulo do Breno - LawSystem
(`docs/product/modules/`). Ele trata do domínio funcional do produto —
como as entidades, relações e estados devem ser entendidos ao ler ou
escrever uma especificação — e não da nomenclatura arquitetural do
sistema.

Este documento complementa, sem duplicar integralmente,
[../governance/terminology-policy.md](../governance/terminology-policy.md).
Para nomes arquiteturais e termos oficiais do produto (por exemplo,
nome do produto, estilo arquitetural, nomenclatura de tenant e schema,
ou a lista de termos históricos depreciados), a política de
terminologia prevalece. Este glossário existe para impedir que agentes
humanos ou de IA confundam entidades, relações e estados ao redigir ou
interpretar especificações funcionais.

## Identidade e organização

| Termo | Definição | Observação ou distinção |
| --- | --- | --- |
| Escritório | Unidade organizacional que contrata e opera o sistema; sinônimo de tenant no domínio de negócio. | Ver `docs/governance/terminology-policy.md` para a definição arquitetural de tenant. |
| Tenant | Escritório de advocacia isolado por schema PostgreSQL na plataforma. | Termo arquitetural; definição canônica em terminology-policy.md. |
| Usuário | Pessoa autenticada no sistema, vinculada a uma conta dentro de um tenant. | Não deve ser confundido com PerfilUsuario, que é um registro complementar. |
| PerfilUsuario | Registro complementar vinculado ao usuário para informações e características específicas de seu perfil dentro do tenant. | Não substitui o usuário autenticável, o papel de acesso ou a matriz de autorização. Sua estrutura técnica será descrita na documentação de arquitetura. |
| Administrador do escritório | Autoridade administrativa máxima dentro de um tenant. | Distinto de Platform Admin e de superusuário técnico; ver terminology-policy.md. |
| Platform Admin | Operador administrativo da plataforma SaaS, fora do escopo de um tenant específico. | Não se confunde com Administrador do escritório. |
| Papel de acesso | Controla a autorização do usuário dentro do sistema — o que ele pode acessar e executar. | Distinto de cargo profissional, que é apenas descritivo. |
| Habilitação | Capacidade funcional específica associada por papel de acesso ou por regra individual, conforme a política de autorização. | Não é sinônimo de papel de acesso, permissão de ação ou escopo de dados. A precedência entre regras de papel e individuais pertence à documentação de autorização. |
| Cargo profissional | Descrição informativa da função da pessoa no escritório (por exemplo, "Advogada Sênior"). | Não controla permissões nem substitui papel de acesso. |
| Equipe | Agrupamento organizacional de usuários dentro de um tenant, usado para distribuição de responsabilidade e referência de escopo. | Termo canônico; substitui o termo histórico "departamento". |
| Membro de equipe | Usuário vinculado a uma equipe. | Um usuário pode ou não pertencer a uma equipe; ver [equipes.md](modules/equipes.md) para pontos ainda não decididos sobre múltiplas equipes. |
| Gerente de equipe | Relação organizacional de responsabilidade de um usuário sobre uma equipe específica. | Não é, por si só, um papel de acesso global; acesso amplo depende de papel, habilitação e escopo. |
| Escopo de dados | Determina, dentro dos módulos que um usuário já está autorizado a acessar, quais registros específicos ele pode alcançar. | Autorização de módulo e escopo de dados são conceitos distintos: um define se o módulo é acessível, o outro define quais registros dentro dele. |

Regras obrigatórias:

- Papel de acesso controla autorização; cargo profissional é apenas
  descritivo e não tem efeito sobre permissões.
- Equipe é uma relação organizacional, não um mecanismo de
  autorização em si.
- Gerente de equipe não é automaticamente um papel de acesso global;
  o alcance de um gerente depende de papel, habilitação e escopo de
  dados aplicados no backend.
- Escopo de dados determina quais registros autorizados um usuário
  pode alcançar dentro de um módulo já acessível a ele.
- Autorização de módulo (o que um usuário pode abrir) e escopo de
  dados (quais registros ele vê dentro do módulo) não são a mesma
  coisa.

## Clientes e processos

| Termo | Definição | Observação ou distinção |
| --- | --- | --- |
| Cliente | Pessoa física ou jurídica atendida pelo escritório. | Distinto de participante processual, que é um conceito mais amplo. |
| Pasta do cliente | Espaço que reúne os dados, documentos e processos relacionados a um cliente. | Não é uma entidade de banco separada por definição; é a visão organizada dos dados do cliente. |
| Processo judicial | Processo tramitando perante um órgão do Poder Judiciário. | Ver processo apenso para processos tecnicamente vinculados a outro. |
| Caso extrajudicial | Atendimento conduzido pelo escritório fora do âmbito de um processo judicial formal (por exemplo, consultivo ou administrativo). | Compartilha conceitos com o processo judicial quando aplicável, mas não tramita perante o Judiciário. |
| Cliente representado | Cliente do escritório que figura como participante em um processo, com representação pelo escritório indicada nesse vínculo. | Reaproveita o cadastro de Cliente; não gera um cadastro duplicado. |
| Cliente relacionado | Cliente cuja relação com outro cliente é derivada por eles compartilharem um mesmo processo. | Não é um vínculo cadastrado manualmente entre clientes; é derivado dos processos compartilhados. |
| Participante processual | Qualquer pessoa ou entidade com papel formal em um processo (cliente representado, parte contrária, terceiro, Ministério Público, entre outros). | Não é sinônimo automático de cliente. |
| Pessoa externa | Pessoa ou entidade envolvida em um processo que não é cliente do escritório (parte contrária, terceiro, representante externo). | Pode ser pessoa física, pessoa jurídica ou órgão público. |
| Vínculo com o escritório | Dimensão do participante que indica se ele é cliente representado, parte contrária ou outro tipo de relação com o escritório. | Uma das três dimensões separadas exigidas por PDR-0001, junto com posição estrutural e qualificação processual. |
| Posição estrutural | Dimensão mais estável do vínculo processual de um participante: polo ativo, polo passivo, terceiro, ou atuação específica do Ministério Público. | Não deve ser confundida com qualificação processual, que é o nome jurídico exercido naquele processo ou fase. |
| Polo ativo | Posição estrutural ocupada no lado ativo da relação processual. | Pode conter uma ou várias pessoas e não determina, por si só, o vínculo da pessoa com o escritório. |
| Polo passivo | Posição estrutural ocupada no lado passivo da relação processual. | Pode conter uma ou várias pessoas e não é sinônimo automático de parte contrária ao escritório. |
| Terceiro | Participante processual que não integra o polo ativo nem o polo passivo, mas possui interesse ou papel formal no processo. | Distinto de representante e de autoridade processual. |
| Ministério Público como parte | Atuação do Ministério Público quando ele figura como parte do processo. | Uma das duas formas de atuação previstas pelo PDR-0001. |
| Ministério Público como fiscal da ordem jurídica | Atuação do Ministério Público quando ele intervém no processo na função de fiscalização, sem ser parte. | Distinta da atuação como parte; ambas devem ser representáveis. |
| Qualificação processual | Nome jurídico exercido pelo participante naquele processo ou fase (requerente, requerido, exequente, executado, agravante, agravado, entre outros). | É a dimensão que pode variar entre fases e recursos; não deve ser confundida com posição estrutural. |
| Representante | Advogado ou procurador que representa um participante no processo. | Não é uma parte do processo; está sempre vinculado a um participante. |
| Advogado interno | Representante que é usuário ou membro de equipe já cadastrado no escritório. | Reaproveita o cadastro existente; não gera uma ficha independente. |
| Advogado externo | Representante que não pertence ao escritório. | Cadastro principal: nome, OAB, UF da OAB, telefone e e-mail; CPF não é obrigatório. |
| Autoridade processual | Agente do processo com função decisória, como juiz. | Registrada separadamente das partes; não pertence ao grupo dos participantes-partes. |
| Processo principal | Processo ao qual um processo apenso permanece vinculado. | Referência central do vínculo de apenso. |
| Processo apenso | Processo com identificação própria, tecnicamente vinculado a um processo principal. | Continua sendo um processo próprio; seus dados não devem ser fundidos com os do processo principal. |
| Andamento processual | Evento registrado na tramitação de um processo. | Distinto de fase processual e de status processual. |
| Documento processual | Arquivo ou registro anexado ao processo, servindo como evidência ou registro formal da tramitação. | Sua existência não depende de identificação por IA. |
| Fase processual | Etapa do rito processual em que o processo se encontra. | Distinta de andamento processual e de status processual. |
| Status processual | Situação corrente do processo. | Distinta de fase processual e de andamento processual; a lista canônica definitiva de valores ainda não foi decidida — ver [processos.md](modules/processos.md). |
| Prazo processual | Data ou intervalo relevante decorrente da tramitação de um processo, com potencial repercussão na agenda. | Ver também prazo de agenda, na seção "Tarefas e agenda". |

Regras obrigatórias:

- Participante processual não é sinônimo de cliente.
- Representante não é parte do processo.
- Autoridade processual não pertence ao grupo das partes.
- Posição estrutural não é igual a qualificação processual.
- Uma mudança de qualificação processual não cria uma nova pessoa; o
  mesmo participante mantém sua identidade.
- Clientes relacionados são derivados de processos compartilhados —
  não são cópias uns dos outros nem um vínculo cadastrado
  manualmente.
- Um processo apenso é um processo próprio, ligado a outro processo
  principal; não é o mesmo processo com outro nome.

## Tarefas e agenda

| Termo | Definição | Observação ou distinção |
| --- | --- | --- |
| Tarefa | Unidade de trabalho atribuída a um usuário dentro do escritório. | Funciona como uma ordem ou atribuição direta de trabalho; ver [tarefas.md](modules/tarefas.md). |
| Criador | Usuário que criou o registro da tarefa. | Registrado separadamente do atribuidor, mesmo quando coincidem. |
| Atribuidor | Usuário que atribuiu a tarefa a um destinatário. | Distinto de criador e de responsável atual, mesmo quando a mesma pessoa acumula os papéis. |
| Destinatário da atribuição | Usuário para quem a tarefa foi atribuída no momento da atribuição. | Pode divergir do responsável atual após uma reatribuição. |
| Responsável atual | Usuário responsável pela tarefa no momento presente. | Pode mudar por reatribuição, preservando o histórico mínimo exigido. |
| Delegação direta | Modelo de atribuição de tarefa em que a tarefa passa a existir para o destinatário assim que é criada ou delegada, sem fluxo de aceite. | Não existe status de aceite nem de recusa nesta versão; ver PDR-0002. |
| Reatribuição | Ato de alterar o responsável atual de uma tarefa. | Deve preservar responsável anterior, novo responsável, autor da alteração e data, sem sobrescrita silenciosa. |
| Prazo da tarefa | Data limite associada a uma tarefa. | Distinto de prazo de agenda e de prazo processual. |
| Compromisso | Registro de agenda representando um evento, reunião, audiência, perícia ou outro tipo de ocorrência agendada. | Pode ser manual ou originado de processo. |
| Prazo de agenda | Data relevante registrada na agenda, podendo refletir um prazo processual. | Ver prazo processual, na seção "Clientes e processos". |
| Evento originado de processo | Compromisso cuja origem é um prazo ou dado do processo. | Deve preservar a referência à sua origem processual. |
| Evento manual | Compromisso criado diretamente na agenda, sem origem em um processo. | Não possui vínculo de origem processual a preservar. |

## Financeiro

Mesmo que o módulo Financeiro seja detalhado em especificação de
módulo em lote futuro, os termos abaixo já são estáveis por estarem
formalizados nos PDRs aceitos (PDR-0003 a PDR-0007). Este glossário
não resolve [OPEN-001](open-decisions.md#open-001--periodicidades-financeiras-da-primeira-versão)
nem [OPEN-002](open-decisions.md#open-002--etapas-de-aprovação-das-solicitações-financeiras).
Plano e assinatura SaaS pertencem ao billing compartilhado e não geram
automaticamente lançamento no Financeiro operacional do escritório.

| Termo | Definição | Observação ou distinção |
| --- | --- | --- |
| Financeiro geral | Área funcional que representa receitas e despesas operacionais do escritório. | Custas judiciais não são uma categoria do financeiro geral; ver PDR-0003. |
| Custa judicial | Valor pago a tribunais para movimentar um processo, controlado em área própria com saldo por cliente. | Ver PDR-0005; distinta de despesa comum do escritório. |
| Solicitação de pagamento | Pedido feito por um usuário sem acesso ao caixa geral para que o Financeiro processe um pagamento. | Ver PDR-0006; não gera despesa realizada automaticamente ao ser criada. |
| Solicitação de reembolso | Pedido feito por um usuário sem acesso ao caixa geral para reaver um gasto profissional próprio. | Ver PDR-0006. |
| Honorário | Registro manual de valor a receber pelo escritório vinculado a processo e, quando aplicável, a cliente. | Não depende de IA para existir; ver PDR-0007. |
| Lançamento único | Modalidade de lançamento financeiro que não se repete nem se parcela. | Ver PDR-0003. |
| Lançamento parcelado | Modalidade de lançamento financeiro dividida em parcelas a partir de quantidade, periodicidade e primeiro vencimento. | Gera ocorrências individuais vinculadas à mesma origem; ver PDR-0003. |
| Lançamento recorrente | Modalidade de lançamento financeiro que se repete por periodicidade, com data final, duração ou prazo indeterminado. | Cada ocorrência nasce como lançamento independente; ver PDR-0003. |
| Ocorrência | Cada instância individual gerada por um lançamento parcelado ou recorrente. | Identificável individualmente; seu cancelamento ou confirmação não reescreve as demais. |
| Competência | Data que posiciona um lançamento no período a que ele pertence. | Obrigatória para todo lançamento; ver PDR-0004. |
| Vencimento | Data limite para pagamento ou recebimento de um lançamento pendente, parcela ou ocorrência recorrente. | Pode não se aplicar a um lançamento já realizado, desde que existam competência e data de realização; ver PDR-0004. |
| Previsto | Dimensão do lançamento financeiro que ainda não foi confirmado como pago ou recebido. | Não altera o saldo realizado; ver PDR-0004. |
| Realizado | Dimensão do lançamento financeiro após confirmação efetiva de pagamento ou recebimento. | Único estado que altera o saldo realizado; ver PDR-0004. |
| Saldo realizado | Indicador financeiro calculado exclusivamente a partir de lançamentos confirmados. | Ver PDR-0004. |
| Saldo previsto | Indicador financeiro que reflete lançamentos ainda pendentes. | Ver PDR-0004. |
| Crédito de custas | Valor depositado por um cliente para cobrir custas judiciais futuras. | Parte da fórmula do saldo de custas por cliente; ver PDR-0005. |

## Inteligência artificial

| Termo | Definição | Observação ou distinção |
| --- | --- | --- |
| Assistente do sistema | Funcionalidade de apoio ao uso do próprio produto: documentação, navegação e dúvidas operacionais sobre como utilizar o sistema. | Distinto de IA jurídica, que trata de conteúdo jurídico, não de uso do produto. |
| IA jurídica | Funcionalidade de inteligência artificial aplicada a conteúdo jurídico: análise de documentos e processos, pesquisa contextual, resumo, discussão de estratégia, e geração e edição de peças. | Depende de pré-requisitos consolidados antes de ser implementada; ver PDR-0008. |
| Assistente/Laboratório | Painel planejado para apresentar a IA jurídica dentro do contexto visual do processo, preservando a separação técnica interna entre esse componente e os demais módulos. | É a interface prevista para a IA jurídica, não um terceiro produto de IA; ver PDR-0008. |

Assistente do sistema, IA jurídica e Assistente/Laboratório são
conceitos distintos: o primeiro é apoio operacional ao uso do
produto; o segundo é a funcionalidade de inteligência artificial
jurídica em si; o terceiro é a interface planejada para apresentar a
IA jurídica dentro do processo.

## Regra de evolução

- Novos termos devem ser adicionados a este glossário quando uma
  especificação canônica de módulo introduzir um novo conceito
  funcional.
- Sinônimos devem apontar para o termo canônico correspondente, em vez
  de criar uma definição paralela.
- Termos históricos ou depreciados (ver
  `docs/governance/terminology-policy.md`) não devem ser
  reintroduzidos como novos conceitos neste glossário.
- Uma mudança incompatível com um PDR aceito exige uma nova decisão
  formal (novo PDR ou substituição explícita), não uma edição
  silenciosa deste glossário.
