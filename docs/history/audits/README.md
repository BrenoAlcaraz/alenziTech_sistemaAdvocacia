---
title: Auditorias históricas
status: canonical
owner: product-and-engineering
last_reviewed: 2026-08-06
---

# Auditorias históricas

## Finalidade

As auditorias deste diretório registram observações verificadas em um
momento específico do projeto. Elas não se atualizam automaticamente
quando o código muda e devem ser lidas como fotografias, não como estado
vigente.

## Catálogo

| Arquivo | Escopo | Base de verificação | Limitação |
|---|---|---|---|
| `2026-08-05-chatgpt-context-audit.txt` | Histórico de conversas e decisões relatadas. | Conteúdo das conversas fornecidas ao ChatGPT. | Não inspecionou diretamente o repositório; afirmações técnicas podem ser implementações relatadas, não verificadas no código. |
| `2026-08-05-claude-repository-documentation-audit.txt` | Git, arquitetura, módulos, permissões, escopo de dados, testes, infraestrutura e documentação. | Leitura do repositório no commit `031a878` e working tree daquele momento. | É um snapshot; não representa automaticamente commits posteriores e pode conter transcrições operacionais extensas. |

## Regra de uso

- auditoria não substitui current-state;
- uma auditoria deve sempre indicar commit ou data de referência;
- achados precisam ser reconfirmados antes de orientar mudança crítica;
- agentes não devem carregar auditorias longas quando documentos
  canônicos suficientes já existirem.
