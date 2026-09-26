# Spec — Acompanhamento automático de processos via DataJud + DJEN

Status: **definida com padrões provisórios, pronta para implementar.**
Cálculo de prazo pelo texto da intimação decidido no PDR-0037. Liberação para escritórios clientes só depois da validação em uso real
(ver "Critérios de liberação").

## Objetivo

Um job diário acompanha, nas fontes públicas do CNJ, os processos já
cadastrados no escritório e traz para dentro deles, como **sugestão**, o
que o tribunal publicou ou movimentou — andamentos e prazos — para o
usuário confirmar, rejeitar ou editar.

A API **não cria processo**: só acompanha o que o escritório cadastrou.
Não há módulo nem tela nova. O resultado aparece na aba de andamentos e
na aba Prazos do processo, na Agenda do responsável e nos avisos do
painel.

## Fontes (contrato conferido com chamadas reais em 24/09/2026)

- **DataJud (API Pública CNJ)**
  - Requisição: `POST https://api-publica.datajud.cnj.jus.br/api_publica_<tribunal>/_search`.
  - Autenticação: header `Authorization: APIKey <chave>`. A chave é
    pública, publicada na wiki do CNJ, e pode ser trocada pelo CNJ a
    qualquer momento. Por isso fica em configuração (env var), nunca fixa
    no código.
  - O que traz: todos os movimentos do processo (código TPU, nome, data),
    órgão julgador e grau.
  - O que não traz: texto e prazo. Processos em segredo de justiça não
    aparecem, e há atraso de dias. Chegam movimentos repetidos (mesmo
    código e mesma data).
  - O tribunal é deduzido do número CNJ, pelos segmentos `J.TR`
    (8.26 → `tjsp`).
- **DJEN (Comunica PJe)**
  - Requisição: `GET https://comunicaapi.pje.jus.br/api/v1/comunicacao`,
    sem autenticação, com `numeroProcesso` (com ou sem máscara) e
    período `dataDisponibilizacaoInicio`/`dataDisponibilizacaoFim`.
    Conferido em 26/09/2026: devolve só as comunicações daquele número,
    respeita o período e devolve lista vazia para número inexistente.
  - O que traz: publicações e intimações, com inteiro teor (HTML),
    data de disponibilização, `tipoComunicacao` (ex.: Intimação, Edital,
    Lista de distribuição), destinatários com polo (`A`/`P`), advogados
    destinatários com OAB+UF, `hash` e `id` da comunicação, link e
    indicação de cancelamento (`ativo`).
  - O prazo vem em dias dentro do texto ("no prazo de 15 (quinze) dias"),
    nunca como data final.

## Comportamento esperado

### Quais processos são acompanhados
- Todo processo com número CNJ válido, cadastrado à mão ou por qualquer
  outro caminho, exceto:
  - arquivado (volta a ser acompanhado se desarquivado);
  - marcado como **segredo de justiça**.
- Suspenso e sobrestado continuam acompanhados.
- Processo não cadastrado não é acompanhado; publicações dele não chegam.

### Segredo de justiça
- Campo manual "Segredo de justiça" no processo.
- Marcado: aviso fixo no processo — "Acompanhamento automático
  indisponível (segredo de justiça). Acompanhe manualmente." — e o
  processo sai do job.

### Primeira consulta de um processo
- Não importa o histórico: só registra o ponto de partida (movimentos e
  publicações já existentes não viram andamento).
