> ⚠️ **Rascunho de pesquisa — NÃO é aconselhamento jurídico.** Este documento é insumo para uma spec de produto ainda não escrita e precisa de revisão item por item por advogado com OAB ativa antes de qualquer prazo aqui listado virar regra ativa no sistema.

# Prazos processuais no Brasil — pesquisa de embasamento

Pesquisa factual para embasar o catálogo de tipos de ato/prazo e as regras de
contagem de uma futura feature de geração automática de compromissos de
"prazo" na Agenda a partir de andamentos processuais. Não descreve a feature
em si — é só o levantamento de fontes primárias (lei e portais oficiais).

Leis consultadas diretamente no texto oficial do Planalto:
- CPC — Lei nº 13.105/2015: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm
- CLT — Decreto-Lei nº 5.452/1943: https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm
- Lei nº 5.584/1970 (prazo recursal trabalhista): https://www.planalto.gov.br/ccivil_03/leis/l5584.htm
- Lei nº 11.419/2006 (processo eletrônico): https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11419.htm

Todos os artigos abaixo foram conferidos por acesso direto ao HTML publicado
em planalto.gov.br nesta sessão de pesquisa (08/09/2026), não apenas por
memória do modelo.

---

## Seção 1 — Catálogo de prazos processuais mais comuns com contagem fixa em lei

Todos os prazos abaixo, salvo indicação contrária, são contados em **dias
úteis**, por força do art. 219, CPC (ver Seção 2). No processo do trabalho a
CLT não tem regra equivalente ao art. 219 do CPC — a contagem trabalhista é,
historicamente, em dias corridos (consultar nota específica ao final da
tabela trabalhista).

### 1.1 Cível — CPC (Lei 13.105/2015)

