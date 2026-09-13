# Dashboard — painel "Intimações"

## Objetivo

Implementar o painel "Intimações" da Visão geral do Dashboard, com
criação/vínculo **manual** nesta primeira versão. Leitura automática de
e-mail e identificação por IA/LLM ficam registradas como pendência
futura (ver Fora de escopo).

## Decisões já tomadas (não reabrir sem novo pedido)

- Mecanismo técnico de acesso a e-mail (OAuth vs IMAP) fica **adiado**
  — decisão e ticket de implementação separados, quando essa
  integração for priorizada.
- Identificação do conteúdo do e-mail (a quem processo pertence, prazo,
  motivo) é **sempre manual** nesta versão. Quando o sistema tiver um
  pipeline de IA/LLM em produção, a ideia é usá-lo para interpretar o
  e-mail e sugerir processo/prazo/motivo automaticamente, com revisão
  humana antes de confirmar — registrado abaixo como pendência futura,
  não implementar agora.
- Como consequência de adiar o mecanismo de e-mail, esta versão inclui
  uma forma de criar uma Intimação **manualmente, sem depender de
  e-mail nenhum** — assim a feature já tem uso antes da integração
  real existir.
- Decisão de escopo tomada ao escrever esta spec (sinalizar se
  discordar): como não há mecanismo de e-mail, **a tela de "cadastro de
  e-mail de intimações" em Configurações não é construída agora** — não
  faz sentido oferecer um botão "conectar e-mail" que não liga a nada.
  O link do protótipo "Gerenciar e-mail de intimações" fica sem
  destino até essa base existir.

## Comportamento esperado

- Novo modelo `Intimacao`: `processo` (FK `Processo`, obrigatório),
  `motivo` (texto curto), `prazo_manifestacao` (data, obrigatório),
  `status` (`pendente`/`manifestada`), `origem` (`manual`/`email` —
  todo registro nesta versão nasce `manual`; `email` fica reservado
  para quando a ingestão automática existir), `criado_por` (FK User),
  `criado_em`.
- **Criação manual**: tela para escolher um processo (dentro do escopo
  de mutação do usuário — mesma regra de "quais processos ele pode
  editar" já usada em Processos), motivo e prazo de manifestação.
- **Marcar como manifestada**: ação simples que muda `status` — some
  do painel do Dashboard a partir daí.
- **Painel "Intimações"** na Visão geral do Dashboard, visível quando
  `acesso_processos`: lista `Intimacao` com `status="pendente"`, dentro
  do mesmo escopo `somente_seus`/`todos` de Processos (baseado no
  processo vinculado), ordenada por `prazo_manifestacao`. Link para o
  processo.

## Regras de negócio relevantes

- Intimação sempre vinculada a um Processo existente e dentro do
  escopo de mutação de quem cria — não é possível vincular a um
  processo fora desse escopo (mesma regra dos outros formulários de
  Processo).
- O painel do Dashboard só mostra intimações pendentes; manifestadas
  saem da visão operacional mas continuam no banco (histórico).

## Fora de escopo

- Qualquer mecanismo de leitura de e-mail (OAuth/IMAP) — decisão
  técnica e ticket de implementação separados.
- Identificação automática do conteúdo por regex ou IA/LLM —
  **pendência futura explícita**: quando o sistema tiver um pipeline de
  IA (ver PDR-0008/Laboratório em `docs/STATUS.md`), revisitar esta
  feature para extrair processo/prazo/motivo automaticamente do e-mail,
  sempre com revisão humana antes de confirmar (nunca criar a
  Intimação direto sem confirmação).
- Tela de "cadastro de e-mail de intimações" em Configurações — não
  construída nesta versão (ver decisão acima).
- Notificação externa (e-mail/push) sobre intimação criada.

## Critérios de aceite

- Usuário com acesso a Processos consegue criar uma Intimação
  manualmente vinculada a um processo do seu escopo de mutação.
- Painel "Intimações" no Dashboard mostra só intimações pendentes,
  respeitando o escopo somente_seus/todos.
- Marcar uma intimação como manifestada a remove do painel
  imediatamente.
- Sem acesso a Processos, o painel não aparece (mesma regra dos outros
  painéis da Visão geral).
