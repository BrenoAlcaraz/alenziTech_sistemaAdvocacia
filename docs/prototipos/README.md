---
title: Protótipos funcionais de referência
status: draft
owner: product-and-engineering
last_reviewed: 2026-08-31
---

# Protótipos funcionais de referência

## Autoridade

Os arquivos HTML deste diretório são referências visuais e registros de
exploração do produto. Não são especificações canônicas nem instruções de
implementação. Quando um protótipo divergir de PDR, especificação de módulo,
segurança, arquitetura ou Work Item vigente, prevalece a fonte de maior
autoridade definida em [docs/README.md](../README.md#hierarquia-das-fontes-de-verdade).

Um agente não deve copiar models, campos, permissões, transições ou jobs dos
blocos “Como construir” sem reconfirmá-los nas fontes canônicas aplicáveis.

## Divergências já resolvidas

- `processo-prototipo.html` demonstra propagação de integrantes entre
  apensos; PDR-0012/PDR-0014 preservam a independência e não adotam essa
  cascata.
- `financeiro-prototipo.html` demonstra solicitações em fluxo curto
  `a_pagar`/`paga`; PDR-0015 define o fluxo vigente com análise e aprovação.
- `agenda-prototipo.html` não é a fonte da antecedência de notificação; a
  regra vigente de 15 minutos foi decidida em PDR-0016.
- os detalhes de Partes de `processo-prototipo.html` são subordinados ao
  modelo aprovado em PDR-0013.

## Arquivos

- `agenda-prototipo.html`
- `configuracoes-prototipo.html`
- `dashboard-prototipo.html`
- `financeiro-prototipo.html`
- `modelos-prototipo.html`
- `processo-prototipo.html`
- `tarefas-prototipo.html`