| Ato/decisão que gera o prazo | Prazo | Dias úteis/corridos | Artigo (texto conferido em planalto.gov.br) |
|---|---|---|---|
| Contestação | 15 dias | Úteis (art. 219) | Art. 335, caput, CPC — "O réu poderá oferecer contestação, por petição, no prazo de 15 (quinze) dias, cujo termo inicial será a data: [...]" |
| Réplica à contestação (fato impeditivo/modificativo/extintivo alegado pelo réu) | 15 dias | Úteis | Art. 350, CPC — "Se o réu alegar fato impeditivo, modificativo ou extintivo do direito do autor, este será ouvido no prazo de 15 (quinze) dias [...]" |
| Manifestação sobre documento novo juntado pela parte contrária (inclui réplica sobre documentos anexados à contestação, art. 437 caput) | 15 dias | Úteis | Art. 437, §1º, CPC — "Sempre que uma das partes requerer a juntada de documento aos autos, o juiz ouvirá, a seu respeito, a outra parte, que disporá do prazo de 15 (quinze) dias [...]" |
| Apelação (interposição) | 15 dias | Úteis | Art. 1.003, §5º, CPC — regra geral de recursos: "Excetuados os embargos de declaração, o prazo para interpor os recursos e para responder-lhes é de 15 (quinze) dias." (Art. 1.010 trata do procedimento da apelação, mas não fixa prazo próprio — o prazo vem da regra geral do art. 1.003, §5º) |
| Contrarrazões de apelação | 15 dias | Úteis | Art. 1.010, §1º, CPC — "O apelado será intimado para apresentar contrarrazões no prazo de 15 (quinze) dias." |
| Agravo de instrumento (interposição) | 15 dias | Úteis | Art. 1.003, §5º, CPC (regra geral de recursos — o CPC não fixa prazo específico dentro do art. 1.015/1.017, que tratam de cabimento e formação do instrumento) |
| Agravo interno (contra decisão do relator) | 15 dias | Úteis | Art. 1.003, §5º, CPC (regra geral). O art. 1.021, CPC apenas prevê o cabimento: "Contra decisão proferida pelo relator caberá agravo interno [...]", sem fixar prazo próprio — prazo vem do art. 1.003, §5º |
| Embargos de declaração (qualquer decisão) | 5 dias | Úteis | Art. 1.023, caput, CPC — "Os embargos serão opostos, no prazo de 5 (cinco) dias, em petição dirigida ao juiz [...]" |
| Recurso especial / recurso extraordinário (interposição) | 15 dias | Úteis | Art. 1.003, §5º, CPC (regra geral de recursos). O art. 1.029, CPC trata do cabimento e requisitos, sem fixar prazo próprio diferente do geral |
| Contrarrazões de recurso especial/extraordinário | 15 dias | Úteis | Art. 1.030, caput, CPC (redação dada pela Lei 13.256/2016) — "Recebida a petição do recurso pela secretaria do tribunal, o recorrido será intimado para apresentar contrarrazões no prazo de 15 (quinze) dias [...]" |
| Agravo em recurso especial/extraordinário (contra decisão de inadmissão) | 15 dias | Úteis | Art. 1.042, CPC (regra geral do art. 1.003, §5º; o art. 1.042 não repete o número do prazo no caput, mas a doutrina e a prática forense aplicam os 15 dias gerais de recurso) |
| Cumprimento de sentença — pagamento voluntário | 15 dias | Úteis | Art. 523, caput, CPC — "[...] o cumprimento definitivo da sentença far-se-á a requerimento do exequente, sendo o executado intimado para pagar o débito, no prazo de 15 (quinze) dias, acrescido de custas, se houver." |
| Impugnação ao cumprimento de sentença | 15 dias | Úteis | Art. 525, caput, CPC — "Transcorrido o prazo previsto no art. 523 sem o pagamento voluntário, inicia-se o prazo de 15 (quinze) dias para que o executado [...] apresente [...] sua impugnação." (termo inicial é o fim do prazo do art. 523, não uma nova intimação) |
| Embargos à execução (título extrajudicial) | 15 dias | Úteis | Art. 915, caput, CPC — "Os embargos serão oferecidos no prazo de 15 (quinze) dias, contado, conforme o caso, na forma do art. 231." |
| Embargos de terceiro | Sem prazo fixo — "a qualquer tempo" enquanto não houver trânsito em julgado (fase de conhecimento); no cumprimento de sentença/execução, até 5 dias após adjudicação/alienação/arrematação | Corridos (é prazo de direito material de exercício de pretensão, não prazo processual em dias) | Art. 675, caput, CPC — "Os embargos podem ser opostos a qualquer tempo no processo de conhecimento enquanto não transitada em julgado a sentença e, no cumprimento de sentença ou no processo de execução, até 5 (cinco) dias depois da adjudicação, da alienação por iniciativa particular ou da arrematação, mas sempre antes da assinatura da respectiva carta." — **atenção**: este não é um prazo "de X dias contados de um andamento" no mesmo padrão dos demais; o catálogo de UI precisa tratá-lo como caso especial (janela aberta, com termo final variável) |

**Nota sobre agravo de instrumento e agravo interno**: o CPC não repete o
número "15 dias" dentro dos artigos que tratam do cabimento desses recursos
(arts. 1.015–1.020 e 1.021); o prazo vem da regra geral do art. 1.003, §5º,
que se aplica a "os recursos" em geral, ressalvados os embargos de
declaração. Isso deve ser conferido por advogado antes de virar regra ativa,
porque é uma inferência de sistemática (regra geral + ausência de regra
especial), não uma remissão literal expressa no artigo do recurso específico.

### 1.2 Trabalhista — CLT (Decreto-Lei 5.452/1943) e Lei 5.584/1970