- **[Provisório]** Publicação do DJEN dos últimos 15 dias antes do
  cadastro gera só um aviso ao responsável ("houve publicação antes do
  cadastro, confira"), com o link. Sem andamento e sem prazo.
- Processo não encontrado no DataJud: nota no processo com os possíveis
  motivos (recém-distribuído, segredo de justiça, número errado) e
  informando que a busca continua nos dias seguintes.

### Andamento sugerido
- Todo andamento automático nasce com o selo **"Sugerido"** e mostra a
  fonte (DataJud ou DJEN).
- Ações sobre o sugerido:
  - **confirmar**: tira o selo;
  - **rejeitar**: apaga o andamento e, com ele, o prazo e o item da
    Agenda gerados (regra atual de apagar andamento);
  - **editar**: ajusta dados e permite anexar o documento real.
- **[Provisório]** Quem confirma, rejeita e edita: as mesmas regras atuais
  de mutação de andamento (Administrador ou responsável do processo).

### DJEN → andamento "Intimação" + prazo
- Cada publicação vira andamento "Intimação" sugerido, com o texto, o
  link e os destinatários.
- Publicações com mesmo texto e mesma data de disponibilização (uma por
  destinatário) viram **um único** andamento, listando todos os
  destinatários.
- Prazo:
  - texto com **exatamente um** prazo em "N dias" → andamento nasce com a
    data do prazo calculada;
  - sem prazo, mais de um prazo, ou prazo em outro formato (horas, meses,
    "prazo legal", "prazo de lei", "imediatamente") → andamento marcado
    **"prazo a definir"**;
  - processo da área **Penal** → sempre "prazo a definir".
- **De quem é o prazo** (atributo do andamento: *nosso cliente* ou *outra
  parte*):
  - publicação com advogado do escritório entre os destinatários (OAB+UF
    do cadastro de usuários) → *nosso cliente*;
  - publicação só com advogados de outras partes → *outra parte*;
  - **[Provisório]** publicação sem advogado identificado entre os
    destinatários → *nosso cliente*, marcada "prazo a definir".
  - O usuário pode reclassificar.
- Só prazo de *nosso cliente* gera item Prazo na Agenda do responsável
  (entra na hora, marcado "Sugerido"). Todos os prazos aparecem na aba
  Prazos do processo.
- **Prazo em dobro**: parte do processo pode ser marcada como
  beneficiária (Fazenda Pública, Ministério Público, Defensoria, núcleo de
  prática jurídica). Se o destinatário é essa parte, o número de dias é
  dobrado e o prazo mostra "Dobrado automaticamente (15 → 30) —
  confirme".
- Todo prazo calculado mostra: "Calculado automaticamente, sem considerar
  feriado local ou suspensão do tribunal — confirme."
- Publicação cancelada no DJEN depois de importada não apaga nada; só
  avisa o responsável. Republicação gera novo andamento sugerido; o
  antigo é descartado pelo usuário.

### Cálculo da data do prazo
- **[Provisório — J1]** Conta pela publicação no DJEN:
  - publicação = 1º dia útil após a disponibilização;
  - contagem começa no dia útil seguinte à publicação.
- Dias úteis em todas as áreas, exceto Penal. Texto que diz
  expressamente "dias corridos" conta em dias corridos.
- **[Provisório — J9]** Dias não úteis: fins de semana, feriados
  nacionais (1/1, Sexta-feira Santa, 21/4, 1/5, 7/9, 12/10, 2/11, 15/11,
  20/11, 25/12) e recesso de 20/12 a 20/1. Lista em dado, não em código.
- Recesso: a data de publicação não muda; a contagem não corre de 20/12 a
  20/1 e retoma em 21/1 (ou no dia útil seguinte). Ex.: disponibilizada
  22/12 → publicada 23/12 → 1º dia da contagem 21/1.
- Feriado local e suspensões do tribunal ficam fora do cálculo (coberto
  pelo aviso).

### DataJud → andamento sem prazo
- Só movimentos com código TPU de uma **lista de códigos relevantes**:
  sentença, decisão, despacho, audiência, trânsito em julgado, juntada,
  acórdão, citação realizada, penhora, expedição de alvará, baixa e
  arquivamento.
- Ficam de fora "Conclusão", "Remessa", "Ato ordinatório" e similares, e
  os códigos que representam a própria publicação/intimação
  (disponibilização no DJe, publicação), que já chegam pelo DJEN.
- **[Provisório]** Movimento relevante vira andamento sugerido com o nome
  TPU na descrição, sem prazo, com a indicação "traga o documento".
- O código é mapeado para o tipo de andamento equivalente do catálogo; sem
  equivalente, entra como "Andamento".
- Baixa e arquivamento só geram andamento; o status do processo nunca
  muda sozinho.

### Dados do processo alterados no tribunal
- Quando o valor informado pelo DataJud para vara/órgão julgador ou grau
  muda em relação ao **último valor que o próprio DataJud informou**, o
  sistema atualiza o campo no processo e avisa o responsável para
  confirmar ou editar. Diferença de escrita entre o DataJud e o que o
  usuário digitou não conta como mudança.

### Recursos e incidentes com número próprio
- Número CNJ citado no texto de uma publicação de processo acompanhado,
  diferente do próprio e não cadastrado no escritório, aparece na aba
  Apensos como sugestão "Número X citado, não cadastrado — cadastrar e
  vincular" (atalho para novo processo com o número preenchido). Não cria
  vínculo de apenso.

### Avisos
- Andamento sugerido novo, "prazo a definir", publicação anterior ao
  cadastro, dado do processo alterado e publicação cancelada: aviso ao
  responsável no painel e no processo.
- "Prazo a definir" não resolvido: novo aviso 1× por dia ao responsável
  até ser resolvido.
- Faixa visível a todos, no painel e na aba de andamentos: "Última
  atualização: <data hora>". Se a execução do dia falhar: "Falhou hoje —
  acompanhe manualmente".

### Execução
- Uma vez por dia, antes das 7h.
- Por escritório ativo, cada um isolado no próprio schema. Uma falha em
  um processo, fonte ou escritório não interrompe os demais.
- Rodar mais de uma vez nunca duplica andamento, prazo ou aviso.

## Regras de negócio relevantes

- Extrair número de dias, destinatário e número CNJ do texto é regra
  (padrão textual), não IA jurídica (PDR-0008). Na dúvida, o sistema não
  chuta: marca "prazo a definir".
- Nada automático é definitivo sem ação humana (selo "Sugerido").
- Regras atuais mantidas nesta versão (mudança futura, fora desta spec):
  - Prazo na Agenda é sempre do `Processo.responsavel`; integrantes
    habilitados não recebem prazos (PDR-0014);
  - data para fazer = fatal − 2 dias corridos; edição do item pelo
    responsável ou Administrador;
  - aviso na véspera e no dia da fatal, só no sistema.
- Andamento automático segue as mesmas regras de visibilidade e escopo de
  processos (PDR-0010/0017).
- Alterações ficam no log de atividade.

## Padrões provisórios (a confirmar pelo sócio)

Cada item marcado **[Provisório]** acima é o padrão para desenvolver e
validar; mudar a resposta troca a regra, não a estrutura.

- J1 — data que vale quando o ato chega pelo DJEN e pelo portal.
- J2/J9 — exemplo de cálculo (01/10/2026 → 26/10/2026) e lista de
  feriados.
- Publicação anterior ao cadastro: só aviso.
- Movimento do DataJud sem texto: andamento sugerido.
- J5 — publicação sem advogado identificado: nosso cliente + prazo a
  definir.
- Quem confirma/rejeita/edita: regras atuais.

## Relação com outras specs

`specs/agenda-prazos-processuais-automaticos.md` calcula prazo por
**catálogo legal** (tabela cível validada pelo sócio em 09/2026). Esta
spec calcula a partir do **número de dias escrito na intimação**, outra
premissa, decidida no PDR-0037. O
motor de dias úteis (fins de semana, feriados nacionais, recesso) deve
ser único e compartilhado entre as duas specs.

## Fora do escopo

- Criação de processo, cliente, partes, documentos, modelos ou custas a
  partir da íntegra por IA (feature própria, condicionada ao PDR-0008).
- Área do direito e partes sugeridas automaticamente.
- Leitura de PDF; reconhecimento de citação (continua manual).
- Audiência, perícia ou julgamento criados na Agenda a partir do texto.
- Prazos em horas, meses ou "prazo legal"; cálculo na área Penal.
- Feriado local/municipal e suspensões do tribunal no cálculo.
- Detecção automática de segredo de justiça.
- Deduplicação entre o movimento do DataJud e a publicação do DJEN do
  mesmo ato (são atos distintos: o ato e sua intimação).
- Prazo interno de 1 dia antes, visibilidade da fatal para integrantes e
  edição por gerente de equipe (mudam regras atuais da Agenda; spec
  própria).
- E-mail, resumo diário e outros canais externos.
- Busca no DJEN por OAB.

## Critérios de aceite

- Processo ativo com número CNJ é acompanhado; arquivado ou marcado em
  segredo de justiça, não. Segredo de justiça mostra o aviso fixo.
- Primeira consulta não cria andamentos antigos; publicação dos últimos
  15 dias gera só aviso.
- Intimação com um único prazo em "N dias" dirigida a advogado do
  escritório gera andamento sugerido com data correta (dias úteis,
  feriado nacional e recesso) e Prazo sugerido, com aviso, na Agenda do
  responsável.
- Intimação dirigida só a outros advogados gera prazo *outra parte* na
  aba Prazos, sem item na Agenda.
- Intimação sem prazo, com vários prazos, em outro formato ou de processo
  Penal gera "prazo a definir", sem item na Agenda, e cobra o responsável
  diariamente.
- "Dias corridos" expresso conta em dias corridos; parte beneficiária tem
  o prazo dobrado com aviso.
- Rejeitar um sugerido apaga o andamento, o prazo e o item da Agenda.
- Publicações idênticas por destinatário viram um único andamento.
- Movimento do DataJud da lista gera andamento sugerido sem prazo; código
  fora da lista ou de publicação não gera nada.
- Mudança de vara/grau no DataJud atualiza o processo e avisa; diferença
  só de escrita não.
- Número CNJ não cadastrado citado em publicação aparece como sugestão em
  Apensos.
- Executar o job duas vezes seguidas não duplica nada.
- Um escritório nunca recebe dado de outro; falha isolada não interrompe
  o job; falha do dia aparece na faixa de última atualização.
- Chave do DataJud e lista de feriados configuráveis sem alterar código.

## Critérios de liberação para escritórios clientes

- 2 a 3 semanas em ambiente de teste com processos reais do escritório,
  comparando os sugeridos com o controle manual; divergências levadas ao
  sócio.
- J1, J2 e J9 confirmados pelo sócio.
- Cláusula nos termos de uso: preenchimento e cálculo são apoio e não
  substituem a conferência do advogado.
