---
id: PDR-0037
title: Prazo sugerido a partir do texto da intimação
status: accepted
owner: product-and-engineering
decision_date: 2026-09-26
last_reviewed: 2026-09-26
supersedes: []
complements:
  - PDR-0008
  - PDR-0014
  - PDR-0034
source_files: []
---

# PDR-0037 — Prazo sugerido a partir do texto da intimação

## Contexto

O acompanhamento automático de processos (DataJud + DJEN) traz as
intimações publicadas no DJEN com o inteiro teor. O prazo vem escrito
em dias no texto ("no prazo de 15 (quinze) dias"), nunca como data
final. Lançar esse prazo à mão é justamente o trabalho que a feature
quer eliminar.

Havia duas premissas já registradas que pareciam impedir isso:

- o cálculo de prazo por **catálogo legal**
  (`specs/agenda-prazos-processuais-automaticos.md`) estava parado
  aguardando validação jurídica;
- o PDR-0008 condiciona a IA jurídica (leitura e interpretação de
  documentos) à consolidação do núcleo funcional.

O sócio advogado validou o fluxo em que tudo o que chega automaticamente
entra como sugestão para o usuário confirmar, rejeitar ou editar.

## Decisão

- O sistema pode calcular a data de um prazo a partir do **número de
  dias escrito no texto da intimação** do DJEN. É uma premissa distinta
  do catálogo legal e não depende dele.
- A extração é **regra (padrão textual)**, não IA jurídica: o sistema
  procura a expressão de prazo em dias, sem interpretar a decisão. Não
  se enquadra no PDR-0008.
- Na dúvida o sistema não chuta: texto sem prazo, com mais de um prazo
  ou com prazo em formato diferente de "N dias" fica **"prazo a
  definir"**, sem data.
- Andamento e prazo gerados automaticamente nascem **"Sugerido"**:
  - o prazo entra na hora na Agenda, sem etapa de aprovação que o
    bloqueie;
  - confirmar tira o selo; rejeitar apaga o andamento e, com ele, o
    prazo e o item da Agenda; editar corrige a data ou anexa o documento
    real.
- Todo prazo calculado exibe o aviso de que foi calculado
  automaticamente, sem feriado local nem suspensão do tribunal, e deve
  ser conferido.
- O prazo tem dono: **nosso cliente** ou **outra parte**. Só o de nosso
  cliente gera item na Agenda do responsável do processo (PDR-0014,
  PDR-0034); o de outra parte fica registrado no processo para
  acompanhamento.
- O motor de dias úteis é único e compartilhado com o futuro cálculo por
  catálogo legal.

## Consequências

- O catálogo legal deixa de ser pré-requisito para haver prazo
  automático; as duas origens convivem.
- A regra "todo andamento com `data_prazo` gera um Prazo na Agenda"
  passa a valer só para prazo de nosso cliente.
- Parâmetros do cálculo ainda sem validação jurídica final (termo
  inicial DJEN × portal, lista de feriados) são configuráveis e ficam
  como padrão provisório na spec da feature até a confirmação do sócio;
  a liberação para escritórios clientes depende dessa confirmação.
- Os termos de uso precisam dizer que o cálculo é ferramenta de apoio e
  não substitui a conferência do advogado.

## Fora do escopo desta decisão

- Leitura de PDF, interpretação de decisão e cadastro de processo a
  partir da íntegra por IA (continuam sob o PDR-0008).
- Feriados locais e suspensões do tribunal no cálculo.
- Regras de contagem da área Penal.
- Os parâmetros detalhados de contagem (vivem na spec e, depois, em
  `docs/modules/processos.md`).
