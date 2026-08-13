---
title: Desenvolvimento
status: canonical
owner: development
last_reviewed: 2026-08-06
---

# Desenvolvimento

## Objetivo

Este diretório documenta **como desenvolver** o Breno - LawSystem: como
preparar o ambiente, quais comandos existem de fato no repositório, como
executar a aplicação e como executar testes.

`docs/development/` não substitui:

- [docs/product/](../product/) — **o que** construir;
- [docs/architecture/](../architecture/) — **como** o sistema é
  estruturado;
- [docs/security/](../security/) (quando existir) — controles de
  segurança;
- [docs/delivery/](../delivery/) — onde o projeto está e o que fazer
  agora.

Ver também a organização documental completa em
[docs/README.md](../README.md#organização-documental).

## Princípios

- Todo comando documentado aqui é provado pelo HEAD do repositório —
  pela leitura direta de `manage.py`, `requirements/`, `package.json`,
  `config/settings/`, ou pela execução de um comando de
  leitura/diagnóstico (`python manage.py help`, `python manage.py
  check`) que não altera estado. Nenhum comando é documentado apenas
  porque é comum em projetos Django.
- Nenhuma ferramenta é presumida — se `pytest`, `Docker`, `Celery`,
  `Ruff` ou qualquer outra ferramenta comum não for encontrada no HEAD,
  este diretório registra a ausência em vez de presumir uso futuro.
- Ambiente de desenvolvimento e ambiente de produção são tratados como
  configurações distintas (`config/settings/development.py` versus
  `config/settings/production.py`), sem misturar as duas.
- O escopo de qualquer implementação é definido pelo Work Item ativo
  (ver [docs/delivery/work/README.md](../delivery/work/README.md)), não
  por este diretório.
- [docs/delivery/current-state.md](../delivery/current-state.md) é a
  fotografia verificada do HEAD em um commit específico — este diretório
  não a duplica, apenas documenta os procedimentos operacionais para
  trabalhar sobre o código.
- Código e testes continuam sendo a prova da implementação real,
  conforme a
  [hierarquia das fontes de verdade](../README.md#hierarquia-das-fontes-de-verdade).
  Nenhum comando documentado aqui prova, por si, que uma funcionalidade
  está implementada ou correta.

## Documentos desta seção

- [commands.md](commands.md) — comandos de desenvolvimento confirmados:
  ambiente Python, dependências, variáveis de ambiente, banco de dados e
  multitenancy, Django, Tailwind, static/media e diagnóstico.
- [testing.md](testing.md) — estratégia e comandos de teste: runner
  atual, inventário de testes existentes, organização, comandos e
  limitações conhecidas da suíte.
- [workflow.md](workflow.md) — o ciclo de execução de uma unidade de
  trabalho, do preflight ao relatório final: quando um Work Item pode
  sair de `ready`, como controlar escopo durante a implementação, como
  tratar achados fora do escopo e falhas de teste.
- [quality-gates.md](quality-gates.md) — os critérios de validação
  obrigatórios e condicionais antes de considerar uma implementação
  concluída.
- [git-procedure.md](git-procedure.md) — o procedimento de Git: auditoria
  do working tree, staging, commit, push, tratamento de falha de push,
  operações de alto risco e a política de line endings do repositório
  (`.gitattributes`).

Uso de agentes de IA além do que já está implícito no caráter
executor-agnóstico destes documentos pertence a um lote futuro desta
reorganização documental e não é tratado aqui.

## Fluxo mínimo para começar

Resumo; os comandos completos estão em [commands.md](commands.md).

1. Preparar o ambiente Python (virtualenv) e instalar as dependências de
   desenvolvimento.
2. Configurar as variáveis de ambiente (`.env`, a partir de
   `.env.example`).
3. Preparar o banco de dados PostgreSQL e aplicar as migrations do
   schema público e dos schemas de tenant.
4. Compilar (ou observar em modo watch) o CSS via Tailwind, quando
   houver alteração de estilo.
5. Executar a aplicação (`python manage.py runserver`).
6. Executar os testes adequados ao trabalho em andamento — ver
   [testing.md](testing.md).

## Referências

- [docs/README.md](../README.md)
- [docs/architecture/overview.md](../architecture/overview.md)
- [docs/architecture/multitenancy.md](../architecture/multitenancy.md)
- [docs/delivery/current-state.md](../delivery/current-state.md)
- [docs/delivery/roadmap.md](../delivery/roadmap.md)
- [docs/delivery/work/README.md](../delivery/work/README.md)
- [docs/governance/documentation-policy.md](../governance/documentation-policy.md)
