# Instruções do repositório

Este é o ponto de entrada operacional para pessoas e agentes. As regras
canônicas permanecem em `docs/`; este arquivo indica apenas o contexto
mínimo necessário para começar.

## Fonte de verdade

[docs/README.md](docs/README.md) define a hierarquia documental. O HEAD
prova a implementação atual; PDRs, ADRs e especificações canônicas governam
a intenção. Divergências não são resolvidas silenciosamente.

## Contexto padrão

Leia sempre:

- este arquivo;
- o Work Item e seu **Context Pack** ativo;
- os arquivos diretamente afetados pelo trabalho.

Carregue sob demanda somente o que o impacto exigir e o Context Pack
indicar: documentação do módulo, PDR/ADR, segurança, arquitetura, estratégia
detalhada de testes, migrations, `current-state` ou histórico. Uma tarefa não
exige releitura indiscriminada dessas áreas.

Antes de escrever, faça o preflight de Git, confirme o escopo no HEAD e
classifique a execução como `FAST`, `STANDARD` ou `STRICT`, conforme
[workflow.md](docs/development/workflow.md#modos-de-execução).

## Guardas permanentes

- O Work Item delimita o escopo; não invente requisito, não resolva
  `OPEN-XXX` e não faça refatoração lateral.
- Mudanças preexistentes pertencem ao usuário: não resetar, limpar ou
  sobrescrever. Commit e push exigem autorização explícita.
- Alterações em autorização, IDOR/escopo, tenant, dados sensíveis,
  constraints ou migrations carregam as fontes aplicáveis e preservam
  controles de backend, isolamento e integridade.
- Testes e gates são selecionados pelo impacto. Evidência válida não é
  repetida só porque uma nova sessão começou.
- Todo critério de aceite e gate declarado como aprovado precisa de
  evidência real.

## Fontes operacionais

- [Workflow, modos, review e H1/H2](docs/development/workflow.md)
- [Estratégia de testes e invalidação de evidências](docs/development/testing.md)
- [Quality gates condicionais](docs/development/quality-gates.md)
- [Protocolo e template de Work Item](docs/delivery/work/README.md)
- [Procedimento de Git](docs/development/git-procedure.md)
