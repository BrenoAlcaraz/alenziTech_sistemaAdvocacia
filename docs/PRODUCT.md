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
| Papel de acesso | Único mecanismo de autorização além do Administrador (PDR-0030); configurável pelo Administrador. Distinto de cargo profissional (só descritivo, sem efeito em permissão). |
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
- Um processo pode ter vários clientes representados (`Processo.clientes`,
  N:N); um processo compartilhado não duplica entre pastas.
- Vínculo cliente-processo deve ser íntegro: servidor rejeita
  associação inconsistente mesmo com requisição manipulada; seletores
  dependentes de processo não oferecem processos incompatíveis com o
  cliente selecionado.
- Brasileiro por padrão; marcar Estrangeiro libera documento em
  digitação livre (sem validação de CPF/CNPJ), nacionalidade por lista
  suspensa e endereço inteiro manual. Brasileiro exige CPF/CNPJ com
  dígito verificador válido quando preenchido, trava nacionalidade em
  "Brasileira", libera RG, e busca endereço automaticamente por CEP
  (demais campos de endereço só vêm dessa busca, não digitáveis à mão).
- Formulário distinto por tipo: Pessoa Jurídica oculta os campos que só
  fazem sentido para o próprio cliente Pessoa Física (estado civil,
  profissão, RG, nacionalidade/Estrangeiro) e, no lugar, oferece uma
  seção "Representante" — nome, CPF (mesmo dígito verificador do
  CPF/CNPJ), cargo/qualificação (texto livre) e contato
  (telefone e/ou e-mail). Dados do representante pertencem ao próprio
  Cliente PJ (não criam um segundo Cliente nem usuário do sistema) e
  servem de base a peças geradas para o cliente (ex.: "Gerar
  procuração"). Um representante principal por cliente PJ nesta versão
  — sem vínculo com um Cliente PF já cadastrado.
- Segundo visor no detalhe do cliente (painel fora do bloco principal
  de identificação): para PF mostra estado civil, nacionalidade,
  profissão e idade; para PJ mostra os dados do representante. Idade é
  sempre calculada a partir de `data_nascimento` (campo novo, só PF,
  nunca digitada diretamente) — `Cliente.idade`/`Cliente.selo_prioridade`
  (`None` sem data preenchida ou para PJ).
- Selo de prioridade "Idoso" (Estatuto do Idoso, idade ≥ 60) ou "Menor
  de idade" (< 18) ao lado do nome do cliente na listagem/detalhe e em
  Tarefas/Processos vinculados a ele (componente
  `templates/components/selo_prioridade.html`) — só indicativo/visual,
  não altera ordenação de fila, prazo ou notificação.
- Exclusão definitiva (PDR-0025), distinta de desativar — lançamentos
  financeiros, tarefas e compromissos vinculados permanecem, só perdem
  a referência. Exceção: as procurações geradas para o cliente
  (`ModeloPeca.cliente`) são excluídas junto com ele, para nunca virarem
  modelo-base com os dados dele.
- "Clientes relacionados": dois clientes aparecem vinculados um ao
  outro quando estão do mesmo polo (ambos ativo, ou ambos passivo) de
  algum processo em comum — depende de os dois terem sido cadastrados
  manualmente como Parte desse processo (sem vínculo automático
  Cliente↔Parte ainda, ver [modules/processos.md](modules/processos.md)).
- Aba "Documentos" do detalhe: anexo de arquivo (RG/CNH, comprovante de
  residência, contrato social, procuração etc.) por Cliente, mesmo
  padrão de storage protegido por tenant e de escopo de Documentos de
  Processo — leitura segue o escopo de detalhe do cliente, mutação
  (adicionar/excluir) exige ser responsável pelo cliente ou
  Administrador, mais as habilitações `clientes_documento_adicionar`/
  `clientes_documento_excluir`.
- Fora de escopo: dedup por CPF/CNPJ, cardinalidade de múltiplos
  endereços/contatos por cliente — sem decisão aprovada.

- Formulário (revisão de 2026-09-19): PF pede só CPF e Nome; PJ pede só
  CNPJ e Razão social/Firma, com Nome fantasia e opção "Empresa
  estrangeira" (documento livre, sem validar CNPJ). PJ mostra primeiro
  os dados e o endereço da empresa e, separado abaixo, os dados do
  representante. RG sem máscara (não há padrão nacional). Nome, cidade e
  bairro do cliente são sempre gravados em maiúsculas.
- "Clientes relacionados" também considera clientes vinculados ao mesmo
  processo (`Processo.clientes`), restritos ao escopo de leitura de quem
  consulta.
- Cada cliente relacionado mostra os processos em comum (número +
  status, como links; até 3, depois "+N"), pelas duas origens da
  relação. A coluna só existe para quem tem o módulo Processos e lista só
  processos dentro do escopo de leitura de Processos do usuário; o
  cliente relacionado continua listado mesmo sem nenhum processo visível.

### Tarefas

Delegação de trabalho — direta na maioria dos casos hierárquicos claros,
por convite (aceitar/recusar) nos demais (PDR-0002/PDR-0033).

- Delegar (atribuir a outro usuário) gera convite pendente, exceto
  quando quem delega é Administrador do escritório (para qualquer
  usuário) ou gerente de Equipe delegando para subordinado não-gerente
  da própria Equipe — nesses dois casos a tarefa aparece imediatamente
  para o destinatário, sem convite (PDR-0002). Nos demais casos,
  inclusive gerente para gerente da mesma Equipe, a tarefa só passa a
  ser atribuição ativa do destinatário depois que ele aceita o convite;
  recusar (com justificativa opcional) também é uma resposta válida —
  ver "Delegação por convite" abaixo. Auto-atribuição nunca gera
  convite. Reatribuição de tarefa **já existente** continua livre, sem
  convite (comportamento inalterado de PDR-0002).
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
- Faixa de sub-abas abaixo da lista principal: "Recentes (últimas 24h)",
  "Atribuídas a mim por terceiros" e "Convites recebidos" (PDR-0033)
  sempre visíveis para qualquer usuário; "Delegadas por mim" e "Ver
  tarefas de outra pessoa" só para quem já tem a habilitação de
  atribuir tarefa a terceiros — mesma habilitação nas duas, nenhuma
  habilitação nova. "Delegadas por mim" mostra o estado do convite
  (pendente/aceito ou direto/recusado com justificativa) de cada item.
- Múltiplos participantes: "Atribuir a" aceita vários usuários de uma
  vez (botão "Atribuir a todos" marca todos de uma vez). Na criação,
  "Atribuir a" é obrigatório (mínimo um; o usuário logado já vem
  pré-selecionado) e o "Responsável" é obrigatoriamente um dos
  atribuídos — não há opção "Eu mesmo"; a lista de responsável mostra
  só os marcados em "Atribuir a" e, com um único atribuído, ele já vem
  selecionado. Quem não tem a habilitação de atribuir a terceiros vê
  só o próprio nome nas duas listas. A regra vale no backend; a
  reatribuição de tarefa já criada continua livre (qualquer usuário
  ativo). Continua existindo um único
  responsável formal (`Tarefa.responsavel`) — os demais entram como
  `Tarefa.participantes`, sem responsabilidade formal: não concluem a
  tarefa (só o responsável/Administrador) e não recebem a notificação
  de conclusão. Participante consegue ver a tarefa (mesmo escopo de
  leitura do responsável), mas não aparece como quem a concluiu. Uma
  Equipe pode ser usada como atalho para selecionar vários atribuídos/
  participantes de uma vez — ver "Equipe como atalho de seleção" abaixo.
- Fora de escopo: gamificação, avaliação de desempenho.

### Delegação por convite (Tarefas e Agenda)

Mesma regra conceitual reaproveitada nos dois módulos (PDR-0033):
delegar (Tarefa: atribuir; Agenda: definir responsável de outra
pessoa) gera convite pendente, exceto Administrador→qualquer usuário e
gerente de Equipe→subordinado não-gerente da própria Equipe, que
continuam diretos. Entre dois gerentes da mesma Equipe o convite
continua obrigatório.

- Só o próprio destinatário aceita ou recusa o próprio convite, sem
  checagem de habilitação adicional. Recusar aceita justificativa
  opcional em texto livre.
- Enquanto pendente ou recusado, o item não aparece como atribuição
  ativa do destinatário (fora das listas/quadro/agenda operacionais
  dele) — só como convite aguardando resposta na sub-aba "Convites
  recebidos".
- Não confundir com a confirmação de presença de **participante** de
  Compromisso (PDR-0020) — decide presença, não quem é o responsável;
  não muda com esta regra.
- Reatribuição de item **já existente** para outro responsável
  continua livre, sem convite, nos dois módulos.
- Fora de escopo: notificação de convite, expiração/lembrete/
  cancelamento de convite pendente.

### Equipe como atalho de seleção

Em Processos ("Integrantes habilitados", PDR-0014), Agenda
(participantes do compromisso) e Tarefas (atribuídos/participantes),
escolher uma Equipe só seleciona seus membros ativos como pessoas
individuais — nenhum vínculo com a equipe é gravado (PDR-0028).
Equipe inativa não é oferecida; sem equipe ativa cadastrada a tela
mostra "Nenhuma equipe cadastrada ainda".

- Criação (Tarefa: "Atribuir a"; Agenda: participantes): uma linha de
  botões de equipe acima da lista marca as caixinhas dos membros
  ativos (pode clicar em várias equipes; depois desmarca-se quem não
  deve entrar). Em Tarefas, a lista de "Responsável" acompanha os
  marcados; a equipe nunca é responsável.
- Edição (Processos: card "Integrantes"; Tarefas e Agenda: card de
  participantes): "Adicionar pessoa" e "Adicionar equipe" são
  rotulados. Escolher a equipe abre a lista dos membros ativos,
  todos marcados; quem já está no alvo aparece marcado e desabilitado.
  Confirmar em "Adicionar selecionados" inclui só os marcados; dá para
  repetir com outra equipe. Remoção é sempre individual.
- Depois de adicionados, membros que entram, saem ou são desativados na
  equipe não alteram integrantes/participantes já definidos: quem sai
  da equipe não perde acesso automaticamente — a remoção é manual.
- O servidor valida cada usuário (elegível no módulo e membro ativo da
  equipe informada); não confia no JS.
- Em Processos não afeta o responsável principal; em Agenda cada
  participante passa pela confirmação de presença normal (PDR-0020).
  Nenhuma habilitação nova — cada módulo exige a mesma que já exige
  para gerenciar integrante/participante. O grupo de chat automático
  por equipe (PDR-0026) não muda.

### Agenda

Compromissos manuais e originados de processo, lista + calendário
mensal (mesmos dados, duas visões) convivendo na mesma página, com
alternância dinâmica sem recarregar.

- Prazo processual relevante deve poder aparecer na agenda, preservando
  a referência de origem mesmo após edição.
- Notificação (PDR-0016): todo compromisso/prazo notifica automaticamente
  dentro do sistema 15 minutos antes, por verificação periódica em
  segundo plano, sem ação do usuário. Canais externos (e-mail/push/SMS)
  e antecedência configurável ficam fora de escopo.
- Sincronização bidirecional automática prazo↔evento não está
  claramente aprovada em nenhum PDR — não presumir esse comportamento.
- Faixa de sub-abas abaixo da lista/calendário: "Novos na sua agenda
  (últimas 24h)", "Adicionado por terceiro" e "Convites recebidos"
  (PDR-0033) sempre visíveis para qualquer usuário; "Delegados por mim"
  e "Agenda de outros usuários" só para quem já tem, respectivamente, a
  habilitação de criar compromisso para outros e a Permissão
  "Agenda"/"Todos" + Gerir — nenhuma habilitação nova. Definir outro
  usuário como responsável do compromisso segue a regra de "Delegação
  por convite" (ver seção em Tarefas) — direto só para Administrador ou
  gerente→subordinado da própria Equipe, convite nos demais casos;
  "Delegados por mim" mostra o estado do convite de cada item. Não
  confundir com a confirmação de presença de participante logo abaixo.
- Verificar disponibilidade de um convidado ao adicioná-lo como
  participante (mostra os compromissos que ele já tem no horário)
  é só informativo — nunca impede a criação do compromisso — e exige a
  mesma permissão da aba "Agenda de outros usuários".
- Fora de escopo: Google Calendar, múltiplos fusos, recorrência de
  evento.

- Criar/editar compromisso: botão "Adicionar todos os usuários" como
  participantes (cada um com confirmação de presença normal).

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
reais e autorizados — nunca mock ou número fixo. Três abas — Visão
geral do escritório (inclui o painel "Intimações", criação/vínculo
manual nesta versão), Análise de dados e Painel do gestor — ver
[docs/modules/dashboard.md](modules/dashboard.md) para os painéis e
regras de agrupamento.

- Cada indicador respeita autorização e escopo do usuário que consulta;
  ocultar um card na interface não substitui a filtragem no backend.
- Indicadores financeiros seguem previsto/realizado (PDR-0004).
- Processo sem movimentação usa a data do último andamento como
  referência.
- Fora de escopo: ranking/avaliação automática de desempenho,
  predição por IA, analytics avançado antes da consolidação do núcleo.

- Painel: "Processos por status" = ativo, arquivado, suspenso,
  sobrestado. Suspenso/sobrestado/retomada vêm de decisão do juiz,
  lançada no formulário de andamento. Painel do gestor não tem atalho
  separado para Habilitações (fazem parte de Permissões). Localidade
  (cidade/comarca/vara) de processo é gravada em maiúsculas.

### Chat

Comunicação interna dentro do mesmo tenant.

- Nenhuma conversa atravessa tenant.
- Conversas individuais e em grupo são conceitos distintos.
- Acesso a mensagens/anexos verificado no backend — conhecer o
  identificador não concede acesso.
- Criar uma Equipe cria automaticamente um grupo de chat correspondente,
  com a lista de participantes sincronizada com os membros efetivos da
  equipe — entrar/sair da equipe reflete no grupo automaticamente, mas
  não no sentido contrário (sair do grupo manualmente não remove da
  equipe); efeito de desativar uma equipe sobre o grupo é gap em aberto
  (PDR-0026).
- Notificação: ao enviar mensagem em conversa individual ou em grupo,
  cada participante exceto o autor é notificado dentro do sistema
  (mesmo mecanismo de PDR-0016); sala global não notifica —
  compartilhada por todo o tenant, sem nível de escopo.
- Leitura: indicador de não lida é sempre por participante, nunca
  compartilhado entre eles — inclusive na sala global.
- Mensagem nova chega em tempo real (WebSocket) para quem está com a
  conversa aberta, e o indicador de não lida atualiza em tempo real na
  lista de conversas; sem conexão em tempo real disponível, envio e
  leitura continuam funcionando normalmente por HTTP.
- Fora de escopo: chamada de áudio/vídeo, integração com apps externos,
  IA dentro do chat.

- Grupos avulsos podem ter nome e integrantes editados por quem
  participa (grupo de equipe segue gerido pela Equipe). `@usuario`
  numa mensagem notifica quem foi chamado (na sala global, qualquer
  usuário do módulo); IA por `@` é direção futura.

### Modelos

Repositório de modelos de peças/documentos reutilizáveis.

- Acervo é sempre institucional: usuário autorizado ao módulo alcança
  todos os modelos do tenant, não só os próprios (sem nível
  `somente_seus`/`todos` — decisão de 2026-08-31, tratado como
  Chat/Gerir).
- Upload manual não depende de IA; integração com IA é futura (PDR-0008)
  e nunca salva definitivo sem confirmação humana.
- Reutilizar um modelo não altera o original.
- Categoria do modelo é um catálogo fechado por tenant
  (`CategoriaModeloPeca`), não texto livre — exibida na interface como
  "Tipo de peça" (o catálogo em si, nome do model e do campo, não muda);
  gerenciar o catálogo (criar/editar/excluir) exige
  `modelos_gerir_categorias` ou ser Administrador; excluir categoria em
  uso (por modelo atual ou por histórico de versões) é bloqueado.
- Todo tenant (novo ou já existente) já nasce com 15 tipos de peça
  pré-cadastrados nesse catálogo (Petição inicial, Contestação,
  Réplica, Alegações finais, Apelação, Embargos de declaração, Agravo
  de instrumento, Agravo interno, Recurso especial, Recurso
  extraordinário, Quesitos técnicos, Petição de mero andamento,
  Exceção de pré-executividade, Embargos infringentes, Procuração) —
  cada um editável/excluível como qualquer categoria criada
  manualmente; nenhum vem com `ModeloPeca` de conteúdo pronto (fica a
  critério de cada escritório), exceto Procuração, que serve de base ao
  "Gerar procuração" de Clientes.
- Cada modelo da listagem oferece visualizar (abre a peça para leitura)
  e baixar em PDF ou DOCX — gerado a partir do `conteudo` salvo, aplicando
  cabeçalho/rodapé/marca d'água/assinatura e fonte/espaçamento/recuo do
  `EstiloEscritorio` vigente no momento do download (não um snapshot de
  quando a peça foi criada). Reconhecimento de endereçamento/número de
  processo/jurisprudência/citação não entra na exportação — depende do
  pipeline de IA do PDR-0008, ainda não existe.
- Toda edição de um modelo preserva a versão anterior no histórico
  (autor da edição, data, conteúdo completo); reverter para uma versão
  anterior é uma nova edição — gera nova entrada no histórico, nunca
  apaga a atual. Excluir o modelo remove também seu histórico.
- Estilo do escritório é configuração única do tenant, sem autoria —
  leitura sempre liberada a quem tem o módulo, edição restrita a quem
  tem `modelos_editar_estilo` ou é Administrador. Sem tom de voz/
  instruções gerais (removidos — eram só reserva para uma IA de geração
  de peças que não existe, PDR-0008). Editor visual do padrão de
  documento: cabeçalho, rodapé e marca d'água (texto ou imagem, cada um
  ligável/desligável — em modo imagem, tamanho em % da folha e posição
  esquerda/centro/direita configuráveis), fonte/cor da folha, e a
  formatação própria de endereçamento, número do processo, número da
  guia, nome das partes, jurisprudência, transcrição de artigo e
  citação — cada peça nova segue esse padrão automaticamente.
  Endereçamento/número do processo/guia só aparecem na primeira página
  do documento gerado. Alternativa a construir do zero: anexar uma peça
  já formatada como referência visual apenas (sem extração automática
  de estilo do arquivo).
