---
title: Estado atual — Inteligência Artificial / Laboratório
status: canonical
owner: delivery
last_reviewed: 2026-08-31
---

# Estado atual — Inteligência Artificial / Laboratório

Parte de [current-state.md](../current-state.md#visão-executiva). Ver
também [inteligencia-artificial.md](../../product/modules/inteligencia-artificial.md)
(especificação canônica) e
[PDR-0008](../../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md).

## Estado

Não identificado.

## Implementado no HEAD

`apps/laboratorio/views.py::index` apenas renderiza
`templates/laboratorio/index.html`, protegido por `@login_required`,
sem passar nenhum form ou dado de `CasoLaboratorio` ao contexto. O
template exibe um formulário HTML estático (campos sem submissão
real ao model) cujo botão de envio é `<button type="button" ...
disabled>Gerar peça com IA</button>`, explicitamente desabilitado, e
não existe nenhuma view de criação para `CasoLaboratorio` em
`apps/laboratorio/urls.py` (única rota: `laboratorio/` → `index`).
`CasoLaboratorio` é um model de placeholder, com um valor de
`STATUS_CHOICES` (`"processando"`) comentado no código como
"reservado para IA futura". Nenhuma integração com provedor de IA foi
identificada.

## Estado por área de IA

- **Laboratório (interface)** — existe como shell visual
  (`apps.laboratorio`), sem lógica de IA. Não deve ser tratado como IA
  implementada.
- **IA jurídica (funcionalidade)** — não identificada no código. Os
  pré-requisitos de
  [PDR-0008](../../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
  não estão consolidados (autorização e escopo ainda não aplicados nas
  views operacionais).
- **Modelos** — cadastro e importação manuais funcionam sem depender
  de IA, conforme exigido por
  [modelos.md](../../product/modules/modelos.md); a integração futura com
  IA não está implementada.
- **Sugestão de honorários por IA** — não implementada; depende do
  model `Honorario` (ainda não existente) e dos pré-requisitos de
  [PDR-0008](../../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md),
  conforme [PDR-0007](../../product/decisions/PDR-0007-honorarios-manuais-antes-ia.md).

## Diferenças para o alvo canônico

[inteligencia-artificial.md](../../product/modules/inteligencia-artificial.md)
e
[PDR-0008](../../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
descrevem IA jurídica (contexto de processo, busca em documentos,
resumo, geração e edição de peças) e Assistente/Laboratório como
interface planejada — nenhum desses comportamentos existe além do
shell visual. As habilitações `processos_usar_ia` e
`processos_usar_laboratorio` existem no kernel sob o módulo
`processos`, sem nenhuma view que as consulte.

## Dependências ou bloqueios

[PDR-0008](../../product/decisions/PDR-0008-ia-apos-nucleo-funcional.md)
— pré-requisitos (autorização aplicada, escopo aplicado, acesso seguro
a documentos, dados processuais estruturados, histórico e
rastreabilidade, módulos centrais estáveis) ainda não consolidados.
