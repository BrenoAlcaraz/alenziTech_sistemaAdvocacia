# Módulo — Processos

Processos judiciais e casos extrajudiciais: dados, participantes,
documentos, andamentos, vínculos, prazos, apensos. Arquivo próprio por
volume real de decisão (PDR-0001, 0010, 0012, 0013, 0014) — ver
[PRODUCT.md](../PRODUCT.md) para o padrão dos módulos mais simples.

## Autorização e responsabilidade (PDR-0010, PDR-0014)

- Módulo `processos` é autorização binária nesta versão: módulo
  habilitado dá acesso a todas as operações existentes, sem
  habilitação granular por operação (decisão deliberada, não lacuna).
- Escopo por `Processo.responsavel` (`somente_seus`/`todos`) e
  responsabilidade obrigatória são a direção vigente. Equipe não
  concede acesso nem filtra Processos.
- Cada processo tem um único responsável principal obrigatório —
  referência para prazos na Agenda e indicadores. Pode ter N
  integrantes habilitados além dele, que não recebem prazos
  automaticamente.
- Atribuir/reatribuir responsável exige a habilitação
  `processos_atribuir_responsavel` ou a autoridade do Administrador do
  escritório. Gerenciar integrantes habilitados exige
  `gerir_habilitar_usuario_processos`.

## Partes (PDR-0013 — modelo vigente)

- Cada parte tem um único campo de papel processual (10 opções: Autor,
  Embargante, Recorrente, Réu, Embargado, Recorrido, Terceiro
  Interessado, Ministério Público, Amicus Curiae, Juiz), agrupadas
  visualmente em Polo Ativo / Polo Passivo / Outros.
- Parte que corresponde ao Cliente do processo reaproveita o cadastro
  (sem redigitação); campos de advogado pré-preenchidos quando a parte
  bate com o Cliente por CPF/CNPJ.
- Advogado é texto livre (nome + OAB) associado à parte, no máximo um
  por parte — nunca uma parte em si do processo.
- PDR-0013 substitui PDR-0001/PDR-0011 (modelo de três dimensões:
  vínculo/posição estrutural/qualificação processual, representantes
  normalizados, histórico de classificação). O modelo antigo não deve
  ser reintroduzido.

## Apensos (PDR-0012)

- Relação simétrica entre dois Processos existentes, sem hierarquia.
- Ambos mantêm identidade própria; nada é copiado, fundido, herdado ou
  propagado (cliente, responsável, equipe, status, fase, participantes,
  andamentos, prazos, documentos).
- Remover a relação não exclui nenhum processo. A↔B e B↔C não inferem
  A↔C. "Menor"/"maior" na persistência é só normalização técnica do
  par — não significa principal/pai/filho.

## Arquivamento e andamentos

- Arquivar muda `status` para `arquivado`; processo some das listas
  operacionais mas continua disponível em análise de dados. Reaproveita
  a mesma autorização de edição — sem habilitação separada para
  arquivar.
- Andamentos em ordem cronológica, com anexo opcional e autor
  identificável. Data do último andamento é a referência de inatividade.
- Fase processual, status processual e andamento processual são
  conceitos distintos (não usar como sinônimos).

## Fora de escopo imediato

- Assistente/Laboratório (condicionado a PDR-0008);
- OCR de documentos, integração com API de tribunal;
- determinação automática de status por IA.

## Pontos em aberto

- Lista canônica definitiva de valores de status processual.
- Autoridades além de juiz (relator, desembargador, perito).
- Mecanismo exato de criação rápida de cliente durante o fluxo de
  processo.
- Materialização automática do Cliente como Parte ao vincular o
  Processo (PDR-0013, ponto em aberto) — implementação atual usa só o
  fluxo manual de adicionar parte, com nome/CPF-CNPJ reaproveitáveis
  por atalho no formulário, sem criação automática.

## Referências

- [PDR-0001](../decisions/PDR-0001-participantes-processuais.md) (parcialmente substituído)
- [PDR-0010](../decisions/PDR-0010-autorizacao-escopo-responsabilidade-processos.md)
- [PDR-0012](../decisions/PDR-0012-relacao-simetrica-processos-apensos.md)
- [PDR-0013](../decisions/PDR-0013-partes-processo-modelo-simplificado.md)
- [PDR-0014](../decisions/PDR-0014-responsavel-integrantes-processos.md)
- [STATUS.md](../STATUS.md#processos) para o estado real de implementação