- Assinatura do padrão de Meu Estilo é uma lista (`AssinaturaEstilo`),
  não mais um único bloco — o escritório cadastra quantas quiser (ex.:
  dois sócios assinando a mesma peça), cada uma texto ou imagem, com
  tamanho/posição próprios; a peça exportada traz todas, em sequência.
- Cabeçalho e rodapé (só eles, não a marca d'água) escolhem em quais
  páginas aparecem: todas, só a primeira ou só a última. Padrão vem de
  Meu Estilo; cada `ModeloPeca` pode ter sua própria escolha
  (`cabecalho_replicacao`/`rodape_replicacao`), semeada do padrão do
  escritório no momento da criação e independente dele daí em diante —
  mudar o padrão depois não afeta modelo já criado. "Só a última
  página" não é suportável no .docx exportado (o formato não conhece
  paginação no momento da geração — Word só calcula isso ao abrir o
  arquivo); nesse caso o cabeçalho/rodapé simplesmente não aparece no
  .docx, só no PDF (que consegue calcular a página final).
- Criar um modelo manualmente (não importado) mostra cabeçalho, rodapé,
  marca d'água e assinaturas do estilo vigente do escritório como
  moldura de contexto ao redigir o conteúdo — não editável ali, sempre
  a leitura do estilo atual no momento da criação. O reconhecimento
  automático de jurisprudência/citação pela IA durante a redação
  depende do pipeline de IA de peças (PDR-0008) — ainda não existe.