| Ato/decisão que gera o prazo | Prazo | Dias úteis/corridos | Artigo (texto conferido em planalto.gov.br) |
|---|---|---|---|
| Contestação/defesa | Não é prazo em dias — defesa é **oral, em audiência**, com 20 minutos para aduzi-la (pode ser escrita via PJe até a audiência) | N/A | Art. 847, caput e parágrafo único, CLT — "Não havendo acordo, o reclamado terá vinte minutos para aduzir sua defesa [...]. Parágrafo único. A parte poderá apresentar defesa escrita pelo sistema de processo judicial eletrônico até a audiência." — **este item não se encaixa no padrão "N dias após andamento X"** do restante do catálogo; teria de ser modelado como compromisso vinculado à data da audiência, não como prazo contado em dias |
| Recurso ordinário | 8 dias | — (ver nota de dias úteis/corridos abaixo) | Art. 895, I e II, CLT — "das decisões definitivas ou terminativas das Varas e Juízos, no prazo de 8 (oito) dias" / "das decisões definitivas ou terminativas dos Tribunais Regionais, em processos de sua competência originária, no prazo de 8 (oito) dias [...]" |
| Contrarrazões (qualquer recurso trabalhista) | 8 dias | — | Art. 6º, Lei 5.584/1970 — "Será de 8 (oito) dias o prazo para interpor e contra-arrazoar qualquer recurso (CLT, art. 893)." |
| Embargos de declaração (sentença ou acórdão) | 5 dias | — | Art. 897-A, caput, CLT — "Caberão embargos de declaração da sentença ou acórdão, no prazo de cinco dias [...]" |
| Agravo de petição | 8 dias | — | Art. 897, caput, CLT — "Cabe agravo, no prazo de 8 (oito) dias: [...]" (a alínea "a" do mesmo artigo trata do agravo de petição, decisões do juiz nas execuções) |
| Agravo de instrumento (trabalhista) | 8 dias | — | Art. 897, caput e alínea "b", CLT — mesmo prazo geral de 8 dias, aplicável ao agravo "de instrumento, dos despachos que denegarem a interposição de recursos" |
| Recurso de revista | 8 dias | — | **Não há um número explícito no caput vigente do art. 896, CLT** (que trata das hipóteses de cabimento). O prazo de 8 dias decorre da aplicação do art. 6º da Lei 5.584/1970 (prazo geral para "qualquer recurso") combinado com a prática uniforme dos Tribunais do Trabalho/TST — **conferir com advogado trabalhista antes de fixar como regra**, pois é inferência por analogia/prática consolidada, não remissão literal de um artigo específico |
| Agravo contra decisão denegatória de recurso de revista | 8 dias | — | Art. 896, §12, CLT (incluído/renumerado por reformas posteriores) — "Da decisão denegatória caberá agravo, no prazo de 8 (oito) dias." |

**Nota sobre dias úteis vs. corridos na Justiça do Trabalho**: a CLT não tem
um dispositivo equivalente ao art. 219 do CPC. O art. 775, CLT (não
verificado nesta pesquisa em detalhe — recomenda-se checagem específica antes
de uso) e a jurisprudência do TST historicamente tratam os prazos
trabalhistas como contados em **dias corridos**, computando sábados,
domingos e feriados dentro do intervalo, mas excluindo o dia do começo e
incluindo o dia do vencimento — e prorrogando para o primeiro dia útil
seguinte quando o vencimento cai em dia sem expediente forense. **Este ponto
específico (dias corridos vs. úteis no processo do trabalho) não foi
confirmado nesta pesquisa por leitura direta de um artigo da CLT que o
declare de forma equivalente ao art. 219 do CPC — é uma lacuna que precisa
ser fechada por advogado trabalhista antes de virar regra ativa no sistema**,
porque impacta diretamente o cálculo de todo prazo trabalhista do catálogo
acima.

---

## Seção 2 — Termo inicial da contagem de prazo na prática processual brasileira

### 2.1 Regra geral de contagem (CPC)

- **Art. 219, CPC** — "Na contagem de prazo em dias, estabelecido por lei ou
  pelo juiz, computar-se-ão somente os dias úteis." (parágrafo único do
  mesmo artigo restringe essa regra aos prazos **processuais**; prazos de
  **direito material** — ex.: prescrição, decadência — continuam contados em
  dias corridos, sem essa proteção). Fonte:
  https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm
- **Art. 224, caput, CPC** — "Salvo disposição em contrário, os prazos serão
  contados excluindo o dia do começo e incluindo o dia do vencimento."
  §1º — "Os dias do começo e do vencimento do prazo serão protraídos para o
  primeiro dia útil seguinte, se coincidirem com dia em que o expediente
  forense for encerrado antes ou iniciado depois da hora normal ou houver
  indisponibilidade da comunicação eletrônica."
