---
id: PDR-0038
title: Movimento do DataJud como sugestão e dados do processo pelo tribunal
status: accepted
owner: product-and-engineering
decision_date: 2026-09-26
last_reviewed: 2026-09-26
supersedes: []
complements:
  - PDR-0037
  - PDR-0014
source_files: []
---

# PDR-0038 — Movimento do DataJud como sugestão e dados do processo pelo tribunal

## Contexto

O acompanhamento automático (PDR-0037) também consulta o DataJud, que
traz os movimentos do processo (código TPU, nome, data), o órgão
julgador e o grau, mas não traz texto nem prazo. Há atraso de dias,
movimentos repetidos e processos que não aparecem (recém-distribuídos,
em segredo de justiça ou com número errado). A tabela TPU tem centenas
de códigos, e a maioria é trâmite interno sem interesse para o
advogado.

## Decisão

- Só uma **lista de códigos TPU relevantes** vira andamento: sentença,
  acórdão, decisão, despacho, audiência, trânsito em julgado, juntada,
  baixa, arquivamento e expedição de alvará. Códigos de
  publicação/disponibilização ficam de fora porque já chegam pelo DJEN.
  A lista é dado (`apps/processos/movimentos_tpu.py`), não regra
  espalhada pelo código.
- O movimento relevante vira andamento **"Sugerido"** sem prazo, com a
  indicação "traga o documento". Usa o tipo equivalente do catálogo da
  área do processo e, sem equivalente, entra como "Andamento".
  Julgamento é Sentença no 1º grau/juizado e Acórdão nos demais.
- Baixa e arquivamento **nunca** mudam o status do processo; só geram
  andamento.
- Mudança de vara/órgão julgador ou grau é detectada comparando com o
  **último valor informado pelo próprio DataJud**, nunca com o que o
  usuário digitou. Quando muda, o processo é atualizado e o responsável
  é avisado para confirmar ou editar. Diferença só de escrita (acento,
  caixa, espaços) não conta.
- A primeira vez que o DataJud encontra um processo só registra o ponto
  de partida (não importa histórico nem altera o processo). Processo não
  encontrado mostra uma nota com os motivos possíveis e continua sendo
  buscado nos dias seguintes.
- Ações feitas pelo job, sem autor humano (andamento sugerido criado,
  vara/grau atualizados), **não entram no log de atividade**: o log
  registra quem fez. O rastro fica na notificação ao responsável e no
  selo "Sugerido". Confirmar, rejeitar e editar continuam registrados.
- A chave da API vem só do ambiente (`DATAJUD_API_KEY`), porque o CNJ
  pode trocá-la a qualquer momento.

## Consequências

- Um código relevante que falte na lista não gera andamento: fica
  invisível até entrar na lista. Por isso todo movimento visto é
  registrado, e mudar a lista não reimporta movimentos antigos.
- A lista e o mapeamento são **provisórios** até a validação do sócio.
  Citação realizada e penhora ainda não têm código TPU conferido e estão
  fora; audiência e alvará entram como "Andamento" por falta de tipo
  equivalente no catálogo.
- Falha do DataJud (inclusive falta da chave) é contada na execução do
  dia e aparece como "Falhou hoje", sem impedir o DJEN.

## Fora do escopo desta decisão

- Deduplicação entre o movimento do DataJud e a publicação do DJEN do
  mesmo ato (são atos distintos).
- Detecção automática de segredo de justiça.
- Mudança automática de status, fase ou partes a partir do DataJud.