- Imagem inserida no conteúdo da peça (editor de "novo modelo") tem
  tamanho (% da folha) e posição (esquerda/centro/direita) ajustáveis
  após inserida — vira uma data-URL embutida no HTML salvo (sem upload
  para storage); a exportação em PDF/DOCX reconhece essa imagem como um
  parágrafo próprio (nunca mistura com o texto ao redor) e a desenha no
  tamanho/posição configurados.
- Peças repetitivas (aba "Peças repetitivas", exige `modelos_criar`) —
  Fase 1, sem IA: usuário escolhe uma peça base (do acervo, ou anexando
  um arquivo PDF/DOCX novo só para esta geração — não vira modelo
  próprio antes de gerar) e define um ou mais casos. Cada caso pode
  referenciar um Cliente já cadastrado — nome e CPF/CNPJ entram
  automaticamente — e tem campos manuais para valor, endereço do caso e
  particularidades (não vêm do cadastro do Cliente). Ao gerar, cada caso
  vira um novo `ModeloPeca` no acervo: o conteúdo da peça base com um
  bloco de identificação do caso à frente — não há identificação
  automática dos campos variáveis da peça base nem extração automática
  de dados de documento anexado por caso (isso é a Fase 2, com IA,
  condicionada ao PDR-0008).
- "Gerar procuração" (botão na aba Documentos do Cliente, mesma
  autorização de Peças repetitivas — `modelos_criar` — combinada com
  poder ver o cliente no escopo de Clientes) usa o mesmo padrão: o
  modelo de Procuração cadastrado pelo escritório (categoria
  pré-definida "Procuração") + um bloco de identificação do cliente à
  frente (nome/CPF-CNPJ/endereço, e nome/CPF/cargo do representante se
  PJ), virando um novo `ModeloPeca` no acervo sem alterar o modelo
  original. Sem nenhum modelo cadastrado nessa categoria, o botão
  orienta a criar um em vez de gerar um texto genérico não revisável:
  "+ Criar modelo de Procuração" abre o formulário de modelo com o
  cliente de origem (`modelos:novo?cliente=<id>`, resolvido no mesmo
  escopo/autorização de "Gerar procuração"; cliente inválido ou fora do
  escopo é ignorado e o formulário abre normal). Nesse caminho "Tipo de
  peça" vem como Procuração e travado (também no backend) e o rodapé
  tem "Salvar modelo" (vai ao detalhe do modelo) e "Salvar e criar
  procuração para <cliente>" (salva o modelo e gera a procuração do
  cliente na mesma transação, voltando à aba Documentos com "Procuração
  criada"). Sem a categoria Procuração cadastrada, o formulário é o
  normal.
  A peça gerada fica vinculada ao cliente (`ModeloPeca.cliente`) e
  nunca é oferecida como modelo-base: só peças sem cliente entram na
  lista de modelos-base — a procuração de um cliente não serve de base
  para a de outro. Procurações geradas antes desse vínculo continuam
  sem cliente (o cliente não é adivinhado pelo título) e seguem na lista
  de modelos-base até alguém apagá-las. A aba Documentos do cliente
  ganha a seção "Procurações geradas" (título, data, autor e link para a
  peça, sem exibir o conteúdo), visível só a quem tem acesso ao módulo
  Modelos, além do escopo de leitura do cliente; o contador
  "Documentos (n)" conta só arquivos anexados.