- **Art. 231, CPC** — define o "dia do começo do prazo" conforme a forma de
  citação/intimação. Os incisos relevantes (texto conferido):
  - I — data de juntada aos autos do AR, quando a citação/intimação for pelo
    correio;
  - II — data de juntada do mandado cumprido, quando por oficial de justiça;
  - III — data de ocorrência do ato, quando por escrivão/chefe de secretaria;
  - IV — dia útil seguinte ao fim da dilação assinada pelo juiz, quando por
    edital;
  - **V — "o dia útil seguinte à consulta ao teor da citação ou da intimação
    ou ao término do prazo para que a consulta se dê, quando a citação ou a
    intimação for eletrônica"** — este é o inciso central para intimação
    eletrônica (PJe/DJEN);
  - VII — data de publicação, quando a intimação se der pelo Diário da
    Justiça impresso ou eletrônico;
  - VIII — dia da carga dos autos, quando retirados em carga do cartório.

### 2.2 Intimação eletrônica — Lei 11.419/2006

Texto conferido diretamente em
https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11419.htm:

- **Art. 5º, caput** — "As intimações serão feitas por meio eletrônico em
  portal próprio [...], dispensando-se a publicação no órgão oficial,
  inclusive eletrônico."
- **Art. 5º, §1º** — "Considerar-se-á realizada a intimação no dia em que o
  intimando efetivar a consulta eletrônica ao teor da intimação [...]."
- **Art. 5º, §2º** — se a consulta ocorrer em dia não útil, a intimação é
  considerada realizada no primeiro dia útil seguinte.
- **Art. 5º, §3º — regra da "intimação ficta"**: "A consulta referida nos §§
  1º e 2º deste artigo deverá ser feita **em até 10 (dez) dias corridos**
  contados da data do envio da intimação, sob pena de considerar-se a
  intimação **automaticamente realizada na data do término desse prazo**."
- Para o Diário da Justiça eletrônico (publicação, não intimação pessoal),
  o art. 4º, §3º e §4º fixam: "Considera-se como data da publicação o
  primeiro dia útil seguinte ao da disponibilização da informação no Diário
  da Justiça eletrônico" e "Os prazos processuais terão início no primeiro
  dia útil que seguir ao considerado como data da publicação."

**Diferença prática entre publicação (DJe) e intimação eletrônica (portal
pessoal)**: no regime de publicação em Diário de Justiça (art. 4º), o
"dia da publicação" já é definido como o 1º dia útil seguinte à
disponibilização, e o prazo começa no 1º dia útil seguinte a essa data de
publicação (ou seja, dois "saltos" de dia útil). No regime de intimação
pessoal eletrônica (art. 5º + art. 231, V, CPC), o termo inicial é a data em
que o advogado efetivamente abriu/consultou a intimação no sistema (ou, na
ausência de consulta, o 10º dia corrido contado do envio) — e a partir
dessa data de "intimação realizada", o prazo em si começa a contar no dia
útil seguinte, por força do art. 224, CPC combinado com o art. 231, V.

### 2.3 Entendimento do STJ (jurisprudência mais recente, fonte stj.jus.br)

- **STJ, 5ª Turma, AREsp 2.492.606, rel. Min. Messod Azulay Neto, notícia de
  10/10/2025**: confirmou que o prazo de dez dias corridos do art. 5º, §3º,
  da Lei 11.419/2006 para consulta eletrônica é contado a partir da data de
  **envio** da intimação, "independentemente de feriados ou dias não
  úteis" — e que, encerrado esse período de 10 dias corridos, o prazo
  recursal subsequente começa a contar do dia seguinte ao término dos 10
  dias (contagem ficta), não do próximo dia útil a partir desse marco. Fonte
  primária: https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2025/10102025-Prazo-de-dez-dias-corridos-para-consulta-eletronica-de-intimacao-e-contado-da-data-do-seu-envio-.aspx
- **STJ, 3ª Turma, REsp 1.993.773, rel. Min. Marco Aurélio Bellizze, notícia
  de 19/10/2022**: quando a intimação/citação ocorre por correio, a
  contagem do prazo para praticar o ato subsequente começa no **primeiro
  dia útil seguinte à juntada do Aviso de Recebimento (AR)** aos autos,
  aplicando-se em conjunto os arts. 224 e 231, CPC. Fonte primária:
  https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2022/19102022-Havendo-intimacao-ou-citacao-por-correio--contagem-do-prazo-comeca-no-primeiro-dia-util-seguinte-a-juntada-do-AR.aspx
