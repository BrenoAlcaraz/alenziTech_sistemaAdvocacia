# Instruções do repositório

Instruções de bootstrap para qualquer execução de trabalho neste
repositório, seja por uma pessoa ou por um agente automatizado. Este
arquivo não substitui nem duplica a documentação canônica — ele orienta
por onde começar e aponta para as fontes que efetivamente governam
produto, arquitetura, segurança e processo.

## Fonte de verdade

[docs/README.md](docs/README.md) é o índice oficial da documentação
canônica e define a hierarquia das fontes de verdade. Produto,
arquitetura, segurança, entrega (delivery) e desenvolvimento
(development) têm papéis distintos dentro dessa hierarquia — ver
[docs/governance/documentation-policy.md](docs/governance/documentation-policy.md).

O HEAD do repositório prova a implementação atual; a documentação
canônica governa a intenção e a regra pretendida. Quando os dois
divergirem, ou quando documentos canônicos divergirem entre si, a
divergência não deve ser resolvida silenciosamente — ver a
[Regra de conflito](docs/README.md#regra-de-conflito).

## Antes de implementar

Toda implementação planejada corresponde a um Work Item em
[docs/delivery/work/](docs/delivery/work/README.md), sob o protocolo
definido em
[docs/delivery/work/README.md](docs/delivery/work/README.md).

Antes de alterar qualquer arquivo:

- fazer o preflight de Git;
- ler o Work Item integralmente;
- ler as fontes canônicas que ele indica;
- auditar o HEAD relevante ao item;
- confirmar escopo e dependências antes de começar.

A sequência operacional completa está em
[docs/development/workflow.md](docs/development/workflow.md).

## Execução por Work Item

- o Work Item define a unidade operacional e o escopo da execução;
- escopo não é ampliado silenciosamente;
- uma decisão em aberto (`OPEN-XXX`) não é resolvida dentro do item;
- nenhum requisito de produto é inventado;
- refatoração lateral não relacionada ao objetivo do item não é feita;
- um achado fora do escopo é registrado, nunca implementado
  silenciosamente;
- o estado `blocked` é usado somente diante de um impedimento real, não
  por dificuldade técnica comum;
- todo critério de aceite exige evidência, não inferência.

Estados, protocolo completo e regras de execução:
[docs/delivery/work/README.md](docs/delivery/work/README.md) e
[docs/development/workflow.md](docs/development/workflow.md).

## Segurança e escopo

Qualquer alteração que envolva autorização, multitenancy, dados ou
integridade deve ler as fontes de segurança aplicáveis antes da
implementação:

- [docs/security/overview.md](docs/security/overview.md)
- [docs/security/authorization-model.md](docs/security/authorization-model.md)
- [docs/security/data-scope.md](docs/security/data-scope.md)
- [docs/security/authorization-matrix.md](docs/security/authorization-matrix.md)

Autorização não deve ser presumida por atalho: um perfil administrativo
não implica acesso irrestrito a todo objeto por padrão; o campo técnico
`nivel` não deve ser tratado, por si só, como prova de autorização já
aplicada; isolamento por schema de tenant é uma garantia distinta da
autorização entre usuários do mesmo tenant. As distinções completas
estão nas fontes acima.

## Testes e quality gates

- [docs/development/testing.md](docs/development/testing.md)
- [docs/development/quality-gates.md](docs/development/quality-gates.md)

Não inventar ferramenta de teste ou qualidade além das já constatadas no
repositório. Todo comando executado, e seu resultado, deve ser
registrado — não presumido. Uma falha relevante causada pela alteração
em curso impede a conclusão do trabalho. Testes negativos são exigidos
quando segurança ou integridade de dados estiverem envolvidas.

## Git

[docs/development/git-procedure.md](docs/development/git-procedure.md)
é o procedimento completo. Guardas críticos:

- mudanças preexistentes no working tree pertencem ao usuário até prova
  em contrário;
- não resetar, limpar ou sobrescrever silenciosamente;
- staging é explícito, baseado no escopo da execução;
- commit e push só ocorrem quando explicitamente autorizados;
- nenhuma operação destrutiva é usada apenas para obter um working tree
  "limpo".

## Referências

- [docs/README.md](docs/README.md)
- [docs/governance/documentation-policy.md](docs/governance/documentation-policy.md)
- [docs/delivery/work/README.md](docs/delivery/work/README.md)
- [docs/development/workflow.md](docs/development/workflow.md)
- [docs/development/testing.md](docs/development/testing.md)
- [docs/development/quality-gates.md](docs/development/quality-gates.md)
- [docs/development/git-procedure.md](docs/development/git-procedure.md)