- Fora de escopo: dedup automática, geração em massa assistida por IA
  (Fase 2 do fluxo de peças repetitivas), edição colaborativa em tempo
  real, categorias hierárquicas, diff visual entre versões de peça.

- Peças repetitivas: cada caso leva o cliente (nome/CPF-CNPJ), os
  documentos que embasam a peça (PDF/DOCX/imagem, ficam guardados nela)
  e observações; não há mais campos de valor nem endereço. A IA que
  ajusta a peça base a esses dados depende do PDR-0008.
- Meu estilo: imagens de cabeçalho, rodapé, marca d'água e assinatura se
  ajustam arrastando na folha (mover entre esquerda/centro/direita e
  alça de tamanho); a assinatura salva ao soltar.

### Configurações

Perfil pessoal, gestão administrativa de usuários/papéis/habilitações/
equipes, identidade do escritório, consulta ao plano SaaS.

- Alteração de senha usa o fluxo seguro do Django.
- Perfil pessoal permite trocar a própria foto (avatar), com storage
  protegido por tenant — sem URL pública direta.
- Tela de habilitações/permissões individuais de um usuário mostra
  sempre o estado efetivo (ligado/desligado) de cada módulo/
  habilitação — já refletindo o que veio herdado do(s) papel(éis);
  não expõe herdado/override como conceito separado na
  interface. Qualquer alteração grava um override individual
  explícito, sem exigir uma ação separada de "desligar herança"; o
  mecanismo de override continua existindo tecnicamente por baixo.
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