- **Divergência entre Turmas do STJ** (achado em pesquisa secundária,
  reportando decisões do STJ — não confirmado por leitura do acórdão
  original nesta sessão): há relatos de que a 1ª Turma do STJ, em decisão
  administrativa referida como de 07/12/2017, entendeu que a contagem do
  prazo do destinatário intimado eletronicamente começa no **2º dia útil**
  após a data da intimação (aplicando art. 224 c/c art. 231, V, CPC), ao
  passo que a 2ª e a 3ª Turmas teriam considerado a data efetiva de
  intimação (o próprio 10º dia, ou o dia da consulta) como termo para
  aplicação direta do art. 224 (excluindo apenas esse dia, incluindo o dia
  do vencimento) — chegando a resultados próximos, mas não idênticos, a
  depender de qual dia exato é tratado como "dia da intimação" para fins de
  exclusão do art. 224. **Esse ponto específico não foi confirmado por fonte
  primária .jus.br nesta pesquisa** (a fonte foi um artigo doutrinário
  publicado em jus.com.br, que é blog jurídico, não fonte primária) — fica
  registrado como sinal de que o tema já gerou divergência jurisprudencial e
  **precisa de confirmação por advogado antes de qualquer regra de contagem
  automática ser fixada no sistema para esse cenário específico**
  (interstício entre o fim da intimação ficta de 10 dias e o início efetivo
  do prazo do ato).

### 2.4 Como advogados determinam na prática "a partir de que dia começa a contar"

Combinando os textos legais e jurisprudenciais acima, o fluxo prático típico
para um processo eletrônico (PJe ou sistema equivalente) é:

1. Determinação/decisão é assinada e disponibilizada no sistema (data de
   "disponibilização");
2. Se veiculada por publicação no DJe: considera-se "data da publicação" o
   1º dia útil seguinte à disponibilização (art. 4º, §3º, Lei 11.419/2006);
   o prazo do ato começa no 1º dia útil seguinte a essa data de publicação
   (art. 4º, §4º);
3. Se veiculada por intimação eletrônica pessoal (portal/PJe, mais comum
   para advogados cadastrados): conta-se o prazo de até 10 dias corridos do
   envio para o advogado abrir a intimação (art. 5º, §3º, Lei 11.419/2006);
   se ele abrir antes, a intimação é "realizada" nesse dia (ou no próximo
   dia útil, se a consulta ocorrer em dia não útil — art. 5º, §2º); se não
   abrir, é automaticamente considerada realizada no 10º dia corrido;
4. A partir da data em que a intimação foi "realizada" (seja por consulta
   efetiva, seja pela ficção do 10º dia), o **prazo do ato em si** (os 15
   dias de contestação, por exemplo) começa a correr no dia útil seguinte,
   já contando apenas dias úteis (art. 219 c/c art. 224 c/c art. 231, V,
   CPC).

Isso significa que, para automatizar a geração do compromisso de prazo, o
sistema precisa capturar pelo menos dois marcos distintos e não
confundíveis: (a) a data de disponibilização/publicação do andamento no
sistema do tribunal, e (b) a data em que a intimação é considerada
"realizada" segundo as regras acima — que não é necessariamente a mesma
data em que o andamento foi lançado no sistema jurídico do escritório.

---

## Seção 3 — Viabilidade de cobrir feriados forenses locais de forma automatizável

### 3.1 O recesso forense nacional (art. 220 CPC) é uniforme e não varia por estado

- **Art. 220, caput, CPC** — "Suspende-se o curso do prazo processual nos
  dias compreendidos entre 20 de dezembro e 20 de janeiro, inclusive."
  Fonte: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm
