# UI 4/6 — Simplificar padrões repetidos entre módulos

Origem: critique de 2026-09-24. Sistema visual: `DESIGN.md`.
Depende de: estilos de foco já disponíveis (ver `DESIGN.md`, Navigation → Foco por teclado) para a barra de filtros nova.

## Objetivo

Cada padrão de interface existe uma vez e funciona igual em todos os
módulos; o que é identidade do sistema dá lugar à marca do escritório.

## Comportamento esperado

- **Barra de filtros única** (partial compartilhado) para as listas
  com filtros (Processos, Clientes, Financeiro, Agenda, Análise):
  mesmos rótulos, mesmo espaçamento, mesmo comportamento de envio
  (decidir um: aplicar ao mudar ou botão "Filtrar" — não os dois) e
  "Limpar filtros" sempre presente quando há filtro ativo. Botão de
  filtrar é secundário, nunca primário.
- **Uma ação primária por tela**: demais ações viram secundárias ou
  entram num menu "Mais ações" (caso de `processos/detalhe.html`).
- Links de "Arquivados", "Inativos", "Cancelados" saem do subtítulo em
  cinza claro e viram um controle visível e consistente de visão
  (ex.: abas "Ativos | Arquivados").
- Status de processo deixa de usar o badge de área do direito; ganha
  badge de status próprio.
- **Marca do escritório**: título da aba do navegador passa a ser
  "<Página> · <nome do escritório>" em vez de "Jurídico SaaS"; logo
  padrão (sem logo cadastrado) deixa de ser a balança da justiça e
  passa a ser as iniciais do escritório na cor principal.
- Remover: chip "Da equipe (Em breve)" em Clientes; paleta `sidebar`
  não usada em `tailwind.config.js`; comentário "preto, como nas
  imagens" em `input.css`; `components/search_bar.html` morto;
  `card_summary.html` passa a ser usado pelo Painel ou é removido.
- Texto de títulos padronizado: um tamanho de H1 para página de lista e
  um para detalhe (ver `DESIGN.md`, Typography); sem `text-[10px]`/
  `text-[11px]`.

## Regras de negócio

Nenhuma regra nova. Filtros continuam no URL e com o mesmo escopo no
backend.

## Fora do escopo

- Editor de Modelos.
- Formato das listas (tabela/paginação: UI 5).
- Filtros salvos.

## Critérios de aceite

- Todas as listas com filtro usam o mesmo partial.
- Nenhuma tela com mais de um `btn-primary` visível ao mesmo tempo.
- Aba do navegador mostra o nome do escritório.
- Escritório sem logo não mostra a balança.
- Itens removidos sem referência restante (`grep`).