- Identidade visual (admin): logo do escritório na barra lateral; as
  cores predominantes do logo viram as cores do sistema (ajustáveis; a
  cor principal é escurecida se for clara demais para leitura).
- Excluir usuário (admin) = inativar a conta, remover das equipes e
  passar os processos dele ao Administrador (PDR-0010); não vale para
  si nem para o Administrador. Exige a senha de quem está logado
  (senha ausente/errada não exclui; mensagem genérica) — só para
  usuário, não para cliente/processo/modelo (PDR-0030).
- Papel de acesso é o único mecanismo de autorização (não existe "Tipo
  de conta"). De fábrica só há o Administrador (tudo) e o papel
  "Limitado" (tudo desligado; editável, mas não pode ser excluído nem
  desativado). O Administrador cria/edita papéis, módulo/nível e
  habilitações. Novo usuário exige papel, com "Limitado" pré-selecionado.
  Desativar papel com usuários ativos é recusado ("reatribua os N
  usuários antes"). Usuário sem papel e sem override não acessa nada
  (PDR-0030).
- Foto de perfil visível aos colegas (lista de usuários, chat).
- Documentos e anexos em qualquer módulo têm botões de visualizar
  (olho) e baixar; só PDF, imagem e texto abrem no navegador.
- Botão "Voltar" global no cabeçalho, para a tela de onde o usuário veio.

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