- **Resolução CNJ nº 244, de 12/09/2016** (vigente) confirma e uniformiza
  essa regra para **todos os órgãos do Poder Judiciário, inclusive da
  União**: "Art. 3º Será suspensa a contagem dos prazos processuais em todos
  os órgãos do Poder Judiciário, inclusive da União, entre 20 de dezembro a
  20 de janeiro, período no qual não serão realizadas audiências e sessões
  de julgamento, como previsto no art. 220 do Código de Processo Civil,
  independentemente da fixação ou não do recesso judiciário previsto no
  artigo 1º desta Resolução." Fonte primária:
  https://atos.cnj.jus.br/atos/detalhar/2349 (texto integral obtido nesta
  pesquisa).
  - A mesma resolução distingue esse período de suspensão de prazos (fixo,
    nacional, 20/12–20/01) de um segundo instituto diferente — o **recesso
    administrativo** facultativo de expediente forense (20/12 a 6/1), que os
    Tribunais de Justiça estaduais **podem** instituir por conta própria
    (art. 1º da Resolução), mas que não altera o período de suspensão de
    prazos, já fixo por lei federal.
  - **Conclusão relevante para a feature**: o recesso de fim de ano (20/12 a
    20/1) **é automatizável de forma simples e uniforme nacionalmente** —
    não depende de portaria estadual/municipal, é regra federal única (CPC +
    Resolução CNJ 244/2016).

### 3.2 Feriados forenses "locais" (fora do recesso de fim de ano) variam por estado/comarca e não têm fonte consolidada única

- Não foi encontrada, nesta pesquisa, nenhuma **API pública ou tabela
  nacional consolidada do CNJ** que liste feriados forenses por
  estado/comarca. A API Pública do DataJud/CNJ
  (https://www.cnj.jus.br/sistemas/datajud/api-publica/ e
  https://datajud-wiki.cnj.jus.br/api-publica/) expõe metadados de
  processos judiciais (mais de 80 milhões de processos), não um endpoint de
  calendário/feriados forenses.
- Cada Tribunal de Justiça estadual (e cada TRT) publica, tipicamente uma
  vez por ano, uma **portaria própria** com o calendário de feriados
  forenses e pontos facultativos — inclusive feriados **municipais**
  (aniversário de cidade/comarca) que variam por comarca dentro do mesmo
  estado. Exemplos concretos encontrados nesta pesquisa:
  - **TJSP** mantém uma página institucional dedicada
    (https://www.tjsp.jus.br/CanaisComunicacao/Feriados/ExpedienteForense),
    mas o conteúdo é apresentado em tabela HTML sem link de download
    estruturado (PDF/planilha) nem API — não há, nesta página, segmentação
    por comarca visível no HTML público consultado.
  - **TJSC** publica portaria anual em formato PDF hospedado no próprio
    domínio institucional — ex.: Portaria 2026/005, calendário de feriados
    forenses de 2026, confirmada acessível em
    https://www.tjsc.jus.br/documents/d/tjsc/portaria_2026005-pdf-1 (HTTP
    200 nesta pesquisa).
  - **TJMG** publica portarias conjuntas anuais/periódicas com o calendário
    de suspensão de expediente, incluindo casos de feriado municipal por
    comarca — ex.: Portaria Conjunta nº 1.658/PR/2025
    (https://www8.tjmg.jus.br/institucional/at/pdf/pc16582025.pdf) e
    Portaria Conjunta nº 1.764/PR/2026
    (https://www8.tjmg.jus.br/institucional/at/pdf/pc17642026.pdf), e o
    portal institucional (tjmg.jus.br) confirma que "nas comarcas do
    interior [de MG], a suspensão do expediente forense ocorre em razão de
    feriados municipais instituídos por ato legislativo municipal e
    fixados em portaria pelo diretor do foro" — ou seja, o próprio TJ
    reconhece que a fonte primária do feriado é a lei municipal, replicada
    depois em portaria do foro local.
  - **TJMT** divulgou notícia institucional confirmando suspensão de
    expediente e prazos em comarca específica (São José do Rio Claro) por
    aniversário de município, em 2026
    (https://www.tjmt.jus.br/noticias/2026/3/aniversario-municipio-suspende-expediente-e-prazos-na-comarca-sao-jose-rio-claro)
    — outro exemplo concreto de feriado municipal/comarca isolado, fora de
    qualquer calendário nacional.
  - **TJRJ** publica documento consolidado de suspensão de prazos por
    instância (1ª e 2ª instância) em portal de conhecimento próprio — ex.:
    https://portaltj.tjrj.jus.br/documents/d/portal-conhecimento/suspensao-prazos-1a-e-2a-instancia_2024_seesc
- **Conclusão**: feriados forenses locais (fora do recesso nacional de
  20/12–20/1) **não têm fonte pública única, estruturada e
  legível-por-máquina**. Cada TJ/TRT publica sua portaria anual em PDF, e
  dentro de cada estado ainda há variação por comarca (aniversário de
  município, feriados municipais instituídos por lei local). Automatizar
  isso de forma completa e sempre atualizada exigiria manutenção manual
  contínua (ingestão/curadoria anual de dezenas de portarias estaduais, mais
  atualização pontual por comarca) — **não é uma automação "configure uma
  vez e esqueça"**, é uma fonte de dados que precisa de processo de
  manutenção recorrente, ou aceitar cobertura parcial (ex.: só o recesso
  nacional automatizado + feriados nacionais/estaduais fixos do calendário
  civil, deixando feriados municipais/de comarca como responsabilidade do
  usuário revisar manualmente).

### 3.3 Como legaltechs brasileiras tratam isso hoje (informação pública)

- **Aurum (Astrea)** mantém uma calculadora de prazos processuais pública e
  gratuita (https://www.aurum.com.br/calculadora-de-prazos-processuais/),
  que permite escolher contagem em dias úteis ou corridos e referencia um
  "calendário de feriados e recessos" à parte. A página pública consultada
  **não detalha** se/como a ferramenta trata feriados municipais ou de
  comarca específica — essa informação não está disponível publicamente na
  página consultada nesta pesquisa.
- **Projuris** também mantém uma calculadora pública
  (https://www.projuris.com.br/calculadora-de-prazos-processuais/) que
  declara aplicar automaticamente a suspensão do recesso forense
  (20/12–20/1) e contagem em dias úteis excluindo "finais de semana e
  feriados". A página consultada **não especifica a fonte dos feriados**
  usados (se é só o calendário nacional/estadual civil, ou se inclui
  feriados forenses municipais/de comarca) — essa informação também não
  ficou clara na página pública.
- Não foi encontrada, nesta pesquisa, documentação técnica pública
  detalhada (blog técnico, página de documentação de API, whitepaper) de
  nenhuma das legaltechs pesquisadas — Astrea/Aurum, Projuris, Legal One
  (Thomson Reuters), CPJ-3C, SAJ (Softplan), Advbox, Espaider, Easyjur —
  explicando **como cada uma mantém atualizada, especificamente, a base de
  feriados forenses municipais/de comarca**. **Isso é declarado
  explicitamente aqui como lacuna de pesquisa**: não há evidência pública
  suficiente para afirmar se essas empresas fazem curadoria manual
  contínua, compram uma base de terceiros, ou apenas cobrem o calendário
  nacional/estadual e deixam feriados municipais como responsabilidade do
  usuário. Uma spec futura que dependa desse dado precisaria de contato
  direto com essas empresas ou de engenharia reversa das ferramentas (fora
  do escopo desta pesquisa).

### 3.4 Implicação prática para uma futura spec

Com base no levantado:
- O recesso forense de fim de ano (20/12–20/1) pode ser tratado como regra
  federal fixa, sem necessidade de dado externo por tribunal.
- Feriados nacionais e estaduais "civis" (não forenses) seguem calendário
  público e estável, mas **não são a mesma coisa** que feriados forenses —
  um feriado forense pode existir sem ser feriado civil (ex.: aniversário de
  comarca) e vice-versa nem sempre corresponde (nem todo feriado municipal
  vira suspensão de expediente forense automaticamente — depende de portaria
  do foro local).
- Feriados forenses municipais/de comarca não têm fonte única
  legível-por-máquina; qualquer cobertura completa exigiria um processo de
  manutenção manual recorrente (ingestão anual de portarias por
  estado/comarca) que está fora do escopo desta pesquisa avaliar em custo/
  esforço, mas que precisa ser um item explícito de risco/escopo na spec
  futura.
